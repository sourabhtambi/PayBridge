"""Shim so `uvicorn src.main:app` works."""

from paybridge.api.app import create_app

app = create_app()
