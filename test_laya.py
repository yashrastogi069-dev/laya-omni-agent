import sys
import warnings

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Suppress temperature calibration warnings from laya
warnings.filterwarnings("ignore", category=RuntimeWarning, module=r".*laya.*")
warnings.filterwarnings("ignore", message=r".*checkpoint ships temperatures outside.*")

import laya
from laya import Router

def main():
    print("--- Initializing Laya Router ---")
    print("Loading Laya checkpoints (CPU/GPU auto-detected)...\n")

    # Router automatically detects device (CUDA GPU if available, else CPU)
    # Lazy load (default) or preload=True for zero-latency server deployment
    router = Router()

    # 1. Example state to evaluate
    customer_state = {
        "user": "Alice",
        "ticket": "I was charged twice this morning for my monthly renewal. Please reverse the duplicate charge as soon as possible.",
    }

    # 2. Typed Questions (Choice, Score, Noul)
    questions = {
        "is_duplicate_billing": {
            "type": "noul",
            "instructions": "Does this ticket claim a duplicate or double charge?",
        },
        "urgency_score": {
            "type": "score",
            "instructions": "Rate the urgency and business risk of this customer inquiry.",
            "criteria": [
                "Low: Routine inquiry or feedback",
                "Medium: Minor billing question or feature inquiry",
                "High: Immediate financial dispute or duplicate charge",
                "Critical: Threatening churn, legal, or severe service outage",
            ],
        },
        "routing_department": {
            "type": "choice",
            "instructions": "Which department should handle this request?",
            "criteria": {
                "billing_support": "Payment errors, refunds, and duplicate charges",
                "technical_support": "Software bugs, outages, and product questions",
                "sales": "Upgrades, custom enterprise contracts, and licensing",
            },
        },
    }

    print("Evaluating state with Laya...")
    result = router.predict(customer_state, questions)

    print("\n✅ Laya Decision Results:")
    for q_id, ans in result["answers"].items():
        print(f" - {q_id}: {ans}")

    print("\nRouting Metadata:")
    print(f" - Selected Model: {result['routing']['model']}")
    print(f" - Reason: {result['routing']['reason']}")

if __name__ == "__main__":
    main()
