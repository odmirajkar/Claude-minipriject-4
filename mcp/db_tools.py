"""
PostgreSQL MCP Tool Wrappers (stub — provided for lab).

These functions return simulated data for the lab environment.
In production, they would call the pg-mcp server via mcp.call().

Students: Do NOT modify this file. Use it as a reference for how
          github_tools.py functions should be structured.
"""
from __future__ import annotations
import random
from datetime import datetime, timezone


def get_overnight_alerts() -> list[dict]:
    """
    Return services that had elevated error rates overnight (00:00–07:00 UTC).
    Simulated for lab — returns realistic-looking data.
    """
    services = ["payments", "orders", "gateway", "notifications", "inventory"]
    alerts = []
    for service in random.sample(services, k=random.randint(0, 3)):
        baseline = round(random.uniform(0.1, 0.5), 3)
        current = round(baseline * random.uniform(1.6, 4.0), 3)
        alerts.append({
            "service":    service,
            "hour_utc":   random.randint(1, 6),
            "error_rate": current,
            "baseline":   baseline,
            "delta_pct":  round((current - baseline) / baseline * 100, 1),
        })
    return sorted(alerts, key=lambda x: x["delta_pct"], reverse=True)


def get_error_rate(service: str, window_minutes: int = 30) -> dict:
    """
    Return the error rate for a service over the last N minutes.
    Simulated for lab.
    """
    baseline = round(random.uniform(0.05, 0.3), 4)
    if window_minutes <= 5:
        # Recent window — may show spike
        multiplier = random.choice([1.0, 1.2, 3.5, 8.0])
    else:
        multiplier = random.uniform(0.9, 1.3)

    current = round(baseline * multiplier, 4)
    return {
        "service":        service,
        "window_minutes": window_minutes,
        "error_rate":     current,
        "baseline":       baseline,
        "requests_total": random.randint(500, 50_000),
        "errors_total":   int(current * random.randint(500, 50_000)),
        "as_of":          datetime.now(timezone.utc).isoformat(),
    }
