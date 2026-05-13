"""
Serves as the application entry point. Initializes the FastAPI web server,
discovers the agents defined in the workflow directory, and exposes them
via HTTP endpoints for interaction.
"""

import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    allow_origins=ALLOWED_ORIGINS,
    web=True,
    auto_create_session=True,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
