# Research & References

This project is a small, honest implementation of ideas from real conjunction
assessment (CA) practice — not a from-scratch invention. This doc lays out
what's borrowed from where, what's simplified, and what a production-grade
version would need beyond a class baseline.

## Core methods used

**Orbit propagation — SGP4/SDP4.**
Satellite positions are computed from TLEs using the SGP4 propagator (via the
[Skyfield](https://rhodesmill.org/skyfield/) library), the standard model for
propagating NORAD two-line element sets. See Vallado, Crawford, Hujsak &
Kelso, *"Revisiting Spacetrack Report #3"* (AIAA 2006-6753) for the reference
implementation this ecosystem is built on.

**Probability of collision — the 2D-Pc method (Foster & Estes, 1992).**
The `probability_of_collision.py` module implements the 2D-Pc approach: at
the point of closest approach, project the relative position uncertainty
onto the plane perpendicular to the relative velocity, model it as a 2D
Gaussian, and integrate that density over a disk sized to the combined
"hard body radius" of the two objects. This method was originally developed
for NASA/JSC to assess debris risk to the Space Shuttle and remains the
most widely used approach in operational conjunction assessment today.

- Foster, J.L. and Estes, H.S., *"A Parametric Analysis of Orbital Debris
  Collision Probability and Maneuver Rate for Space Vehicles,"*
  NASA/JSC-25898, August 1992.
- Later work (Chan 1997, Patera 2001/2005, Alfano 2005) proposed faster or
  more general variants of the same underlying integral; a 2016 comparison
  found all four methods agree closely across a wide range of realistic
  collision parameters, differing mainly in computational efficiency.
- Akella & Alfriend (2000) reformulated the 2D-Pc theory in terms of an
  equivalent, more numerically convenient form.

**Important honest limitation:** real Pc calculations use a covariance
matrix derived from orbit determination (a measure of how confident you are
in each object's tracked position), which is *not* part of the public TLE
format — TLEs give you a best-estimate trajectory, not its uncertainty. This
project's Pc module uses a fixed, generic assumed covariance so the *method*
is real and correctly implemented, but the resulting numbers are
illustrative, not operational-grade. A production system would instead pull
real covariance from something like a CCSDS Conjunction Data Message.

**Conjunction Data Message (CDM) — CCSDS 508.0-B-1.**
The real industry standard for exchanging conjunction warnings between
operators is the CCSDS Conjunction Data Message format, which packages
state vectors, covariance, and Pc results in a standardized way. This
project doesn't consume or emit real CDMs yet, but the report format is
loosely inspired by the same fields (objects, TCA, miss distance, Pc).

**SOCRATES Plus — real, free, full-catalog conjunction screening (CelesTrak/CSSI).**
The Center for Space Standards and Innovation has run SOCRATES (Satellite
Orbital Conjunction Reports Assessing Threatening Encounters in Space) as a
free public service since 2004, screening the full active-payload catalog
against the entire tracked object catalog roughly three times a day using
professional Systems Tool Kit (STK) Conjunction Analysis Tools, with real
orbit-determination covariance. This is the actual reference data this
project's phase 2 triage layer (`run_triage.py`, `src/socrates_client.py`)
consumes directly, rather than reimplementing inferior screening — see
"What phase 2 actually adds" below.

**SIMPLETON — validated open-source all-vs-all screening.**
Salad109/SIMPLETON (github.com/Salad109/SIMPLETON) is an open-source
project that performs full-catalog all-vs-all conjunction screening
(~450M pairs) in under 30 seconds on consumer hardware, validated against
SOCRATES at 99.8% agreement on equivalent scope and backtested against two
real historical collisions (Iridium 33/Cosmos 2251, 2009; CERISE/Ariane
debris, 1996) with millisecond-level TCA accuracy. Citing this here
deliberately: before building anything, it's worth knowing this problem —
fast, validated, full-catalog screening — is already solved and open
source. This project does not attempt to re-solve it.

**Risk tiering and operational thresholds.**
The commonly cited operational threshold for treating a conjunction as
"actionable" is a probability of collision around 1 in 10,000 (1e-4),
though individual operators and satellites use different thresholds based
on asset value and maneuver cost. This project's simpler miss-distance
tiers (this README's `knowledge_base.py`) approximate that same triage
logic without requiring trustworthy covariance data.

**Why this problem matters — background.**
The foundational argument for why orbital debris is a compounding, systemic
risk (rather than a one-off hazard) traces back to Kessler & Cour-Palais,
*"Collision Frequency of Artificial Satellites: The Creation of a Debris
Belt,"* Journal of Geophysical Research, 1978 — the paper that introduced
what's now called the Kessler syndrome.

## What real operational systems do that this baseline doesn't

Being upfront about the gap between this project and production
space-situational-awareness (SSA) tooling used by organizations like NASA's
Conjunction Assessment Risk Analysis (CARA) program, the U.S. Space Force's
18th Space Defense Squadron, or commercial providers such as LeoLabs,
Slingshot Aerospace, and COMSPOC:

- **Real tracking-derived covariance**, not an assumed placeholder — this is
  the single biggest fidelity gap in this baseline.
- **Adaptive time-of-closest-approach refinement** (root-finding around the
  coarse screening result) instead of fixed-grid sampling.
- **Full-catalog scale**: tens of thousands of tracked objects, screened
  continuously, with spatial partitioning to avoid O(n²) blowup.
- **Higher-fidelity force models** (atmospheric drag variation, solar
  radiation pressure, third-body effects) beyond what SGP4 captures.
- **Human-in-the-loop review** before any maneuver recommendation is acted
  on — this project's LLM narrative is a drafting aid, not a decision-maker.

## What phase 2 actually adds

Phase 1 (`run_baseline.py`) reimplements screening from scratch with SGP4
and a toy assumed-covariance Pc — useful for demonstrating understanding of
the underlying orbital mechanics, but not something that should compete
with SOCRATES or SIMPLETON on raw screening.

Phase 2 (`run_triage.py`) doesn't reimplement screening at all. It fetches
SOCRATES Plus's own real, published conjunction data (`src/socrates_client.py`)
— real Pc, real covariance, real STK/CAT propagation.

## From narration to reasoning

The first version of phase 2 took a real conjunction record and asked an
LLM to turn it into prose. That's narration, not reasoning — it has nothing
to reason *about* beyond the one snapshot it was given, and a rule-based
template does the same job with less risk. This was a fair critique of the
initial implementation, and the fix wasn't a bigger prompt — it was giving
the agent actual evidence to reason over. Three pieces:

1. **History (`src/observation_store.py`)** — a SQLite-backed log of every
   observation, keyed by object pair + TCA. Each scheduled run appends new
   observations rather than overwriting; nothing is reasoned about across
   time without this.
2. **Deterministic priority scoring (`src/risk_scoring.py`)** — Pc severity,
   time-to-TCA urgency, and tracking-data freshness are three separate,
   named, weighted factors, not a single miss-distance-or-Pc threshold. This
   directly fixes a real bug an earlier version had: with Pc weighted
   additively rather than as a gate, a near-zero probability paired with an
   imminent, fresh-data TCA could still score MEDIUM on urgency and
   freshness alone — the exact "Pc=7.8e-22 but MEDIUM" problem a reviewer
   flagged. `_tier()` now caps the ceiling by Pc severity first: urgency and
   freshness modulate priority within a tier the collision probability
   already justifies, they can't manufacture concern out of a negligible
   Pc. `tests/test_risk_scoring.py::test_near_zero_pc_does_not_produce_high_tier`
   pins this down; it failed against the pre-fix scoring logic during
   development, which is exactly what it's there to catch.
3. **Trend detection (`src/trends.py`)** — compares the oldest and newest
   observation on record for a given pair+TCA (not just the last two, so
   one noisy update doesn't flip the verdict) and classifies escalating,
   decreasing, stable, or insufficient_data.

**The agent (`src/analyst.py`)** is then given the current observation, the
deterministic assessment, and the trend, and asked analyst questions: why
does this matter, what changed, what's missing, how confident should we be,
what's next. The constraint that makes this trustworthy isn't just prompt
wording — `AnalystOutput` has no field anywhere for a probability or a
priority score. It is structurally unable to report an altered number,
because there's nowhere to put one, whether the answer comes from the LLM
or the rule-based fallback. `tests/test_analyst.py` verifies this: the
fallback path is checked to reproduce the exact input Pc and tier verbatim,
and a standalone test asserts the output schema itself has no numeric
override field, independent of what any model does.

Demonstrated end-to-end with two simulated runs against the same mocked
object pair: run 1 correctly reported `insufficient_data` (nothing to
compare yet); run 2, with Pc raised from 1.2e-6 to 6.1e-5 in the fixture,
correctly detected a 50.8x escalation and moved the priority tier from
MEDIUM to HIGH — matching the actual ratio, not an invented one.

## Why this project stopped calling itself an agent

Everything above is real and load-bearing engineering. It is still not an
agent, and the project's own earlier README overclaimed by calling it one.

The technical definition, not a stylistic one: ReAct (Yao et al., 2022,
*"ReAct: Synergizing Reasoning and Acting in Language Models,"* ICLR 2023)
and Toolformer (Schick et al., 2023, NeurIPS) both define agentic behavior
as an LLM choosing which action to take next, from a real set of options,
based on something it just observed, in a sequence that isn't fully
enumerable by the programmer ahead of time. Voyager (Wang et al., 2023,
*"An Open-Ended Embodied Agent with Large Language Models"*) is the clean
extreme version: an agent that writes and accumulates its own skills
because the task space is genuinely open-ended.

This pipeline's control flow is fixed: fetch, persist, score, check trend,
explain — the same order, unconditionally, every run. The LLM call never
chooses between options; it has exactly one job, every time. By the
field's own definition, that disqualifies it from being called an agent,
regardless of how good the explanation it produces is.

This isn't a gap to apologize for. The reason the pipeline doesn't need
agentic behavior is that its core decision — how urgent is this event,
given (Pc, time-to-TCA, data age) — is a bounded, well-defined, computable
mapping. Agents exist to handle *ambiguity about what to do next*; this
problem doesn't have that ambiguity, so introducing autonomy here would
trade away reproducibility and auditability for nothing. Real
space-situational-awareness organizations make the same call, for the same
reason.

If this project ever grows a genuinely agentic piece, the honest candidate
is object-identity resolution: SOCRATES gives a name string, not a
confirmed identity, and reconciling that against messy, sometimes
conflicting catalog data is a real open-ended, unpredictable-length
investigation — the kind of problem ReAct-style tool use is actually for.
It isn't built, because doing it just to be able to say "now it's agentic"
would repeat the same mistake this section is correcting.

Also worth reading before building any multi-agent system: Cemri et al.,
*"Why Do Multi-Agent LLM Systems Fail?"* (2025, arXiv:2503.13657) — a
taxonomy of real, observed failure modes (agents talking past each other,
no shared ground truth, cascading errors) that's a more useful starting
point than any tutorial. And as a concrete cautionary tale about vague
goals and no stopping condition: AutoGPT's well-documented infinite-loop
failures, where agents given open-ended goals like "research X" mostly
just looped rather than converging.

## On this being "used by companies"

The phase 1 baseline is a well-grounded educational exercise — getting each
piece scientifically right (SGP4, the actual Foster-Estes method, real
citations) is worth doing regardless of adoption, but it doesn't compete
with production screening.

Phase 2 is a narrower, more honest claim: a genuinely useful accessibility
layer on top of real, trusted data (SOCRATES Plus), for an audience
(smaller operators, university cubesat teams, students, educators) that
realistically doesn't have a dedicated SSA analyst reading a raw CSV every
morning. That's a real gap and a real product shape — but it still carries
real liability if presented as more authoritative than it is. Concretely,
this means:

- Every report explicitly labels Pc provenance (real vs. assumed) — never
  presented as this project's own analysis when it's SOCRATES's number.
- The narrative layer is explicitly framed to itself and to the reader as
  a drafting aid, not a decision-maker — any actual maneuver decision
  needs a human analyst and, ideally, direct engagement with the object's
  actual operator or CSpOC.
- Staleness (DSE) is surfaced, not hidden, because acting on out-of-date
  tracking data is exactly the kind of overconfidence that causes harm in
  this domain.

The honest pitch to a company or recruiter is "I understood the real
method and the real data landscape well enough to build something that
adds genuine value without overclaiming what it is" — not "this replaces
a production system."
