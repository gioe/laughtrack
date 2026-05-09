"""Tests for shared Next.js RSC payload extraction helpers."""

import json

from laughtrack.core.clients.rsc.extractor import (
    extract_push_payloads,
    find_json_array,
    resolve_references,
)


def _push(payload: str) -> str:
    escaped = json.dumps(payload)[1:-1]
    return f'<script>self.__next_f.push([1,"{escaped}"])</script>'


def test_extract_push_payloads_decodes_multiple_script_payloads():
    html = _push('1a:["first"]') + _push('1b:{"second":true}')

    assert extract_push_payloads(html) == ['1a:["first"]', '1b:{"second":true}']


def test_find_json_array_extracts_embedded_balanced_array():
    text = (
        '{"before":true,"initialShows":['
        '{"id":1,"label":"uses [brackets] in text","nested":{"value":[1,2]}},'
        '{"id":2}'
        '],"after":true}'
    )

    assert find_json_array(text, "initialShows") == [
        {"id": 1, "label": "uses [brackets] in text", "nested": {"value": [1, 2]}},
        {"id": 2},
    ]


def test_resolve_references_replaces_rsc_reference_strings_with_null():
    payload = (
        '{"id":"1","component":"$L5","symbol":"$Sreact.suspense",'
        '"broad":"$any-reference-form","literal":"not a reference"}'
    )

    assert json.loads(resolve_references(payload)) == {
        "id": "1",
        "component": None,
        "symbol": None,
        "broad": None,
        "literal": "not a reference",
    }
