# DEFERRED.md — Out-of-Scope Architecture Backlog

## Permanent Scope-Control Rule
If a feature or capability:
1. Is not required for the current acceptance gate,
2. Substantially increases architectural complexity, or
3. Depends on foundational layers that do not yet exist,
it MUST be recorded here and postponed.

---

## Deferred Items

| Item ID | Description | Target Phase / Checkpoint | Rationale |
| :--- | :--- | :--- | :--- |
| **DEF-001** | **Flat 23-Tool Catalog Dump** | **REJECTED / SUPERSEDED** | Slicing at 12 is a legacy limitation, but dumping all 23+ tools into a single prompt is rejected in favor of Hierarchical Routing (L6). |
| **DEF-002** | **Vector Episodic Memory (ChromaDB / FAISS)** | Phase V (L19) | Premature optimization. Structured SQLite memory with outcome verification must be proven before adding embedding generation overhead. |
| **DEF-003** | **Vision-Language UI Grounding (OmniParser / YOLO)** | Phase V (L18 / L22) | Requires heavy local vision models or multimodal cloud latency. DOM-based Playwright primitives are sufficient for 95% of web workflows. |
| **DEF-004** | **Local Voice I/O (Whisper STT + Piper TTS)** | Phase VI (L22) | Voice interface is an I/O modality. The core cognitive loop and tool execution safety must be hardened first. |
| **DEF-005** | **Multi-Agent Swarm Handoff Protocols** | Phase VI (L22) | Introducing multiple autonomous agents before single-agent DAG execution and idempotency are robust creates unbounded race conditions and infinite loops. |
| **DEF-006** | **Automated DPO/SFT Fine-Tuning Pipeline** | Phase VI (L25) | Fine-tuning local Laya weights requires collecting a high-quality corpus of verified successful real-world executions. |
| **DEF-007** | **N8N / Zapier External Webhook Engine** | Phase V (L20) | Outbound/inbound automation requires reliable mutation safety and confirmation policy before connecting to live third-party webhooks. |
| **DEF-008** | **Multilingual Models & Language Routing** | **EXPLICITLY DEFERRED / BANNED** | LAYA Omni Agent is strictly an ENGLISH-ONLY system. Multilingual checkpoints, tokenizers, and language detection are banned to preserve host RAM and focus engineering effort. |
