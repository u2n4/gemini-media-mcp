"""Offline-only tests: no credentials, dotenv loading, real SDK clients or HTTP."""
import os

import httpx
import pytest
from google import genai

for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY_BACKUP"):
    os.environ.pop(key, None)
os.environ["PYTHON_DOTENV_DISABLED"] = "1"


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY_BACKUP"):
        monkeypatch.delenv(key, raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("Tests must use a fake client; network is forbidden")

    monkeypatch.setattr(genai, "Client", blocked)
    monkeypatch.setattr(httpx.Client, "send", blocked)
    monkeypatch.setattr(httpx.AsyncClient, "send", blocked)
