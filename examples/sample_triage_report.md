# Orbital Collision-Risk Triage Report

> **Note on this example file**: generated with mocked SOCRATES CSV data (matching
> the real documented schema exactly) because this sandbox can't reach celestrak.org.
> Run `python run_triage.py` yourself to get a real, current report. The escalation
> example in this project's writeup (Pc increasing 50.8x across two runs) was
> demonstrated separately with two simulated runs against the same mocked schema —
> see the PR description / commit message for that trace.

- Data source: CelesTrak SOCRATES Plus (real conjunction data)
- Generated: 2026-09-12T05:53:59+00:00
- Conjunctions flagged: 3

## 1. ISS (ZARYA) [+] vs COSMOS 2251 DEB [-] — HIGH (75.1/100)

- NORAD IDs: 25544 / 90001
- TCA (UTC): 2026-09-12T04:12:33.000000
- Miss distance: **0.62 km**
- Probability of collision (real, SOCRATES): **6.100e-05**
- Priority breakdown: Pc=63.1, urgency=100.0, freshness=81.7
- Trend: **insufficient_data** (1 observation(s) so far)

**ISS (ZARYA) [+] vs COSMOS 2251 DEB [-]: probability of collision 6.10e-05, priority HIGH (score 75.1/100).**

*Why it matters*: Closest approach is soon (0.0h away)

*Trend*: Only one observation is available so far; no trend can be established yet.

*Suggested next step*: Recommend an active maneuver evaluation and re-screen against fresher tracking data.

*Confidence*: low (rule_based_fallback)

*Limitations*: Closest approach is soon (0.0h away); Fewer than 3 observations available — trend estimate is preliminary.

## 2. STARLINK-3011 [+] vs FENGYUN 1C DEB [-] — MEDIUM (50.1/100)

- NORAD IDs: 48274 / 90002
- TCA (UTC): 2026-09-13T14:22:10.000000
- Miss distance: **3.1 km**
- Probability of collision (real, SOCRATES): **4.100e-06**
- Priority breakdown: Pc=43.5, urgency=59.9, freshness=60.0
- Trend: **insufficient_data** (1 observation(s) so far)

**STARLINK-3011 [+] vs FENGYUN 1C DEB [-]: probability of collision 4.10e-06, priority MEDIUM (score 50.1/100).**

*Why it matters*: No individual factor is extreme; priority reflects a moderate combination

*Trend*: Only one observation is available so far; no trend can be established yet.

*Suggested next step*: Continue monitoring and re-screen as the event approaches.

*Confidence*: low (rule_based_fallback)

*Limitations*: No individual factor is extreme; priority reflects a moderate combination; Fewer than 3 observations available — trend estimate is preliminary.

## 3. NOAA 19 [+] vs IRIDIUM 33 DEB [-] — LOW (27.6/100)

- NORAD IDs: 33591 / 90003
- TCA (UTC): 2026-09-14T02:00:00.000000
- Miss distance: **4.5 km**
- Probability of collision (real, SOCRATES): **5.000e-07**
- Priority breakdown: Pc=28.3, urgency=42.3, freshness=0.0
- Trend: **insufficient_data** (1 observation(s) so far)

**NOAA 19 [+] vs IRIDIUM 33 DEB [-]: probability of collision 5.00e-07, priority LOW (score 27.6/100).**

*Why it matters*: Underlying tracking data is 10.0 days old — treat as less certain

*Trend*: Only one observation is available so far; no trend can be established yet.

*Suggested next step*: Log the event; no immediate action needed.

*Confidence*: low (rule_based_fallback)

*Limitations*: Underlying tracking data is 10.0 days old — treat as less certain; Underlying tracking data is more than 7 days old.; Fewer than 3 observations available — trend estimate is preliminary.
