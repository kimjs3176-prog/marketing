"""Vercel entrypoint for FastAPI.

Vercel's Python runtime expects an ASGI app object in the module path defined
in `vercel.json`.
"""

from app.main import app

__all__ = ["app"]
