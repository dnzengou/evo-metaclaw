"""evo-metaclaw CLI — capture, summarize, emit."""
from __future__ import annotations

import argparse
import sys

from .emit import post_train, train_payload
from .signals import Signal, SignalStore
from .summarize import summarize_session


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="evo-metaclaw")
    p.add_argument("--db", default="metaclaw.db")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("capture", help="record one signal")
    c.add_argument("session_id")
    c.add_argument("kind")
    c.add_argument("detail")
    c.add_argument("--agent", default="")
    c.add_argument("--score", type=float)

    s = sub.add_parser("summarize", help="draft candidate SKILL.md for a session")
    s.add_argument("session_id")

    e = sub.add_parser("emit", help="summarize + POST to an evo-skillopt worker")
    e.add_argument("session_id")
    e.add_argument("bot_id")
    e.add_argument("--worker", required=True)
    e.add_argument("--token", required=True)

    args = p.parse_args(argv)
    store = SignalStore(args.db)
    try:
        if args.cmd == "capture":
            sig = store.add(Signal(kind=args.kind, session_id=args.session_id,
                                   detail=args.detail, agent=args.agent, score=args.score))
            print(sig.to_json())
            return 0
        if args.cmd == "summarize":
            out = summarize_session(store, args.session_id)
            if out is None:
                print("session too thin — nothing to distill", file=sys.stderr)
                return 1
            print(out)
            return 0
        # emit
        out = summarize_session(store, args.session_id)
        if out is None:
            print("session too thin — nothing to emit", file=sys.stderr)
            return 1
        result = post_train(args.worker, args.token, train_payload(args.bot_id, out))
        print(result)
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
