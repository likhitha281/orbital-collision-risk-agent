"""
probability_of_collision.py
-----------------------------
Tool: computes a Probability of Collision (Pc) using the 2D-Pc method
originally published by Foster & Estes (NASA/JSC-25898, 1992) and still the
most widely used approach in operational conjunction assessment today
(see README "Research & References" for citations).

Method, briefly:
  1. At the time of closest approach (TCA), project the relative position
     uncertainty onto the 2D plane perpendicular to the relative velocity
     vector (the "encounter plane").
  2. Model that projected uncertainty as a 2D Gaussian.
  3. Pc is the integral of that Gaussian's density over a disk of radius
     equal to the "hard body radius" (HBR) — the sum of the two objects'
     effective combined radii — centered on the miss vector.

Important, disclosed limitation
--------------------------------
Real conjunction assessment uses a covariance matrix derived from orbit
determination (tracking data quality), which is NOT part of the public TLE
format. TLEs give you a best-estimate trajectory, not its uncertainty. This
module therefore uses a *configurable, assumed* isotropic covariance
(default: 1-sigma of a few hundred meters per axis, a rough, admittedly
generic stand-in loosely representative of a LEO TLE-only position error)
so the Pc number is illustrative of the method, not an operational-grade
estimate. A production system would replace this with real covariance from
sources such as Space-Track Conjunction Data Messages (CCSDS 508.0-B-1).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import integrate

# Default combined hard-body radius in meters (rough stand-in for two small
# satellites / debris pieces; real HBR should come from each object's actual
# physical dimensions).
DEFAULT_HBR_M = 20.0

# Default assumed 1-sigma position uncertainty per encounter-plane axis, in
# meters. This is a generic placeholder, NOT derived from real covariance.
DEFAULT_SIGMA_M = 300.0


@dataclass
class PcResult:
    probability: float
    hbr_m: float
    sigma_m: float
    miss_distance_km: float
    is_covariance_assumed: bool = True


def compute_pc(
    miss_distance_km: float,
    hbr_m: float = DEFAULT_HBR_M,
    sigma_m: float = DEFAULT_SIGMA_M,
) -> PcResult:
    """2D-Pc (Foster & Estes, 1992) under a simplifying isotropic-covariance
    assumption, so the encounter-plane integral collapses to a 1D radial
    integral (no correlation between the two in-plane axes):

        Pc = 1 - exp( -HBR^2 / (2 * sigma^2) )   [for a centered miss,
                                                    i.e. miss distance
                                                    treated as the offset
                                                    of the Gaussian mean
                                                    from the HBR-disk
                                                    center]

    We keep the general 2D numerical integral (rather than the closed form
    above) so this is easy to extend to an anisotropic covariance later
    without changing the calling code.
    """
    miss_distance_m = miss_distance_km * 1000.0

    def integrand(x, y):
        r2 = (x - miss_distance_m) ** 2 + y**2
        return np.exp(-r2 / (2 * sigma_m**2))

    # Integrate the Gaussian density over the HBR disk, centered at the
    # origin, with the miss vector offset built into the integrand above.
    def y_bounds(x):
        remaining = hbr_m**2 - x**2
        return (-np.sqrt(remaining), np.sqrt(remaining)) if remaining > 0 else (0, 0)

    integral, _ = integrate.dblquad(
        integrand,
        -hbr_m,
        hbr_m,
        lambda x: y_bounds(x)[0],
        lambda x: y_bounds(x)[1],
    )
    pc = integral / (2 * np.pi * sigma_m**2)

    return PcResult(
        probability=float(pc),
        hbr_m=hbr_m,
        sigma_m=sigma_m,
        miss_distance_km=miss_distance_km,
    )
