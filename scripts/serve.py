"""Run the VibeCheck FastAPI backend with uvicorn.

Defaults:
    host    0.0.0.0     bind on all interfaces so an iPhone on the same Wi-Fi
                        can hit the laptop's LAN IP
    port    8000
    reload  true (dev)

Override with env vars or CLI flags:
    VIBECHECK_HOST, VIBECHECK_PORT, VIBECHECK_RELOAD
    python scripts/serve.py --port 8001 --no-reload
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
# uvicorn --reload spawns worker processes that re-import the app; export
# PYTHONPATH so they can find the ``vibecheck`` package too. (Without this,
# reload mode fails with ModuleNotFoundError on every restart.)
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if str(SRC) not in _existing_pythonpath.split(os.pathsep):
    os.environ["PYTHONPATH"] = (
        f"{SRC}{os.pathsep}{_existing_pythonpath}" if _existing_pythonpath else str(SRC)
    )


def _lan_ip() -> str | None:
    """Best-effort detection of the local LAN IP (for the mobile dev hint)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(0.1)
            sock.connect(("8.8.8.8", 53))
            return sock.getsockname()[0]
    except OSError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("VIBECHECK_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port", type=int, default=int(os.getenv("VIBECHECK_PORT", "8000"))
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable autoreload (use for benchmarking + production).",
    )
    args = parser.parse_args()

    reload_env = os.getenv("VIBECHECK_RELOAD", "1") not in {"0", "false", "False"}
    reload_enabled = (not args.no_reload) and reload_env

    lan_ip = _lan_ip()
    print(f"[serve] backend booting on {args.host}:{args.port}")
    print("[serve] local:    http://localhost:{}".format(args.port))
    if lan_ip:
        print(f"[serve] LAN:      http://{lan_ip}:{args.port}")
        print(
            "[serve] mobile:   set EXPO_PUBLIC_API_URL="
            f"http://{lan_ip}:{args.port} in mobile/.env to use this from your phone"
        )

    import uvicorn

    uvicorn.run(
        "vibecheck.server.app:app",
        host=args.host,
        port=args.port,
        reload=reload_enabled,
        log_level="info",
    )


if __name__ == "__main__":
    main()
