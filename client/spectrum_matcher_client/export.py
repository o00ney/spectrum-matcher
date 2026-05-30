"""Export utilities for results, data, and plots."""

import csv
import json


def export_results_csv(results, filepath):
    """Export results table to CSV with Name and Probability columns."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Probability"])
        for r in results:
            writer.writerow([r.get("name", ""), r.get("probability", "")])


def export_results_json(full_data, filepath):
    """Export full response data including spectrum arrays to JSON."""
    # convert numpy types if present
    cleaned = _sanitize_for_json(full_data)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)


def export_plot_png(plot_widget, filepath):
    """Save current plot figure as a high-resolution PNG."""
    plot_widget.save_figure(filepath)


def _sanitize_for_json(obj):
    """Recursively convert numpy numeric types to plain Python types."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if hasattr(obj, "item"):
        return obj.item()
    return obj
