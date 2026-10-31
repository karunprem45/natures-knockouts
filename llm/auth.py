"""Credentials for the OpenAI-compatible Gemini endpoint, for either backend in config."""
import os
import threading
import config

_lock = threading.Lock()
_creds = None


def endpoint():
    """Return (base_url, bearer_token, model_name). Vertex tokens refresh when near expiry."""
    if config.LLM_BACKEND == "api_key":
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set (copy .env.example to .env)")
        return config.LLM_BASE_URL, key, config.LLM_MODEL
    global _creds
    import google.auth
    import google.auth.transport.requests
    with _lock:
        if _creds is None:
            _creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"],
                                            quota_project_id=config.GCP_PROJECT)
        if not _creds.valid:
            _creds.refresh(google.auth.transport.requests.Request())
        return config.VERTEX_BASE_URL, _creds.token, f"google/{config.LLM_MODEL}"
