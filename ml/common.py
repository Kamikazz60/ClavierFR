"""Briques communes du ContextLM français : normalisation, découpage en mots, hachage (copie de vocab_hash.hpp)."""
import re

M64 = (1 << 64) - 1

# --- wyhash : copie fidèle de swipe-library/include/swipe_decoder/vocab_hash.hpp -------------
_S0 = 0xa0761d6478bd642f
_S1 = 0xe7037ed1a0b428db
_S2 = 0x8ebc6af09c88c6e3
_S3 = 0x589965cc75374cc3
_A0 = 0x9E3779B97F4A7C15
_A1 = 0x517CC1B727220A95


def _mix(a, b):
    r = (a & M64) * (b & M64)
    return ((r & M64) ^ (r >> 64)) & M64


def _r8(p, i): return int.from_bytes(p[i:i + 8], "little")
def _r4(p, i): return int.from_bytes(p[i:i + 4], "little")
def _r3(p, k): return (p[0] << 16) | (p[k >> 1] << 8) | p[k - 1]


def wyhash(p: bytes, seed: int = 0) -> int:
    n = len(p)
    seed = (seed ^ _mix(seed ^ _S0, _S1)) & M64
    if n <= 16:
        if n >= 4:
            a = ((_r4(p, 0) << 32) | _r4(p, (n >> 3) << 2)) & M64
            b = ((_r4(p, n - 4) << 32) | _r4(p, n - 4 - ((n >> 3) << 2))) & M64
        elif n > 0:
            a = _r3(p, n); b = 0
        else:
            a = b = 0
    elif n <= 48:
        i = 0
        while i + 16 <= n:
            seed = _mix(_r8(p, i) ^ _S1, _r8(p, i + 8) ^ seed)
            i += 16
        a = _r8(p, n - 16); b = _r8(p, n - 8)
    else:
        i = 0
        see1 = seed; see2 = seed
        while i + 48 <= n:
            seed = _mix(_r8(p, i) ^ _S1, _r8(p, i + 8) ^ seed)
            see1 = _mix(_r8(p, i + 16) ^ _S2, _r8(p, i + 24) ^ see1)
            see2 = _mix(_r8(p, i + 32) ^ _S3, _r8(p, i + 40) ^ see2)
            i += 48
        while i + 16 <= n:
            seed = _mix(_r8(p, i) ^ _S1, _r8(p, i + 8) ^ seed)
            i += 16
        seed ^= see1 ^ see2
        a = _r8(p, n - 16); b = _r8(p, n - 8)
    return _mix(_S1 ^ n, _mix(a ^ _S1, b ^ seed))


def hash_indices(word: str, num_buckets: int):
    """Deux buckets pour un mot hors vocabulaire (num_buckets = puissance de 2)."""
    shift = 64 - (num_buckets.bit_length() - 1)
    key = wyhash(word.encode("utf-8"))
    return (((_A0 * key) & M64) >> shift, ((_A1 * key) & M64) >> shift)


# --- texte -----------------------------------------------------------------------------------
# L'appli découpe le contexte avec Regex("[^\\w']+") puis met en minuscules : un mot garde ses
# apostrophes internes (« l'heure », « d'une » sont un seul mot).
_TOKEN = re.compile(r"[\w']+")


def normalize(text: str) -> str:
    return text.replace("’", "'").replace("‘", "'").replace("ʼ", "'")


def tokenize(line: str):
    out = []
    for t in _TOKEN.findall(normalize(line).lower()):
        t = t.strip("'")
        if t and any(c.isalpha() for c in t) or t.isdigit():
            out.append(t)
    return out
