# Architecture

The agent is a linear pipeline of four tools orchestrated by `run_baseline.py`.
Each tool has a narrow, testable responsibility, and the LLM is only used for
the final narrative step — every number in the report comes from deterministic
orbital mechanics, not from the model.

```mermaid
flowchart LR
    A[TLE catalog file] --> B[tle_loader\nparse TLEs to\nEarthSatellite objects]
    B --> C[conjunction\nSGP4 propagation +\nclose-approach screening]
    C -->|ConjunctionEvent list| D[knowledge_base\nTF-IDF retrieval over\nops-practice notes]
    D --> E[reasoning_agent\nLLM narrative\nrule-based fallback]
    E --> F[report\nrender Markdown]
    F --> G[report.md]

    style A fill:#1f2937,stroke:#38bdf8,color:#e5e7eb
    style G fill:#1f2937,stroke:#22c55e,color:#e5e7eb
```

## Why this shape

- **Deterministic core, generative edge.** Orbit propagation and distance
  screening are physics, not language modeling — they run the same way every
  time. The LLM is confined to turning already-computed numbers into a
  readable recommendation, and is explicitly told not to alter the risk tier.
- **Fails soft.** If `ANTHROPIC_API_KEY` isn't set, or the API call fails for
  any reason, `reasoning_agent.py` falls back to a rule-based template so the
  baseline is fully runnable and reproducible with zero external
  dependencies or credentials.
- **Swappable knowledge base.** `KnowledgeBase.retrieve()` is the only
  interface the rest of the code depends on. The current implementation is a
  small in-memory TF-IDF index; a future iteration can swap in a real vector
  store over operator handbooks without touching any other module.

## Known limitations (see also README § Limitations)

- The conjunction screener samples distance on a fixed time grid rather than
  solving for the true minimum, so very short, very close passes between
  samples could be missed or under/over-estimated.
- The sample catalog includes one real object (ISS) and one synthetic
  object constructed to guarantee a close approach, so the pipeline has a
  concrete, reproducible test case that doesn't depend on live tracking data.
- Screening is currently O(n^2) in the number of catalog objects — fine for
  a handful of objects, not yet suitable for a full multi-thousand-object
  catalog without spatial partitioning.
