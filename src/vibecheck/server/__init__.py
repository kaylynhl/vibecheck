"""FastAPI backend for the mobile app (Step 8).

The FastAPI instance lives at ``vibecheck.server.app:app`` so uvicorn can find
it (``uvicorn vibecheck.server.app:app``). We deliberately do NOT re-export it
from the package init: a top-level ``vibecheck.server.app`` attribute would
shadow the submodule and break tooling that does ``import vibecheck.server.app``.
"""

from vibecheck.server.app import create_app

__all__ = ["create_app"]
