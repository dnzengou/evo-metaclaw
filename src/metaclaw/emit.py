"""Emission contract for evo-skillopt.

Single responsibility boundary: evo-metaclaw produces payloads in the
worker's /train shape; evo-skillopt owns training, gating, rollback.
Never duplicate gate logic here.
"""
from __future__ import annotations

import json
import urllib.request


def train_payload(bot_id: str, skill_md: str, eval_cases: list[dict] | None = None) -> dict:
    """Build a /train request body. eval_cases are held-out cases in
    evo-skillopt's suite shape; empty list means 'train but expect the
    gate to reject' — useful for dry runs of the pipeline itself."""
    if not bot_id:
        raise ValueError("bot_id required")
    if not skill_md.strip():
        raise ValueError("skill_md must be non-empty")
    return {
        "bot_id": bot_id,
        "skill_md": skill_md,
        "eval_cases": eval_cases or [],
        "source": "evo-metaclaw",
    }


def post_train(worker_url: str, token: str, payload: dict, timeout_s: float = 30.0) -> dict:
    """POST a payload to an evo-skillopt worker. Fail loud: a caller
    that can't reach the trainer must know, not silently drop skills."""
    url = worker_url.rstrip("/") + "/train"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    # worker URL is operator config, not user input
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode())
