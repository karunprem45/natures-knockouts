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
