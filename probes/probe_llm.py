"""LLM probe: text, JSON mode, usage fields, and which parameters the backend accepts.

  python -m probes.probe_llm            # vertex (pre-registered backend)
  python -m probes.probe_llm openai     # exploratory: picks a model from the account's list
  python -m probes.probe_llm nebius
"""
import json, os, sys
from dotenv import load_dotenv
from openai import OpenAI
import config

load_dotenv()
backend = sys.argv[1] if len(sys.argv) > 1 else config.LLM_BACKEND
config.LLM_BACKEND = backend
from llm.auth import endpoint, probe_path  # noqa: E402

result = {"backend": backend}
if backend in config.PROVIDERS:
    prov = config.PROVIDERS[backend]
    key = os.environ.get(prov["key_env"])
    if not key:
        print(f"FAIL {prov['key_env']} not set in .env"); sys.exit(1)
    models, errors = None, []
    for url in prov["base_urls"]:
        try:
            models = sorted(m.id for m in OpenAI(base_url=url, api_key=key, timeout=30).models.list().data)
            result["base_url"] = url
            break
        except Exception as e:
            errors.append(f"{url}: {str(e)[:120]}")
    if not models:
        print("FAIL could not list models\n  " + "\n  ".join(errors)); sys.exit(1)
    chat = [m for m in models if not any(x in m.lower() for x in ("embed", "whisper", "tts", "dall", "image",
                                                                   "audio", "realtime", "moderation", "search"))]
    pick = next((m for pref in prov["model_prefs"] for m in chat if pref in m.lower()), None)
    if not pick:
        print(f"FAIL none of {prov['model_prefs']} in {chat[:20]}"); sys.exit(1)
    result["model"] = pick
    result["n_models_listed"] = len(models)
    base_url, token, model = result["base_url"], key, pick
else:
    try:
        base_url, token, model = endpoint()
    except Exception as e:
        print(f"FAIL {backend} credentials: {str(e)[:200]}"); sys.exit(1)
    result.update(base_url=base_url, model=model)

client = OpenAI(base_url=base_url, api_key=token, timeout=120)
msg = [{"role": "user", "content": "Reply with the single word: ready"}]


def accepts(**kw):
    try:
        r = client.chat.completions.create(model=model, messages=msg, **kw)
        return bool((r.choices[0].message.content or "").strip()), r
    except Exception as e:
        return False, str(e)[:200]


ok, r = accepts()                                     # (a) plain completion returns text
if not ok:
    print(f"FAIL chat completion with {model}: {r}"); sys.exit(1)
result["text"] = True
result["temperature_ok"], _ = accepts(temperature=config.TEMPERATURE)
result["seed_ok"], _ = accepts(seed=1)
result["reasoning_effort_ok"], _ = accepts(reasoning_effort=config.LLM_REASONING_EFFORT)
try:                                                  # (b) JSON mode returns valid JSON
    kw = {"temperature": config.TEMPERATURE} if result["temperature_ok"] else {}
    rj = client.chat.completions.create(model=model, response_format={"type": "json_object"}, **kw,
        messages=[{"role": "user", "content": 'Return JSON {"stance":"neutral","strength":0.5}'}])
    json.loads(rj.choices[0].message.content)
    result["json_mode"] = True
except Exception as e:
    result["json_mode"] = False
    result["json_mode_error"] = str(e)[:200]
u = getattr(r, "usage", None)                         # (c) usage fields for R8 logging
result["usage"] = bool(u and u.prompt_tokens is not None and u.completion_tokens is not None)

config.PROBE_RESULTS.mkdir(parents=True, exist_ok=True)
probe_path(backend).write_text(json.dumps(result, indent=2))
if not result["usage"]:
    print(f"FAIL usage fields missing {result}"); sys.exit(1)
flags = ", ".join(f"{k.removesuffix('_ok')}={'yes' if result[k] else 'no'}"
                  for k in ("temperature_ok", "seed_ok", "reasoning_effort_ok"))
print(f"PASS {backend} {model}: JSON via {'json_object' if result['json_mode'] else 'tolerant parser'}, {flags}")
