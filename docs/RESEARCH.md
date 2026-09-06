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

## On this being "used by companies"

This is a genuinely well-grounded educational baseline, and getting each
piece scientifically right (SGP4, the actual Foster-Estes method, real
citations) is worth doing regardless of adoption. But real SSA is a
capital-intensive, liability-sensitive field with entrenched, well-funded
providers who have real tracking data this project doesn't have access to.
The honest pitch to a company or recruiter is "I understood the real method
well enough to implement it correctly and know exactly where it's
simplified" — not "this replaces a production system."
