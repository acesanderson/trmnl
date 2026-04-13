# src/trmnl/cli.py
from __future__ import annotations
import argparse
import os
import sys

import httpx

TRMNL_PORT = 8070


def _resolve_server_url() -> str:
    if url := os.environ.get("TRMNL_SERVER_URL"):
        return url
    from dbclients.discovery.host import get_network_context
    ctx = get_network_context()
    return f"http://{ctx.preferred_host}:{TRMNL_PORT}"


def _get(path: str) -> dict:
    url = _resolve_server_url()
    try:
        resp = httpx.get(f"{url}{path}", timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        print(f"Could not connect to TRMNL server at {url}. Is the service running?")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error {e.response.status_code}: {e.response.json().get('error', str(e))}")
        sys.exit(1)


def _post(path: str, body: dict) -> dict:
    url = _resolve_server_url()
    try:
        resp = httpx.post(f"{url}{path}", json=body, timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        print(f"Could not connect to TRMNL server at {url}. Is the service running?")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error {e.response.status_code}: {e.response.json().get('error', str(e))}")
        sys.exit(1)


def cmd_status(_args: argparse.Namespace) -> None:
    data = _get("/api/control/status")
    print(f"Engine:      {data['engine']}")
    if data.get("sequence"):
        print(f"Sequence:    {' -> '.join(data['sequence'])}")
    print(f"Last served: {data['last_served'] or '(none)'}")


def cmd_list(_args: argparse.Namespace) -> None:
    data = _get("/api/control/engines")
    print("Available engines:")
    for name in data["engines"]:
        print(f"  {name}")


def cmd_engine(args: argparse.Namespace) -> None:
    if args.name is None:
        cmd_list(args)
        return
    body: dict = {"engine": args.name}
    if args.name == "mix":
        if args.sequence:
            body["sequence"] = args.sequence
        else:
            body["sequence"] = _get("/api/control/engines")["engines"]
    data = _post("/api/control/engine", body)
    print(f"OK -- engine: {data['engine']}")
    if data.get("sequence"):
        print(f"Sequence: {' -> '.join(data['sequence'])}")


def cmd_next(_args: argparse.Namespace) -> None:
    data = _post("/api/control/next", {})
    print(f"Advanced -- next image: {data['image']}")


def cmd_reload(_args: argparse.Namespace) -> None:
    data = _post("/api/control/reload", {})
    print(f"Reloaded -- engine: {data['engine']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="trmnl-ctl", description="TRMNL remote control")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show current engine and last served image")
    sub.add_parser("list", help="List available engines")
    sub.add_parser("next", help="Force carousel to advance")
    sub.add_parser("reload", help="Re-read config.yaml and apply without restart")

    p_engine = sub.add_parser("engine", help="Switch active engine (no arg = list engines)")
    p_engine.add_argument("name", nargs="?", default=None, help="Engine name: poem, fantasy, or mix")
    p_engine.add_argument(
        "--sequence",
        nargs="+",
        metavar="ENGINE",
        help="Ordered sequence for mix mode, e.g. --sequence poem poem fantasy",
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    {
        "status": cmd_status,
        "list": cmd_list,
        "engine": cmd_engine,
        "next": cmd_next,
        "reload": cmd_reload,
    }[args.command](args)


if __name__ == "__main__":
    main()
