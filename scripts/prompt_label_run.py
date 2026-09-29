"""Send one /chat request through the real app with a chosen prompt label.

    python scripts/prompt_label_run.py --label baseline
    python scripts/prompt_label_run.py --label candidate

The label is read per request from LANGFUSE_PROMPT_LABEL, so this runs the FastAPI app
in-process (same middleware, logging and tracing as the server) instead of restarting
uvicorn once per label.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_MESSAGE = "Explain why metrics traces and logs work together"


async def send(message: str) -> httpx.Response:
    from app.main import app
    from app.tracing import get_langfuse_client

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
        response = await client.post(
            "/chat",
            json={"user_id": "u-prompt-ab", "session_id": "s-prompt-ab", "feature": "qa", "message": message},
        )
    get_langfuse_client().flush()
    return response


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True)
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    load_dotenv(REPO_ROOT / ".env")
    os.environ["LANGFUSE_PROMPT_LABEL"] = args.label

    response = asyncio.run(send(args.message))
    body = response.json()
    print(f"label={args.label} status={response.status_code} correlation_id={body.get('correlation_id')}")
    return 0 if response.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
