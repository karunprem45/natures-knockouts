"""Phase 0: Gemini via the OpenAI-compatible endpoint. Checks text, JSON mode, usage fields."""
import json, sys
from dotenv import load_dotenv
from openai import OpenAI
import config
from llm.auth import endpoint

load_dotenv()
try:
    base_url, token, model = endpoint()
except Exception as e:
    print(f"FAIL {config.LLM_BACKEND} credentials: {str(e)[:200]}"); sys.exit(1)
client = OpenAI(base_url=base_url, api_key=token)
result = {"backend": config.LLM_BACKEND, "model": model}

try:  # (a) plain completion returns text
    r = client.chat.completions.create(model=model, temperature=config.TEMPERATURE,
        messages=[{"role": "user", "content": "Reply with the single word: ready"}])
    text = (r.choices[0].message.content or "").strip()
    assert text, "empty completion"
    result["text"] = True
except Exception as e:
    print(f"FAIL chat completion: {e}"); sys.exit(1)

try:  # (b) response_format json_object returns valid JSON
    r = client.chat.completions.create(model=model, temperature=config.TEMPERATURE,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": 'Return JSON {"stance":"neutral","strength":0.5}'}])
    json.loads(r.choices[0].message.content)
    result["json_mode"] = True
except Exception as e:
    result["json_mode"] = False
    result["json_mode_error"] = str(e)[:200]

# (c) token usage present (needed for R8 logging)
u = getattr(r, "usage", None)
result["usage"] = bool(u and u.prompt_tokens is not None and u.completion_tokens is not None)

config.PROBE_RESULTS.mkdir(parents=True, exist_ok=True)
(config.PROBE_RESULTS / "llm.json").write_text(json.dumps(result, indent=2))
if not result["usage"]:
    print(f"FAIL usage fields missing {result}"); sys.exit(1)
mode = "json_object" if result["json_mode"] else "prompt-only JSON (tolerant parser)"
print(f"PASS text ok, JSON via {mode}, usage ok")
