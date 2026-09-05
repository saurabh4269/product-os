"""CLI helper — create LOOP orchestrator on GEAP Agent Runtime."""

from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deploy LOOP orchestrator to GEAP Agent Runtime")
    parser.add_argument("--create", action="store_true", help="Create a new Reasoning Engine")
    parser.add_argument("--list", action="store_true", help="List existing Reasoning Engines")
    parser.add_argument("--smoke", action="store_true", help="Smoke query live Agent Engine via async_stream_query")
    parser.add_argument("--display-name", default="loop-incident-orchestrator")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args(argv)
    if not args.create and not args.list and not args.smoke:
        parser.error("Use --create, --list, or --smoke")

    os.environ.setdefault("LOOP_GEAP_ENABLED", "1")
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        print("GOOGLE_CLOUD_PROJECT is required", file=sys.stderr)
        return 2

    from loop.engine import default_engine
    from loop.geap_runtime import create_agent_engine, geap_staging_bucket, list_agent_engines, smoke_query, status

    if args.smoke:
        os.environ.setdefault("LOOP_GEAP_ENABLED", "1")
        os.environ.setdefault(
            "LOOP_GEAP_AGENT_ENGINE_ID",
            "projects/mystical-timing-442601-q8/locations/us-central1/reasoningEngines/7709236223511887872",
        )
        result = smoke_query()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("ok" if result.get("ok") else "fail", result.get("reply") or result.get("error"))
        return 0 if result.get("ok") else 1

    if args.list:
        rows = list_agent_engines()
        if args.json:
            print(json.dumps({"engines": rows}, indent=2))
        else:
            for row in rows:
                print(row.get("resource_name") or row.get("agent_engine_id"))
        return 0

    eng = default_engine()
    print(f"GEAP deploy: project={status()['project']} region={status()['region']} bucket={geap_staging_bucket()}")
    result = create_agent_engine(eng, display_name=args.display_name)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Created Agent Engine: {result['resource_name']} (model={result.get('model_id')})")
        print(f"Set LOOP_GEAP_AGENT_ENGINE_ID={result['resource_name']}")
        print("Then redeploy main loop with LOOP_GEAP_ENABLED=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
