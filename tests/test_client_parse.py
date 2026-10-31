import json
import pytest
from llm.client import parse_json


def test_plain_object():
    assert parse_json('{"stance": "neutral"}') == {"stance": "neutral"}


def test_code_fence_and_prose():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Here you go: {"a": 1} thanks') == {"a": 1}


def test_single_item_list_is_unwrapped():
    assert parse_json('[\n {"stance": "supports", "strength": 0.9}\n]') == {"stance": "supports", "strength": 0.9}


def test_multi_item_list_is_not_silently_picked():
    assert isinstance(parse_json('[{"a": 1}, {"a": 2}]'), list)


def test_garbage_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_json("no json here")


class _Usage:
    prompt_tokens, completion_tokens, completion_tokens_details = 10, 5, None


class _Resp:
    def __init__(self, text):
        self.choices = [type("C", (), {"message": type("M", (), {"content": text})()})()]
        self.usage = _Usage()


def _client(tmp_path, reply):
    from llm.client import LLMClient
    c = LLMClient("t", tmp_path)
    c._call = lambda messages: ("m", _Resp(reply))
    return c


def test_single_challenge_list_is_wrapped_not_unwrapped(tmp_path):
    c = _client(tmp_path, '[{"type": "single_cohort", "channel": "burden"}]')
    parsed, err = c.complete_json(agent="skeptic", gene_code="Gene_01", prompt="p", schema="s", list_key="challenges")
    assert err is None and parsed == {"challenges": [{"type": "single_cohort", "channel": "burden"}]}


def test_wrapped_object_still_unwrapped_without_list_key(tmp_path):
    c = _client(tmp_path, '[{"stance": "neutral"}]')
    parsed, _ = c.complete_json(agent="burden", gene_code="Gene_01", prompt="p", schema="s")
    assert parsed == {"stance": "neutral"}
