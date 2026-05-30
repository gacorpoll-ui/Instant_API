"""Live API server runner."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from instantapi.ai.detector import DetectionResult
from instantapi.api.generator import create_api


def run_server(result: DetectionResult, port: int = 3000, host: str = "0.0.0.0") -> None:
    """Start the live API server.

    Args:
        result: Detection result to serve.
        port: Port to listen on.
        host: Host to bind to.
    """
    app = create_api(result)
    uvicorn.run(app, host=host, port=port, log_level="info")


async def get_app(result: DetectionResult) -> FastAPI:
    """Create and return the FastAPI app without starting it.

    Useful for testing or embedding in another app.
    """
    return create_api(result)
