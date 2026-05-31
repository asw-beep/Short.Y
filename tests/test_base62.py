import pytest

from app.services import base62


def test_encode_zero_pads_to_min_length():
    assert base62.encode(0) == "0000000"


def test_encode_known_values():
    assert base62.encode(1) == "0000001"
    assert base62.encode(61) == "000000z"
    assert base62.encode(62) == "0000010"


def test_encode_decode_roundtrip():
    for n in [0, 1, 61, 62, 1000, 123_456_789, 10**12]:
        assert base62.decode(base62.encode(n).lstrip("0") or "0") == n


def test_decode_invalid_char():
    with pytest.raises(ValueError):
        base62.decode("abc!def")


def test_encode_rejects_negative():
    with pytest.raises(ValueError):
        base62.encode(-1)
