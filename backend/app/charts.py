"""
Chart planning and construction module.

Uses Gemini LLM to decide what charts to show based on user questions,
then builds chart data structures accordingly.
"""
import json
import logging
from typing import Dict, Any, List

from app.llm import call_llm

logger = logging.getLogger(__name__)


def build_metrics_summary_for_planner(metrics_by_year: Dict[int, Dict[str, float]]) -> str:
    """
    Convert metrics_by_year dict into a short, planner-friendly text.
    
    Example:
      2023: revenue, net_profit, total_assets, total_liabilities
      2024: revenue, net_profit, total_assets, total_liabilities
    """
    if not metrics_by_year:
        return "No metrics available."
    
    lines = []
    for year in sorted(metrics_by_year.keys()):
        metric_names = sorted(metrics_by_year[year].keys())
        if metric_names:
            lines.append(f"{year}: {', '.join(metric_names)}")
    
    return "\n".join(lines) if lines else "No metrics available."


def plan_chart_config(user_question: str, metrics_by_year: Dict[int, Dict[str, float]]) -> Dict[str, Any]:
    """
    Use Gemini (via call_llm) to decide chart config:
      - wants_chart: bool
      - chart_type: "line" | "bar" | "pie" | "none"
      - x_axis: "year" or "metric"
      - metrics: list of metric names (e.g. ["revenue", "net_profit"])
      - aggregation: e.g. "none" or "latest_year"
    """
    metrics_summary = build_metrics_summary_for_planner(metrics_by_year)
    
    system_prompt = """You are a chart planning assistant for a financial dashboard.

You receive:
1) A user's question about financial performance.
2) A summary of what metrics are available by year, such as:
   2023: revenue, net_profit, total_assets, total_liabilities
   2024: revenue, net_profit, total_assets, total_liabilities

Your job is to decide IF a chart should be shown, WHAT metrics to plot, and WHAT chart type is appropriate.

Chart types you can choose:
- "line": for trends over time (e.g. revenue by year).
- "bar": for comparing values across years or across metrics.
- "pie": for showing composition of one year's metrics (e.g. assets vs liabilities).

If the user asks for a "flow chart" or "flowchart", you MUST set chart_type to "none".
We do NOT support actual flowchart visuals; the main assistant will answer with text steps instead.

Rules:
- If the question does not explicitly ask to show/plot/visualize/graph/chart/draw something, set "wants_chart" to false.
- Only use metrics that actually exist in the metrics summary.
- If the user mentions a specific chart type (bar, line, pie), prefer that type.
- If the question is about trends over years → line chart is usually best.
- If the question is about comparing a few values in specific years → bar chart is good.
- If the question is about showing share or distribution for a single year → pie chart is good.
- If a chart would add no value, set "wants_chart" to false.

Return ONLY valid JSON with keys:
  "wants_chart": boolean,
  "chart_type": string, one of "line", "bar", "pie", "none"
  "x_axis": string, either "year" or "metric"
  "metrics": array of metric names (like ["revenue", "net_profit"])
  "aggregation": string, e.g. "none" or "latest_year"
"""

    user_prompt = f"""User's question:
\"\"\"{user_question}\"\"\"

Available metrics by year:
{metrics_summary}

Return JSON only.
"""

    try:
        raw = call_llm(system_prompt, user_prompt)
        
        # Try to extract JSON
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            json_str = raw[start:end]
            config = json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse chart planner JSON: {e}. Response: {raw[:200]}")
            # Fallback conservative config: no chart
            return {
                "wants_chart": False,
                "chart_type": "none",
                "x_axis": "year",
                "metrics": [],
                "aggregation": "none",
            }
        
        # Basic validation & defaults
        wants_chart = bool(config.get("wants_chart"))
        chart_type = config.get("chart_type") or "none"
        x_axis = config.get("x_axis") or "year"
        metrics = config.get("metrics") or []
        aggregation = config.get("aggregation") or "none"
        
        # If chart_type invalid, force none
        if chart_type not in ("line", "bar", "pie"):
            chart_type = "none"
            wants_chart = False
        
        return {
            "wants_chart": wants_chart,
            "chart_type": chart_type,
            "x_axis": x_axis,
            "metrics": metrics,
            "aggregation": aggregation,
        }
        
    except Exception as e:
        logger.exception(f"Error in chart planner: {e}")
        # Fallback: no chart
        return {
            "wants_chart": False,
            "chart_type": "none",
            "x_axis": "year",
            "metrics": [],
            "aggregation": "none",
        }


