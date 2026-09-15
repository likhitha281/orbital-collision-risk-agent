# 🛰️ Orbital Collision-Risk Agent

[![CI](https://github.com/likhitha281/orbital-collision-risk-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/likhitha281/orbital-collision-risk-agent/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**🔴 [Live dashboard](https://likhitha281.github.io/orbital-collision-risk-agent/)** — no login, no setup, updates automatically every 12 hours.

A deterministic priority-scoring and trend-detection pipeline for real
orbital conjunction (near-collision) data, with an optional LLM-assisted
explanation step.

**What it is not, on purpose**: an autonomous agent. There's no dynamic
tool selection, no decision loop, nothing choosing what to do next. Given
(probability of collision, time to closest approach, tracking-data age),
there's a computable right answer for how urgent an event is — so that
answer is computed deterministically, not routed through an LLM. The one
LLM call in this pipeline is optional, structurally prevented from altering
any number it's given, and exists only to write a clearer explanation than
a template — see "Why no agent" below for the actual reasoning, not just
the assertion.

## What it does

```text
CelesTrak SOCRATES Plus (real conjunction data)
      ↓
Persist to SQLite (observation history, keyed by object pair + TCA)
      ↓
Deterministic priority score (Pc severity + urgency + data freshness)
      ↓
Trend detection (escalating / decreasing / stable, vs. observation history)
      ↓
Optional LLM explanation (or rule-based fallback — same contract either way)
      ↓
Dashboard + Markdown/JSON report
```

For every conjunction, three concerns stay explicitly separate:

- **Collision probability** — CelesTrak SOCRATES Plus's own number, computed
  with professional STK/Conjunction Analysis Tools and real tracking
  covariance. This project doesn't recompute it.
- **Operational priority** — a 0-100 score computed by `src/risk_scoring.py`
  from three named, weighted factors. The LLM never sees this computation.
- **Explanation** — generated from the score and trend history, by
  `src/analyst.py`. Its output schema has no field for a probability or a
  score, so it's structurally unable to report an altered number, whether
  the answer comes from the LLM or its rule-based fallback.

### Example

**HIGH · 74.5/100**

ISS (ZARYA) vs COSMOS 2251 DEB

| Metric | Value |
|---|---:|
| Collision probability (real, SOCRATES) | 6.1 × 10⁻⁵ |
| Miss distance | 620 m |
| Time to closest approach | 7.5h |
| Trend | first observation — insufficient history yet |

> Recommend an active maneuver evaluation and re-screen against fresher
> tracking data. *(low confidence, rule_based_fallback — no API key was
> set for this example)*

## Why no agent

The first version of this project called itself an agent because it had an
LLM call in it. That's not what the word means in the actual research —
ReAct (Yao et al., 2022) and Toolformer (Schick et al., 2023) define
agentic behavior as an LLM choosing *which* action to take next, from real
options, based on something just observed, in a sequence that couldn't be
fully enumerated ahead of time. This pipeline never does that: fetch →
score → check trend → explain, unconditionally, in the same order, every
time. Calling that an agent oversells it.

More importantly, this domain mostly doesn't have the kind of ambiguity
agents are for. Given clean, structured inputs and a well-defined scoring
function, computing the answer deterministically is strictly better than
routing it through an LLM: reproducible, free, instant, auditable. Real
space-situational-awareness organizations make the same call for the same
reason — the objection to "let an LLM triage collision risk" isn't caution
for its own sake, it's that non-determinism is a pure cost when the mapping
from inputs to answer is already well-defined.

Full writeup, including a real scoring bug this project's own tests caught
during development (the exact "near-zero Pc scoring as MEDIUM" failure
mode), in [`docs/RESEARCH.md`](docs/RESEARCH.md).

## Quickstart

```bash
git clone https://github.com/likhitha281/orbital-collision-risk-agent.git
cd orbital-collision-risk-agent
pip install -r requirements.txt

python run_triage.py --max-results 50 --min-probability 1e-6 --output triage_report.md
```

Optional — LLM-generated explanations instead of the rule-based fallback
(same contract either way: no field to alter a number even if it wanted to):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python run_triage.py --output triage_report.md
```

Run the test suite (41 tests, including the schema-level guarantee that the
explanation layer has no numeric override field):

```bash
python -m pytest tests/ -v
```

**One thing to verify before relying on this**: `src/socrates_client.py`
assumes SOCRATES Plus's CSV export accepts a `FORMAT=CSV` parameter,
following the convention CelesTrak uses elsewhere — this project's
development sandbox couldn't confirm that URL directly (see the module
docstring). Open the built URL in a browser once and adjust if needed; the
CSV column parsing itself is taken verbatim from CelesTrak's documented
format and is correct regardless.

## Trend detection, concretely

A single run reports what it has. Repeated runs — via the scheduled
`live-monitor.yml` workflow, which persists history in a cache between
runs — let it say things like "probability of collision increased 51x
across the last three observations," which is a qualitatively different
claim from restating one snapshot in English. Demonstrated end-to-end
during development with two simulated runs against the same mocked object
pair: run 1 correctly reported insufficient data; run 2, with Pc raised in
the fixture, correctly detected a 50.8x escalation and moved the priority
from MEDIUM to HIGH — matching the real ratio, not an invented one.

## Physics baseline (secondary, educational)

`run_baseline.py` is a from-scratch SGP4 orbit propagator and conjunction
screener, implementing the actual 2D-Pc method used in the field (Foster &
Estes, 1992) — kept in the repo to demonstrate the underlying orbital
mechanics, not as the live pipeline. It uses an *assumed* covariance
(TLEs don't carry real tracking uncertainty), so its Pc numbers are
illustrative, not operational. Two free, established tools already solve
full-catalog conjunction screening properly — CelesTrak's own SOCRATES Plus
service (free, public, running since 2004) and the open-source SIMPLETON
screener, validated against it — which is exactly why this project consumes
SOCRATES's real data above rather than trying to out-build either:

```bash
python run_baseline.py --input data/sample_catalog.tle --output report.md
python run_baseline.py --live --live-group stations --output report.md  # live Celestrak fetch
```

Full detail in [`docs/RESEARCH.md`](docs/RESEARCH.md), including why this
split exists and what it deliberately doesn't try to replace.

## Chatbot (optional)

The dashboard has a chat widget for asking questions about the current
data in plain language — "what's the highest priority event," "is
anything escalating." It's grounded strictly in the dashboard's JSON
snapshot and instructed never to invent a number that isn't in it, same
philosophy as `src/analyst.py`.

Requires a small backend, because GitHub Pages is static hosting and an
API key can never safely live in client-side JavaScript. `chatbot/worker.js`
is a Cloudflare Worker (free tier) that holds the key server-side; see
[`chatbot/README.md`](chatbot/README.md) for the ~10-minute deploy, and
honest notes on what CORS does and doesn't protect against. Its
request-handling logic (CORS, validation, rate limiting, error handling)
is tested directly with Node in `chatbot/test_worker.mjs` — 11 checks, no
live deployment required to verify the logic.

## Deployment options

The pipeline logic doesn't change — these just package and schedule it
differently. Default is GitHub Actions (`.github/workflows/live-monitor.yml`),
which is genuinely the right amount of infrastructure for what this does
today: one fetch, one scoring pass, every 12 hours, no inter-task
dependencies. The others exist as documented alternatives, not because the
current pipeline needs them:

| Approach | When it's actually worth it |
|---|---|
| Docker (`Dockerfile`, `docker-compose.yml`) | Running off GitHub's infrastructure entirely |
| Kubernetes (`k8s/cronjob.yaml`) | Already operating a cluster this can run alongside |
| Prefect (`orchestration/`) | Multiple data sources, inter-task dependencies, need for per-task retries/backfills |

## Project layout

```
├── run_triage.py             # the actual pipeline entrypoint
├── run_baseline.py           # secondary: SGP4 physics baseline
├── src/
│   ├── socrates_client.py    # real conjunction data (CelesTrak SOCRATES Plus)
│   ├── observation_store.py  # SQLite observation history (enables trend detection)
│   ├── risk_scoring.py       # deterministic priority score, walled off from the LLM
│   ├── trends.py             # escalating/decreasing/stable detection across history
│   ├── analyst.py            # explanation layer — no field to alter a number
│   ├── triage.py             # filter/prioritize real records
│   ├── tle_loader.py, live_fetch.py, conjunction.py,
│   │   probability_of_collision.py, knowledge_base.py,
│   │   reasoning_agent.py, report.py   # physics baseline (secondary)
├── data/sample_catalog.tle
├── examples/                 # worked example outputs
├── tests/                    # 41 tests
├── docs/
│   ├── index.html            # live dashboard (GitHub Pages) + chat widget
│   ├── latest.json           # data the dashboard reads (auto-updated)
│   └── RESEARCH.md           # papers, data sources, and the honest history of this project
├── chatbot/
│   ├── worker.js              # Cloudflare Worker backend (holds the API key server-side)
│   ├── test_worker.mjs        # tests the worker logic without a live deployment
│   └── wrangler.toml
├── Dockerfile, docker-compose.yml, k8s/, orchestration/   # deployment options, not defaults
└── .github/workflows/
    ├── ci.yml                # tests on every push
    └── live-monitor.yml      # scheduled fetch + score + publish
```

## Known limitations

- `src/socrates_client.py`'s exact CSV endpoint parameter is unverified
  from this project's development sandbox (see module docstring) — verify
  once before relying on it in production.
- The knowledge base backing the physics baseline is six hand-written
  notes, not a real corpus of operator handbooks.
- This project trusts and attributes CelesTrak's Pc numbers; it doesn't
  independently verify them.
- Trend detection compares oldest-vs-newest observation on record, not a
  fitted curve — a genuinely noisy single early reading can bias the first
  few trend calls until more history accumulates.
- The physics baseline's fixed-grid screening and O(n²) scaling are real
  limitations, moot for the live pipeline since it doesn't use that path.

## Research & References

[`docs/RESEARCH.md`](docs/RESEARCH.md) has the actual papers (Foster &
Estes 1992 on 2D-Pc, Vallado et al. on SGP4, Kessler & Cour-Palais 1978,
Yao et al. 2022 and Schick et al. 2023 on what "agentic" actually means),
the real prior art this project builds on rather than reinvents (SOCRATES
Plus, SIMPLETON), and an honest account of where every simplification is,
including one this project's own tests caught mid-development.

## License

MIT — see [`LICENSE`](LICENSE).
