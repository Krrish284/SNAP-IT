"""Collision-safe short code generation for Snap links."""

import secrets

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE62_LEN = len(BASE62_ALPHABET)


def encode_base62(number: int, length: int) -> str:
    """Encode an integer into a fixed-length base62 string (left-padded)."""
    if number < 0:
        raise ValueError("number must be non-negative")
    if length <= 0:
        raise ValueError("length must be positive")

    chars: list[str] = []
    value = number
    for _ in range(length):
        value, remainder = divmod(value, BASE62_LEN)
        chars.append(BASE62_ALPHABET[remainder])

    return "".join(chars)


def generate_short_code(length: int = 7) -> str:
    """Generate a cryptographically random short code of the given length.

    Uses ``secrets.randbelow`` so the code space is uniformly sampled. Combined
    with ``ON CONFLICT DO NOTHING`` at insert time this is collision-safe even
    under concurrent requests.
    """
    if not 1 <= length <= 16:
        raise ValueError("length must be between 1 and 16")

    return encode_base62(secrets.randbelow(BASE62_LEN**length), length)
