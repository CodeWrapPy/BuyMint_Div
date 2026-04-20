from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import TIER_THRESHOLDS

rewards_api = Blueprint("rewards_api", __name__, url_prefix="/api/rewards")

# BUG FIX #19: TIERS was a standalone dict defined only here with hardcoded
# threshold values that had to be manually kept in sync with the magic numbers
# in models.py User.update_tier(). If one changed, the other would silently
# diverge and users would be shown incorrect progress bars / tier labels.
# Now the thresholds come from models.TIER_THRESHOLDS — one source of truth.
TIERS = {
    "Seedling": {
        "min":   TIER_THRESHOLDS["Seedling"],
        "max":   TIER_THRESHOLDS["Sprout"],    # exclusive upper bound
        "next":  "Sprout",
        "perks": ["5% off on first order", "Access to member deals"],
    },
    "Sprout": {
        "min":   TIER_THRESHOLDS["Sprout"],
        "max":   TIER_THRESHOLDS["Grove"],
        "next":  "Grove",
        "perks": ["10% off sitewide", "Free delivery on orders ₹300+", "Early access to sales"],
    },
    "Grove": {
        "min":   TIER_THRESHOLDS["Grove"],
        "max":   TIER_THRESHOLDS["Forest"],
        "next":  "Forest",
        "perks": ["15% off sitewide", "Free delivery always", "Priority support", "Exclusive products"],
    },
    "Forest": {
        "min":   TIER_THRESHOLDS["Forest"],
        "max":   None,
        "next":  None,
        "perks": ["20% off sitewide", "Free delivery always", "Dedicated account manager", "VIP early access", "Annual gift"],
    },
}


def _ok(data, status=200):
    return jsonify({"success": True, **data}), status


@rewards_api.route("/", methods=["GET"])
@login_required
def get_rewards():
    tier_info = TIERS.get(current_user.tier, TIERS["Seedling"])
    next_tier = tier_info.get("next")

    points_to_next = None
    if next_tier:
        points_to_next = max(0, TIERS[next_tier]["min"] - current_user.reward_points)

    # BUG FIX #20: progress_pct was calculated using tier_info["max"] as the
    # span endpoint, but in the old code "max" was 499 for Seedling while the
    # actual promotion threshold was 500 — so the bar maxed out at 99.8% rather
    # than 100% just before the tier upgrade.  Using "min of next tier" as the
    # exclusive ceiling fixes the off-by-one cleanly.
    progress_pct = 0
    if next_tier:
        tier_min = tier_info["min"]
        tier_max = TIERS[next_tier]["min"]   # exclusive: this is where next tier starts
        span     = tier_max - tier_min
        earned   = current_user.reward_points - tier_min
        progress_pct = min(100, int(earned / span * 100)) if span > 0 else 100
    elif tier_info["max"] is None:
        # Top-tier (Forest) — always 100%
        progress_pct = 100

    return _ok({
        "points":         current_user.reward_points,
        "tier":           current_user.tier,
        "tier_info":      tier_info,
        "next_tier":      next_tier,
        "points_to_next": points_to_next,
        "progress_pct":   progress_pct,
        "all_tiers":      TIERS,
    })
