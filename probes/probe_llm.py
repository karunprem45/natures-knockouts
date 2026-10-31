"""Phase 0: Gemini via the OpenAI-compatible endpoint. Checks text, JSON mode, usage fields."""
import json, os, sys
from dotenv import load_dotenv
from openai import OpenAI
import config

load_dotenv()
key = os.environ.get("GEMINI_API_KEY")
if not key:
    print("FAIL GEMINI_API_KEY not set (copy .env.example to .env)"); sys.exit(1)
client = OpenAI(base_url=config.LLM_BASE_URL, api_key=key)
result = {"model": config.LLM_MODEL}

try:  # (a) plain completion returns text
    r = client.chat.completions.create(model=config.LLM_MODEL, temperature=config.TEMPERATURE,
        messages=[{"role": "user", "content": "Reply with the single word: ready"}])
    text = (r.choices[0].message.content or "").strip()
    assert text, "empty completion"
    result["text"] = True
except Exception as e:
    print(f"FAIL chat completion: {e}"); sys.exit(1)

try:  # (b) response_format json_object returns valid JSON
    r = client.chat.completions.create(model=config.LLM_MODEL, temperature=config.TEMPERATURE,
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
