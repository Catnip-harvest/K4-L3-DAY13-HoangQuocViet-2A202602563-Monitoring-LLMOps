"""Render the six-panel Day 13 dashboard from data/logs.jsonl.

The panel list, units, time range and thresholds are read from config/dashboard.yaml,
so the picture always follows the graded contract instead of a second copy of it.

    python scripts/build_dashboard.py --out submission/evidence/11-dashboard-overview.png
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio  # noqa: E402
from app.metrics import percentile  # noqa: E402
from scripts.validate_dashboard import load_dashboard_config  # noqa: E402

THRESHOLD_STYLE = {"color": "#c0392b", "linestyle": "--", "linewidth": 1.2}
SERIES_COLORS = ["#2f6db3", "#e08a1e", "#5b8c5a"]


def load_events(log_path: Path) -> list[dict]:
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        record["_ts"] = datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))
        events.append(record)
    return events


def minute_of(event: dict) -> datetime:
    return event["_ts"].replace(second=0, microsecond=0)


def by_minute(events: list[dict]) -> dict[datetime, list[dict]]:
    buckets: dict[datetime, list[dict]] = defaultdict(list)
    for event in events:
        buckets[minute_of(event)].append(event)
    return dict(sorted(buckets.items()))


def draw_threshold(ax, panel: dict, label_prefix: str = "SLO") -> None:
    threshold = panel["threshold"]
    word = "max" if threshold["operator"] == "lte" else "min"
    ax.axhline(
        threshold["value"],
        label=f"{label_prefix} {word} {threshold['value']} ({threshold['aggregation']})",
        **THRESHOLD_STYLE,
    )


def status_of(value: float, panel: dict) -> str:
    threshold = panel["threshold"]
    ok = value <= threshold["value"] if threshold["operator"] == "lte" else value >= threshold["value"]
    return "OK" if ok else "BREACH"


def panel_latency(ax, panel, responses):
    times = [e["_ts"] for e in responses]
    latencies = [e["latency_ms"] for e in responses]
    ttfts = [e["ttft_ms"] for e in responses]
    ax.plot(times, latencies, "o", ms=3, color=SERIES_COLORS[0], label="latency_ms per request")
    ax.plot(times, ttfts, "o", ms=3, color=SERIES_COLORS[1], label="ttft_ms per request")
    draw_threshold(ax, panel)
    p50, p95, p99 = (percentile(latencies, p) for p in (50, 95, 99))
    ttft_p95 = percentile(ttfts, 95)
    return f"P50 {p50:.0f} · P95 {p95:.0f} · P99 {p99:.0f} · TTFT P95 {ttft_p95:.0f} ms", p95


def panel_traffic(ax, panel, received):
    buckets = by_minute(received)
    ax.bar(list(buckets), [len(v) for v in buckets.values()], width=1 / 1440 * 0.8, color=SERIES_COLORS[0], label="requests per minute")
    draw_threshold(ax, panel)
    active_minutes = max(1, len(buckets))
    rate = len(received) / active_minutes
    return f"{len(received)} requests · {rate:.1f} req/min over active minutes", rate


def panel_errors(ax, panel, received, failed, tool_events):
    received_by_minute = by_minute(received)
    failed_by_minute = Counter(minute_of(e) for e in failed)
    minutes = list(received_by_minute)
    error_pct = [failed_by_minute[m] / len(received_by_minute[m]) * 100 for m in minutes]
    ax.plot(minutes, error_pct, "o-", ms=3, color=SERIES_COLORS[0], label="error rate %")

    tool_by_minute = by_minute(tool_events)
    tool_pct = [
        sum(1 for e in tool_by_minute.get(m, []) if e["tool_success"]) / len(tool_by_minute[m]) * 100
        for m in minutes
        if tool_by_minute.get(m)
    ]
    tool_minutes = [m for m in minutes if tool_by_minute.get(m)]
    ax.plot(tool_minutes, tool_pct, "s-", ms=3, color=SERIES_COLORS[2], label="retrieval success %")
    draw_threshold(ax, panel, "error SLO")
    ax.set_ylim(-5, 105)

    total_error_pct = len(failed) / max(1, len(received)) * 100
    success_pct = sum(1 for e in tool_events if e["tool_success"]) / max(1, len(tool_events)) * 100
    breakdown = ", ".join(f"{k}={v}" for k, v in Counter(e.get("error_type") for e in failed).items()) or "none"
    return f"error {total_error_pct:.1f}% · retrieval ok {success_pct:.1f}% · {breakdown}", total_error_pct


def panel_cost(ax, panel, responses):
    buckets = by_minute(responses)
    per_minute = [sum(e["cost_usd"] for e in v) for v in buckets.values()]
    ax.bar(list(buckets), per_minute, width=1 / 1440 * 0.8, color=SERIES_COLORS[0], label="cost per minute (usd)")
    cumulative, running = [], 0.0
    for value in per_minute:
        running += value
        cumulative.append(running)
    ax.plot(list(buckets), cumulative, "o-", ms=3, color=SERIES_COLORS[1], label="cumulative (usd)")
    draw_threshold(ax, panel, "budget")
    total = sum(e["cost_usd"] for e in responses)
    avg = total / max(1, len(responses))
    ax.set_yscale("symlog", linthresh=0.01)
    return f"total {total:.4f} usd · avg {avg:.5f} usd/request", total


def panel_tokens(ax, panel, responses):
    buckets = by_minute(responses)
    tokens_in = [sum(e["tokens_in"] for e in v) for v in buckets.values()]
    tokens_out = [sum(e["tokens_out"] for e in v) for v in buckets.values()]
    width = 1 / 1440 * 0.8
    ax.bar(list(buckets), tokens_in, width=width, color=SERIES_COLORS[0], label="tokens_in per minute")
    ax.bar(list(buckets), tokens_out, width=width, bottom=tokens_in, color=SERIES_COLORS[1], label="tokens_out per minute")
    draw_threshold(ax, panel, "window")
    total_in = sum(e["tokens_in"] for e in responses)
    total_out = sum(e["tokens_out"] for e in responses)
    ax.set_yscale("symlog", linthresh=1000)
    return f"in {total_in:,} · out {total_out:,} tokens in window", max(total_in, total_out)


def panel_quality(ax, panel, responses):
    buckets = by_minute(responses)
    means = [sum(e["quality_score"] for e in v) / len(v) for v in buckets.values()]
    ax.plot(list(buckets), means, "o-", ms=3, color=SERIES_COLORS[0], label="mean quality_score per minute")
    draw_threshold(ax, panel)
    ax.set_ylim(0, 1.05)
    overall = sum(e["quality_score"] for e in responses) / max(1, len(responses))
    return f"mean {overall:.3f}", overall


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--logs", type=Path, default=REPO_ROOT / "data" / "logs.jsonl")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "dashboard.yaml")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "submission" / "evidence" / "11-dashboard-overview.png")
    parser.add_argument("--title-suffix", default="", help="Short note shown in the title, e.g. 'rag_slow practice'")
    parser.add_argument(
        "--minutes",
        type=int,
        help="Zoom window for incident close-ups; the overview keeps the contract's time_range_minutes",
    )
    args = parser.parse_args()

    dashboard = load_dashboard_config(args.config)["dashboard"]
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    events = load_events(args.logs)
    if not events:
        print(f"No events in {args.logs}")
        return 1

    window_end = max(e["_ts"] for e in events)
    window_minutes = args.minutes or dashboard["time_range_minutes"]
    window_start = window_end - timedelta(minutes=window_minutes)
    events = [e for e in events if e["_ts"] >= window_start]
    received = [e for e in events if e.get("event") == "request_received"]
    responses = [e for e in events if e.get("event") == "response_sent"]
    failed = [e for e in events if e.get("event") == "request_failed"]
    tool_events = [e for e in events if e.get("tool_success") is not None]

    fig, axes = plt.subplots(3, 2, figsize=(16, 13))
    renderers = [
        ("latency", lambda ax, p: panel_latency(ax, p, responses)),
        ("traffic", lambda ax, p: panel_traffic(ax, p, received)),
        ("errors", lambda ax, p: panel_errors(ax, p, received, failed, tool_events)),
        ("cost", lambda ax, p: panel_cost(ax, p, responses)),
        ("tokens", lambda ax, p: panel_tokens(ax, p, responses)),
        ("quality", lambda ax, p: panel_quality(ax, p, responses)),
    ]
    summary_lines = []
    for ax, (panel_id, render) in zip(axes.flat, renderers):
        panel = panels[panel_id]
        headline, value = render(ax, panel)
        state = status_of(value, panel)
        ax.set_title(f"{panel['title']}  [{panel['unit']}]\n{headline}  —  {state}", fontsize=10, loc="left")
        ax.set_ylabel(panel["unit"])
        ax.set_xlim(window_start, window_end + timedelta(minutes=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8, loc="upper left")
        summary_lines.append(f"{panel_id:8} {state:6} {headline}")

    suffix = f" · {args.title_suffix}" if args.title_suffix else ""
    fig.suptitle(
        f"{dashboard['title']}{suffix}\n"
        f"Last {window_minutes} min · {window_start:%Y-%m-%d %H:%M}–{window_end:%H:%M} UTC · "
        f"refresh {dashboard['refresh_seconds']}s · source {args.logs.name} ({len(events)} events)",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=110)
    print(f"Wrote {args.out}")
    print("\n".join(summary_lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
