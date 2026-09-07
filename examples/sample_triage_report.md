# Orbital Collision-Risk Report

> **Note on this example file**: generated with mocked SOCRATES CSV data (matching
> the real documented schema exactly) because this sandbox can't reach celestrak.org.
> Run `python run_triage.py` yourself to get a real, current report.

- Data source: `CelesTrak SOCRATES Plus (real conjunction data, STK/CAT propagation, real covariance)`
- Generated: 2026-09-07T21:57:27+00:00
- Conjunctions flagged: 3

> **Note on Pc**: these probability-of-collision figures are CelesTrak SOCRATES Plus's own published numbers, computed with STK/Conjunction Analysis Tools using real orbit-determination covariance — not this project's own estimate. Risk tiers below are based on that real probability. See docs/RESEARCH.md.

## 1. ISS (ZARYA) [+] vs COSMOS 2251 DEB [-]

- NORAD IDs: 25544 / 90001
- Time of closest approach (UTC): 2026-09-10T04:12:33.000000
- Miss distance: **1.234 km**
- Relative speed at closest approach: 7.891 km/s
- Probability of collision (real, CelesTrak SOCRATES Plus): **2.300e-04**
- Risk tier: **HIGH**
- Grounded on notes: pc-threshold, risk-tiers, maneuver-tradeoffs
- Recommendation (rule_based_fallback):
  > Probability of collision 2.30e-04 is inside the high-concern band. Recommend an active maneuver evaluation and re-screening against the freshest available tracking data before the predicted close-approach time.

## 2. STARLINK-3011 [+] vs FENGYU 1C DEB [-]

- NORAD IDs: 48274 / 90002
- Time of closest approach (UTC): 2026-09-11T14:22:10.000000
- Miss distance: **3.1 km**
- Relative speed at closest approach: 9.2 km/s
- Probability of collision (real, CelesTrak SOCRATES Plus): **4.100e-06**
- Risk tier: **MEDIUM**
- Grounded on notes: pc-threshold, risk-tiers, maneuver-tradeoffs
- Recommendation (rule_based_fallback):
  > Probability of collision 4.10e-06 warrants close monitoring and a maneuver plan on standby, with a re-screen as the event approaches.

## 3. NOAA 19 [+] vs IRIDIUM 33 DEB [-]

- NORAD IDs: 33591 / 90003
- Time of closest approach (UTC): 2026-09-12T02:00:00.000000
- Miss distance: **4.5 km**
- Relative speed at closest approach: 7.4 km/s
- Probability of collision (real, CelesTrak SOCRATES Plus): **5.000e-07**
- Risk tier: **LOW**
- ⚠️ **Tracking data >7 days old** — treat as indicative, re-screen before acting
- Grounded on notes: pc-threshold, risk-tiers, maneuver-tradeoffs
- Recommendation (rule_based_fallback):
  > Probability of collision 5.00e-07 is outside the typical action threshold. Log the event and continue routine monitoring. Underlying tracking data is more than 7 days old — treat this as indicative and re-screen against fresher data before acting.
