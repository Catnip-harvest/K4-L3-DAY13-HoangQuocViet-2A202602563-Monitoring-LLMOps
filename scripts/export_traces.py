"""Export recent Langfuse traces from the personal project as readable text evidence.

    python scripts/export_traces.py --minutes 60                 # one row per trace
    python scripts/export_traces.py --correlation-id req-1a2b3c4d  # span tree of one request

Uses GET /api/public/v2/observations (the legacy /traces API is closed to organizations
created after 2026-09-16). Keys come from .env and are never printed; the SDK's public key,
which Langfuse copies into observation metadata, is dropped before output.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio  # noqa: E402

FIELDS = "core,basic,time,usage,model,metadata,prompt"
SAFE_METADATA_KEYS = ("correlation_id", "feature", "model", "prompt_name", "prompt_label", "prompt_version", "prompt_source", "doc_count", "ttft_ms")


def fetch_observations(minutes: int) -> list[dict]:
    env = dotenv_values(REPO_ROOT / ".env")
    now = datetime.now(timezone.utc)
    params = {
        "fromStartTime": (now - timedelta(minutes=minutes)).isoformat(),
        "toStartTime": now.isoformat(),
        "limit": 100,
        "fields": FIELDS,
    }
    observations: list[dict] = []
    with httpx.Client(
        base_url=env["LANGFUSE_BASE_URL"],
        auth=(env["LANGFUSE_PUBLIC_KEY"], env["LANGFUSE_SECRET_KEY"]),
        timeout=30,
    ) as client:
        while True:
            response = client.get("/api/public/v2/observations", params=params)
            response.raise_for_status()
            body = response.json()
            observations.extend(body["data"])
            cursor = (body.get("meta") or {}).get("cursor")
            if not cursor or not body["data"]:
                return observations
            params["cursor"] = cursor


def safe_metadata(observation: dict) -> dict:
    metadata = observation.get("metadata") or {}
    return {key: metadata[key] for key in SAFE_METADATA_KEYS if key in metadata}


def group_by_trace(observations: list[dict]) -> dict[str, list[dict]]:
    traces: dict[str, list[dict]] = defaultdict(list)
    for observation in observations:
        traces[observation["traceId"]].append(observation)
    return traces


def ms(observation: dict | None) -> str:
    if not observation or observation.get("latency") is None:
        return "-"
    return f"{observation['latency'] * 1000:.0f}"


def first(observations: list[dict], name: str) -> dict | None:
    return next((o for o in observations if o["name"] == name), None)


def print_trace_table(traces: dict[str, list[dict]]) -> None:
    rows = []
    for trace_id, observations in traces.items():
        root = next((o for o in observations if o.get("isRootObservation")), None)
        if root is None:
            continue
        generation = first(observations, "llm-generation")
        retrieval = first(observations, "retrieval")
        root_meta = safe_metadata(root)
        worst_level = "ERROR" if any(o.get("level") == "ERROR" for o in observations) else "OK"
        rows.append((
            root["startTime"],
            trace_id,
            root_meta.get("correlation_id", "-"),
            ms(root),
            ms(retrieval),
            ms(generation),
            f"{generation.get('inputUsage', '-')}/{generation.get('outputUsage', '-')}" if generation else "-",
            f"{generation['totalCost']:.6f}" if generation and generation.get("totalCost") is not None else "-",
            f"{root_meta.get('prompt_name', '-')}@{root_meta.get('prompt_label', '-')} v{root_meta.get('prompt_version', '-')}",
            worst_level,
        ))
    rows.sort()
    header = ("start_utc", "trace_id", "correlation_id", "total_ms", "retrieval_ms", "llm_ms", "tok_in/out", "cost_usd", "prompt", "status")
    print(" | ".join(header))
    for row in rows:
        print(" | ".join(str(cell) for cell in row))
    print(f"\n{len(rows)} traces")


def print_tree(observations: list[dict]) -> None:
    children: dict[str | None, list[dict]] = defaultdict(list)
    for observation in observations:
        children[observation.get("parentObservationId")].append(observation)

    def walk(parent_id: str | None, depth: int) -> None:
        for observation in sorted(children[parent_id], key=lambda o: o["startTime"]):
            details = [
                f"{observation['type']} {observation['name']}",
                f"{ms(observation)} ms",
                f"level={observation.get('level')}",
            ]
            if observation.get("statusMessage"):
                details.append(f"status={observation['statusMessage']!r}")
            if observation.get("model"):
                details.append(f"model={observation['model']}")
            if observation.get("usageDetails"):
                details.append(f"usage={observation['usageDetails']}")
            if observation.get("totalCost") is not None:
                details.append(f"cost_usd={observation['totalCost']}")
            if observation.get("timeToFirstToken") is not None:
                details.append(f"ttft_s={observation['timeToFirstToken']}")
            if observation.get("promptName"):
                details.append(f"prompt={observation['promptName']} v{observation.get('promptVersion')}")
            print("  " * depth + "- " + " | ".join(details))
            metadata = safe_metadata(observation)
            if metadata:
                print("  " * depth + f"    metadata={metadata}")
            walk(observation["id"], depth + 1)

    walk(None, 0)


def main() -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--correlation-id")
    parser.add_argument("--trace-id")
    args = parser.parse_args()

    traces = group_by_trace(fetch_observations(args.minutes))
    if not (args.correlation_id or args.trace_id):
        print_trace_table(traces)
        return 0

    for trace_id, observations in traces.items():
        correlation_ids = {safe_metadata(o).get("correlation_id") for o in observations}
        if trace_id == args.trace_id or args.correlation_id in correlation_ids:
            root = next((o for o in observations if o.get("isRootObservation")), observations[0])
            print(f"trace_id={trace_id}  user_id_hash={root.get('userId')}  session_id={root.get('sessionId')}  env={root.get('environment')}")
            print_tree(observations)
            return 0
    print("No matching trace in the window (Langfuse ingestion can lag a few seconds).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
