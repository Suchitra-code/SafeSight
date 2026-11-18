"""
Route handler for Mission Control (Command Center) page & analytics APIs (Milestone 4).
Endpoints:
- GET /command-center: Mission Control interactive dashboard UI
- GET /api/command-center/kpis: 5 top KPIs with sparklines & delta
- GET /api/command-center/heatmap: 7x24 hourly violation density
- GET /api/command-center/trends: 14-day compliance vs violation series
- GET /api/command-center/feed: real-time camera violations stream
- GET /api/command-center/zones: zone status for interactive SVG site map
"""
from flask import Blueprint, render_template, request, jsonify
from app.services.command_center_service import (
    get_command_center_kpis,
    get_hourly_heatmap,
    get_trend_data,
    get_live_events_feed,
    get_zone_status_map
)
import config

command_center_bp = Blueprint("command_center", __name__)


@command_center_bp.route("/command-center")
def mission_control():
    """Renders the primary Mission Control interactive dashboard."""
    return render_template(
        "command_center.html",
        active_page="command_center",
        langgraph_version=config.LANGGRAPH_VERSION
    )


@command_center_bp.route("/api/command-center/kpis")
def kpis_api():
    """Returns top KPI strip data with filters applied."""
    filters = {
        "zone": request.args.get("zone"),
        "violationType": request.args.get("violationType"),
        "severity": request.args.get("severity"),
        "dateRange": request.args.get("dateRange")
    }
    return jsonify(get_command_center_kpis(filters))


@command_center_bp.route("/api/command-center/heatmap")
def heatmap_api():
    """Returns 7x24 hourly violation distribution matrix."""
    filters = {
        "zone": request.args.get("zone"),
        "severity": request.args.get("severity")
    }
    return jsonify({"matrix": get_hourly_heatmap(filters)})


@command_center_bp.route("/api/command-center/trends")
def trends_api():
    """Returns 14-day historical trend data."""
    filters = {
        "zone": request.args.get("zone")
    }
    return jsonify(get_trend_data(filters))


@command_center_bp.route("/api/command-center/feed")
def feed_api():
    """Returns latest live violations feed."""
    limit = int(request.args.get("limit", 15))
    return jsonify({"events": get_live_events_feed(limit)})


@command_center_bp.route("/api/command-center/zones")
def zones_api():
    """Returns compliance and violation counts per site zone for SVG map."""
    return jsonify({"zones": get_zone_status_map()})
