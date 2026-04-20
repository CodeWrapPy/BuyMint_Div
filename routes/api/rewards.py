from flask import Blueprint, jsonify
from flask_login import login_required, current_user

rewards_api = Blueprint("rewards_api", __name__, url_prefix="/api/rewards")

TIERS = {
    "Seedling": {"min": 0,    "max": 499,  "next": "Sprout",   "perks": ["5% off on first order", "Access to member deals"]},
    "Sprout":   {"min": 500,  "max": 1999, "next": "Grove",    "perks": ["10% off sitewide", "Free delivery on orders ₹300+", "Early access to sales"]},
    "Grove":    {"min": 2000, "max": 4999, "next": "Forest",   "perks": ["15% off sitewide", "Free delivery always", "Priority support", "Exclusive products"]},
    "Forest":   {"min": 5000, "max": None, "next": None,       "perks": ["20% off sitewide", "Free delivery always", "Dedicated account manager", "VIP early access", "Annual gift"]},
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
        next_min = TIERS[next_tier]["min"]
        points_to_next = max(0, next_min - current_user.reward_points)

    progress_pct = 0
    if tier_info["max"]:
        span    = tier_info["max"] - tier_info["min"]
        earned  = current_user.reward_points - tier_info["min"]
        progress_pct = min(100, int(earned / span * 100)) if span > 0 else 100

    return _ok({
        "points":         current_user.reward_points,
        "tier":           current_user.tier,
        "tier_info":      tier_info,
        "next_tier":      next_tier,
        "points_to_next": points_to_next,
        "progress_pct":   progress_pct,
        "all_tiers":      TIERS,
    })
