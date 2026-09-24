"""
omni_engine.decision.calibration_eval
====================================
Deterministic Stratified Partitioning and Empirical Calibration Evaluation Harness
for System 1 Decision Fabric on Held-Out Test Splits.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): Stratified 70/30 split is 100% deterministic,
  sorting by domain and case ID with zero external random state.
- Signals are First-Class (Invariant 7): Computes real empirical Expected Calibration Error
  (ECE across 10 bins), Macro-F1, Precision, and Recall.
- Evidence-Based Calibration: Signals are only marked `is_calibrated=True` when
  sample_count >= 30, ECE <= 0.15, and F1 >= 0.70.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from omni_engine.contracts.broker import CalibrationMetrics
from omni_engine.decision.eval_corpus import DECISION_EVAL_CORPUS_V1, DecisionEvalCase
from omni_engine.providers.base import SystemOneProvider


def get_stratified_corpus_split(
    corpus: Optional[List[DecisionEvalCase]] = None,
    train_ratio: float = 0.70,
) -> Tuple[List[DecisionEvalCase], List[DecisionEvalCase]]:
    """Partitions the decision evaluation corpus into deterministic dev (70%) and held-out test (30%) splits.

    Stratified by `expected_domain` and sorted alphabetically by `case.id`.
    Produces exactly 72 dev cases and 31 test cases from the 103-case canonical corpus.
    """
    cases = corpus or DECISION_EVAL_CORPUS_V1
    strata: Dict[str, List[DecisionEvalCase]] = defaultdict(list)

    for case in cases:
        strata[case.expected_domain].append(case)

    dev_split: List[DecisionEvalCase] = []
    test_split: List[DecisionEvalCase] = []

    for domain in sorted(strata.keys()):
        domain_cases = sorted(strata[domain], key=lambda c: c.id)
        n = len(domain_cases)
        k = round(n * train_ratio)
        dev_split.extend(domain_cases[:k])
        test_split.extend(domain_cases[k:])

    return dev_split, test_split


def compute_calibration_metrics(
    ground_truth: List[str],
    predictions: List[str],
    confidences: List[float],
    signal_name: str,
    provider_id: str,
    num_bins: int = 10,
) -> CalibrationMetrics:
    """Computes categorical accuracy, macro precision/recall/F1, and Expected Calibration Error (ECE)."""
    n = len(ground_truth)
    if n == 0 or len(predictions) != n or len(confidences) != n:
        raise ValueError("Inputs must be non-empty and of equal length")

    # 1. Categorical Accuracy
    correct = [1 if gt == pred else 0 for gt, pred in zip(ground_truth, predictions)]
    accuracy = sum(correct) / n

    # 2. Per-class Precision, Recall, and Macro-F1
    all_classes = sorted(list(set(ground_truth) | set(predictions)))
    f1_scores = []
    precisions = []
    recalls = []

    for cls in all_classes:
        tp = sum(1 for gt, pred in zip(ground_truth, predictions) if gt == cls and pred == cls)
        fp = sum(1 for gt, pred in zip(ground_truth, predictions) if gt != cls and pred == cls)
        fn = sum(1 for gt, pred in zip(ground_truth, predictions) if gt == cls and pred != cls)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        f1_scores.append(f1)

    macro_prec = sum(precisions) / len(precisions) if precisions else 0.0
    macro_rec = sum(recalls) / len(recalls) if recalls else 0.0
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    # 3. Expected Calibration Error (ECE) across 10 equal bins
    bin_size = 1.0 / num_bins
    ece = 0.0
    bin_details = {}

    for m in range(num_bins):
        bin_lower = m * bin_size
        bin_upper = (m + 1) * bin_size

        # Find items in bin: [lower, upper) for all except last bin which is [lower, upper]
        if m == num_bins - 1:
            indices = [i for i, c in enumerate(confidences) if bin_lower <= c <= bin_upper]
        else:
            indices = [i for i, c in enumerate(confidences) if bin_lower <= c < bin_upper]

        bin_count = len(indices)
        if bin_count > 0:
            bin_acc = sum(correct[i] for i in indices) / bin_count
            bin_conf = sum(confidences[i] for i in indices) / bin_count
            bin_diff = abs(bin_acc - bin_conf)
            ece += (bin_count / n) * bin_diff
            bin_details[f"bin_{m}"] = {
                "range": [round(bin_lower, 2), round(bin_upper, 2)],
                "count": bin_count,
                "accuracy": round(bin_acc, 4),
                "avg_confidence": round(bin_conf, 4),
                "gap": round(bin_diff, 4),
            }

    # Strict Calibration Gate: N >= 30, ECE <= 0.15, F1 >= 0.70
    is_calibrated = (n >= 30) and (ece <= 0.15) and (macro_f1 >= 0.70)

    return CalibrationMetrics(
        signal_name=signal_name,
        provider_id=provider_id,
        sample_count=n,
        accuracy=round(accuracy, 4),
        precision=round(macro_prec, 4),
        recall=round(macro_rec, 4),
        f1=round(macro_f1, 4),
        ece=round(ece, 4),
        is_calibrated=is_calibrated,
        details={
            "num_classes": len(all_classes),
            "classes": all_classes,
            "bin_statistics": bin_details,
        },
    )


def evaluate_held_out_split(
    provider: Optional[SystemOneProvider] = None,
    test_split: Optional[List[DecisionEvalCase]] = None,
) -> Dict[str, CalibrationMetrics]:
    """Runs empirical calibration evaluation on the held-out test split."""
    if test_split is None:
        _, test_split = get_stratified_corpus_split()

    from omni_engine.decision.fabric import DecisionFabric
    fabric = DecisionFabric(provider=provider)

    gt_domains = []
    pred_domains = []
    conf_domains = []

    gt_intents = []
    pred_intents = []
    conf_intents = []

    gt_risks = []
    pred_risks = []
    conf_risks = []

    gt_needs_tools = []
    pred_needs_tools = []
    conf_needs_tools = []

    for case in test_split:
        frame = fabric.evaluate(prompt=case.prompt)

        # Domain signal
        top_domain = frame.candidate_domains[0] if frame.candidate_domains else "general"
        domain_sig = frame.raw_signals.get("domain")
        if domain_sig and domain_sig.probabilities and top_domain in domain_sig.probabilities:
            top_domain_conf = domain_sig.probabilities[top_domain]
        elif domain_sig:
            top_domain_conf = domain_sig.confidence
        else:
            top_domain_conf = 0.5
        gt_domains.append(case.expected_domain)
        pred_domains.append(top_domain)
        conf_domains.append(top_domain_conf)

        # Intent signal
        gt_intents.append(case.expected_intent)
        pred_intents.append(frame.intent.value)
        conf_intents.append(frame.intent.confidence)

        # Risk signal
        gt_risks.append(case.expected_risk)
        pred_risks.append(frame.risk.value)
        conf_risks.append(frame.risk.confidence)

        # Needs tools signal
        gt_needs_tools.append(str(case.expected_needs_tools).lower())
        pred_needs_tools.append(str(frame.needs_tools.value).lower())
        conf_needs_tools.append(frame.needs_tools.confidence)

    prov_id = provider.provider_id if provider else "laya_shared"

    metrics = {
        "domain": compute_calibration_metrics(gt_domains, pred_domains, conf_domains, "domain", prov_id),
        "intent": compute_calibration_metrics(gt_intents, pred_intents, conf_intents, "intent", prov_id),
        "risk": compute_calibration_metrics(gt_risks, pred_risks, conf_risks, "risk", prov_id),
        "needs_tools": compute_calibration_metrics(gt_needs_tools, pred_needs_tools, conf_needs_tools, "needs_tools", prov_id),
    }

    return metrics
