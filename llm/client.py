"""The single chokepoint for every LLM call (R1, R4, R8, R9). Thread-safe."""
import json, random, re, threading, time
from datetime import datetime, timezone
import openai
from openai import OpenAI
import config
from llm import guards
from llm.auth import endpoint

JSON_NUDGE = "\n\nReturn ONLY one JSON object matching the schema. No prose, no code fences."


def parse_json(text, unwrap_single=True):
    """Tolerant parse: strips code fences, takes the outermost {...}, and unwraps a one-item
    list (Gemini sometimes returns [ {...} ] even in JSON mode)."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise
    if unwrap_single and isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        return parsed[0]
    return parsed


class LLMClient:
    def __init__(self, arm, run_dir, seed=1, budget=None):
        self.arm, self.seed = arm, seed
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = run_dir / "llm_log.jsonl"
        self.budget = budget or guards.Budget()
        self._log_lock = threading.Lock()
        probe = config.PROBE_RESULTS / "llm.json"
        self.json_mode = json.loads(probe.read_text()).get("json_mode", False) if probe.exists() else False

    def _call(self, messages):
        """One API call with exponential backoff + jitter on 429/5xx; every retry is logged."""
        for attempt in range(1, config.LLM_MAX_ATTEMPTS + 1):
            base_url, token, model = endpoint()
            client = OpenAI(base_url=base_url, api_key=token, max_retries=0, timeout=120)
            kwargs = {"model": model, "messages": messages, "temperature": config.TEMPERATURE,
                      "seed": self.seed, "reasoning_effort": config.LLM_REASONING_EFFORT}
            if self.json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            try:
                return model, client.chat.completions.create(**kwargs)
            except (openai.RateLimitError, openai.InternalServerError, openai.APIConnectionError,
                    openai.APITimeoutError) as e:
                if attempt == config.LLM_MAX_ATTEMPTS:
                    raise
                wait = min(60, 2 ** attempt) + random.random()
                self._log({"event": "retry", "attempt": attempt, "wait_s": round(wait, 2), "error": str(e)[:200]})
                time.sleep(wait)

    def complete_json(self, *, agent, gene_code, prompt, schema, list_key=None):
        """Return (parsed dict, error string or None). Never raises on a bad model reply (R10).
        list_key: if the schema is {list_key: [...]} and the model returns the bare list, wrap it."""
        guards.assert_no_identity(prompt)                 # R4
        guards.assert_no_labels(prompt)                   # R3
        messages = [{"role": "user", "content": prompt + "\n\nJSON schema:\n" + schema}]
        last_err = None
        for parse_attempt in (1, 2):
            n = self.budget.take(self.arm, gene_code)     # R1
            t0 = time.time()
            try:
                model, resp = self._call(messages)
            except Exception as e:
                self._log({"agent": agent, "gene_code": gene_code, "call_n": n, "error": str(e)[:300]})
                return None, f"api error: {e}"
            text = resp.choices[0].message.content
            u = resp.usage
            details = getattr(u, "completion_tokens_details", None)
            reasoning = getattr(details, "reasoning_tokens", 0) or 0
            out_tokens = (u.completion_tokens or 0) + reasoning
            cost = (u.prompt_tokens * config.LLM_PRICE_IN_PER_M + out_tokens * config.LLM_PRICE_OUT_PER_M) / 1e6
            entry = {"agent": agent, "gene_code": gene_code, "call_n": n, "model": model,
                     "prompt_tokens": u.prompt_tokens, "completion_tokens": u.completion_tokens,
                     "reasoning_tokens": reasoning, "latency_s": round(time.time() - t0, 2),
                     "cost_usd": round(cost, 6), "parse_attempt": parse_attempt}
            try:
                parsed = parse_json(text, unwrap_single=not list_key)
                if list_key and isinstance(parsed, list):
                    parsed = {list_key: parsed}
                if not isinstance(parsed, dict):
                    raise ValueError("reply is not a JSON object")
                self._log(dict(entry, ok=True))
                return parsed, None
            except (json.JSONDecodeError, ValueError) as e:
                last_err = f"unparseable reply: {e}"
                self._log(dict(entry, ok=False, error=last_err, reply_head=(text or "")[:200]))
                messages = messages + [{"role": "assistant", "content": text or ""},
                                       {"role": "user", "content": JSON_NUDGE}]
        return None, last_err

    def _log(self, entry):                                # R8
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "arm": self.arm, "seed": self.seed, **entry}
        with self._log_lock, self.log_path.open("a") as f:
            f.write(json.dumps(entry) + "\n")
