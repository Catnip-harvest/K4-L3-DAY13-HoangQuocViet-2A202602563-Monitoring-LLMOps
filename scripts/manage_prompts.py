"""Create, promote and roll back the `day13-chat` prompt in the personal Langfuse project.

    python scripts/manage_prompts.py create            # v1 (baseline+production), v2 (candidate)
    python scripts/manage_prompts.py promote --version 2
    python scripts/manage_prompts.py promote --version 1   # rollback
    python scripts/manage_prompts.py show

Keys are read from .env by python-dotenv and never printed.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio  # noqa: E402
from app.prompt_management import DEFAULT_PROMPT_TEMPLATE  # noqa: E402

PROMPT_V1 = DEFAULT_PROMPT_TEMPLATE
# v2 changes only the answer format, so any difference in a trace is attributable to it.
PROMPT_V2 = DEFAULT_PROMPT_TEMPLATE + "\nAnswer in at most 3 short sentences, using only the Docs above."


def prompt_name() -> str:
    return os.getenv("LANGFUSE_PROMPT_NAME", "day13-chat")


def existing_versions(client) -> list:
    versions = []
    version = 1
    while True:
        try:
            versions.append(client.get_prompt(prompt_name(), version=version, cache_ttl_seconds=0, max_retries=0))
        except Exception:
            return versions
        version += 1


def show(client) -> None:
    versions = existing_versions(client)
    if not versions:
        print(f"No versions of '{prompt_name()}' yet.")
    for prompt in versions:
        print(f"{prompt_name()} v{prompt.version}  labels={sorted(prompt.labels)}")


def create(client) -> None:
    if existing_versions(client):
        print("Prompt already exists; not creating duplicates.")
        show(client)
        return
    client.create_prompt(
        name=prompt_name(),
        prompt=PROMPT_V1,
        labels=["baseline", "production"],
        type="text",
        commit_message="v1 baseline: lab contract template",
    )
    client.create_prompt(
        name=prompt_name(),
        prompt=PROMPT_V2,
        labels=["candidate"],
        type="text",
        commit_message="v2 candidate: cap answers at 3 sentences",
    )
    show(client)


def promote(client, version: int) -> None:
    # A label lives on exactly one version, so moving `production` here also removes it
    # from the version that had it. Promote and rollback are the same operation.
    client.update_prompt(name=prompt_name(), version=version, new_labels=["production"])
    show(client)


def main() -> int:
    configure_utf8_stdio()
    load_dotenv(REPO_ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("create")
    sub.add_parser("show")
    promote_parser = sub.add_parser("promote")
    promote_parser.add_argument("--version", type=int, required=True)
    args = parser.parse_args()

    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        print("LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set in .env")
        return 1

    from langfuse import get_client

    client = get_client()
    if args.command == "create":
        create(client)
    elif args.command == "show":
        show(client)
    else:
        promote(client, args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
