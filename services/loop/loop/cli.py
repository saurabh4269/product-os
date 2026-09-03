"""CLI: seed, detect, run, serve."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="loop")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed", help="Generate synthetic warehouse")
    sub.add_parser("detect", help="Run unprompted signal detection")
    sub.add_parser("run", help="Run the warehouse Type A loop until a risk gate")
    sub.add_parser("world", help="Seed the full Product OS world (six fixtures, rooms, memory)")
    p_approve = sub.add_parser("approve", help="Approve an action and verify")
    p_approve.add_argument("action_id")
    p_approve.add_argument("--approver", default="oncall@northstar")
    sub.add_parser("serve", help="Start the API")
    p_export = sub.add_parser("export-demo", help="Write demo JSON for Remotion")
    p_export.add_argument("-o", "--out", default="")
    args = parser.parse_args(argv)

    if args.cmd == "seed":
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "data"))
        from generate import main as gen

        from .config import settings

        gen(settings().warehouse_path())
        return 0

    from .engine import default_engine

    eng = default_engine()
    if args.cmd == "detect":
        signals = eng.detect_signals()
        print(json.dumps([s.model_dump(mode="json") for s in signals], indent=2))
        return 0
    if args.cmd == "run":
        inv = eng.run_until_approval()
        print(json.dumps({"investigation_id": inv.id, "state": inv.state.value}, indent=2))
        return 0
    if args.cmd == "world":
        print(json.dumps(eng.seed_world(), indent=2))
        return 0
    if args.cmd == "approve":
        out = eng.resume_after_approval(args.action_id, args.approver)
        print(json.dumps(out.model_dump(mode="json"), indent=2))
        return 0
    if args.cmd == "serve":
        import uvicorn

        from .config import settings

        uvicorn.run("loop.api:app", host=settings().host, port=settings().port, reload=False)
        return 0
    if args.cmd == "export-demo":
        from .demo_export import write_demo_export

        dest = Path(args.out) if args.out else Path(__file__).resolve().parents[3] / "apps" / "demo" / "public" / "loop.json"
        path = write_demo_export(dest)
        print(path)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