def build_chart_data_from_plan(
    plan: Dict[str, Any], 
    metrics_by_year: Dict[int, Dict[str, float]]
) -> Dict[str, Any] | None:
    """
    Build chart data structure from planner output.
    Returns a dict with chart_type, years, and series, or None if no valid chart.
    """
    chart_type = plan["chart_type"]
    metrics = plan["metrics"]
    x_axis = plan["x_axis"]
    aggregation = plan["aggregation"]
    
    if not metrics or not metrics_by_year:
        return None
    
    # Use years as sorted keys
    years = sorted(metrics_by_year.keys())
    if not years:
        return None
    
    # We'll support two simple cases:
    # - x_axis == "year": typical line/bar chart over time.
    # - x_axis == "metric" is not implemented for now (can be extended later).
    if x_axis != "year":
        # Fallback: treat as year-based
        x_axis = "year"
    
    # Normalize metric names: convert to lowercase and handle variations
    # Available metric keys in metrics_by_year are: revenue, net_profit, total_assets, total_liabilities
    metric_name_mapping = {
        "revenue": "revenue",
        "net_profit": "net_profit",
        "net profit": "net_profit",
        "total_assets": "total_assets",
        "total assets": "total_assets",
        "assets": "total_assets",
        "total_liabilities": "total_liabilities",
        "total liabilities": "total_liabilities",
        "liabilities": "total_liabilities",
    }
    
    # Normalize requested metrics
    normalized_metrics = []
    for metric_name in metrics:
        # Try exact match first
        if metric_name in metric_name_mapping:
            normalized_metrics.append(metric_name_mapping[metric_name])
        elif metric_name.lower() in metric_name_mapping:
            normalized_metrics.append(metric_name_mapping[metric_name.lower()])
        else:
            # Try to find a match by checking if it's a substring
            found = False
            for key, value in metric_name_mapping.items():
                if metric_name.lower() in key.lower() or key.lower() in metric_name.lower():
                    normalized_metrics.append(value)
                    found = True
                    break
            if not found:
                # Try direct lookup in first year's metrics
                first_year = years[0]
                if metric_name in metrics_by_year.get(first_year, {}):
                    normalized_metrics.append(metric_name)
    
    # Remove duplicates while preserving order
    seen = set()
    normalized_metrics = [m for m in normalized_metrics if m not in seen and not seen.add(m)]
    
    if not normalized_metrics:
        return None
    
    # If aggregation == "latest_year" and chart_type == "pie", we only use the latest year
    if chart_type == "pie":
        target_year = years[-1]  # Use latest year
        series = []
        
        for metric_name in normalized_metrics:
            val = metrics_by_year.get(target_year, {}).get(metric_name)
            if val is not None:
                series.append({
                    "label": metric_name.replace("_", " ").title(),
                    "values": [val],  # we'll use only index 0 in the frontend
                })
        
        if not series:
            return None
        
        return {
            "chart_type": "pie",
            "years": [target_year],
            "series": series,
        }
    
    # For line/bar: build series across years
    series = []
    for metric_name in normalized_metrics:
        values = []
        for y in years:
            val = metrics_by_year.get(y, {}).get(metric_name)
            values.append(val if val is not None else 0.0)
        
        # Only add series if at least one value is non-zero
        if any(v != 0.0 for v in values):
            series.append({
                "label": metric_name.replace("_", " ").title(),
                "values": values,
            })
    
    if not series:
        return None
    
    return {
        "chart_type": chart_type,  # "line" or "bar"
        "years": years,
        "series": series,
    }

