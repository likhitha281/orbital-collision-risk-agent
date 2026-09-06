# Orbital Collision-Risk Report

- Catalog file: `data/sample_catalog.tle`
- Generated: 2026-09-06T17:42:04+00:00
- Conjunctions flagged: 1

> **Note on Pc**: the probability-of-collision figures below use an *assumed* generic position-uncertainty covariance (TLEs do not include real covariance data), so treat Pc as illustrative of the method, not an operational-grade number. Risk tiers are driven by miss distance for that reason. See the main README's Research & References and Limitations sections.

## 1. ISS (ZARYA) vs TEST-DEBRIS-1 (SYNTHETIC) _(involves a synthetic test object)_

- NORAD IDs: 25544 / 99999
- Time of closest approach (UTC): 2025-11-04T10:15:19Z
- Miss distance: **2.767 km**
- Relative speed at closest approach: 0.0031 km/s
- Probability of collision (2D-Pc, Foster & Estes 1992; *assumed* covariance, see [Research & References](../README.md#research--references)): **7.826e-22**
- Risk tier: **MEDIUM** (based on miss distance, not Pc — see note below)
- Grounded on notes: risk-tiers, maneuver-tradeoffs, false-positive-context
- Recommendation (rule_based_fallback):
  > Miss distance of 2.767 km warrants close monitoring and a maneuver plan on standby, with a re-screen as the event approaches.
