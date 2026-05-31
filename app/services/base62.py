ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(ALPHABET)
MIN_LENGTH = 7


def encode(n: int) -> str:
    if n < 0:
        raise ValueError("Cannot encode negative integers")
    if n == 0:
        return ALPHABET[0].rjust(MIN_LENGTH, ALPHABET[0])
    out = []
    while n > 0:
        n, rem = divmod(n, BASE)
        out.append(ALPHABET[rem])
    encoded = "".join(reversed(out))
    return encoded.rjust(MIN_LENGTH, ALPHABET[0])


def decode(s: str) -> int:
    n = 0
    for ch in s:
        idx = ALPHABET.find(ch)
        if idx == -1:
            raise ValueError(f"Invalid base62 character: {ch!r}")
        n = n * BASE + idx
    return n
