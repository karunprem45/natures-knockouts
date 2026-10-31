"""Credentials and capabilities for every OpenAI-compatible backend.

vertex   Gemini on Vertex AI via Application Default Credentials (all pre-registered arms)
api_key  Gemini API with GEMINI_API_KEY
openai   OpenAI with OPENAI_API_KEY            (exploratory)
nebius   Nebius-hosted open model, NEBIUS_API_KEY (exploratory)
"""
import json, os
import threading
import config

_lock = threading.Lock()
_creds = None


def probe_path(backend=None):
    backend = backend or config.LLM_BACKEND
    return config.PROBE_RESULTS / ("llm.json" if backend == "vertex" else f"llm_{backend}.json")


def capabilities(backend=None):
    """What the backend's probe found: model, base_url, and which parameters it accepts."""
    p = probe_path(backend)
    return json.loads(p.read_text()) if p.exists() else {}


def endpoint():
    """Return (base_url, bearer_token, model_name). Vertex tokens refresh when near expiry."""
    backend = config.LLM_BACKEND
    if backend == "api_key":
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set (copy .env.example to .env)")
        return config.LLM_BASE_URL, key, config.LLM_MODEL
    if backend in config.PROVIDERS:
        prov = config.PROVIDERS[backend]
        key = os.environ.get(prov["key_env"])
        if not key:
            raise RuntimeError(f"{prov['key_env']} not set in .env")
        caps = capabilities(backend)
        if not caps.get("model"):
            raise RuntimeError(f"run `python -m probes.probe_llm {backend}` first to pick a model")
        return caps["base_url"], key, caps["model"]
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
