from __future__ import annotations

import hashlib
import math
from typing import Iterable, Sequence

from codex_bridge.config import EMBEDDING_DIMENSIONS


def embed_text(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for feature, weight in _iter_features(text):
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        for offset in (0, 8):
            index = int.from_bytes(digest[offset : offset + 2], "big") % EMBEDDING_DIMENSIONS
            sign = -1.0 if digest[offset + 2] & 1 else 1.0
            magnitude = (digest[offset + 3] + 1) / 256.0
            vector[index] += sign * weight * magnitude

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [round(value / norm, 12) for value in vector]


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    return [embed_text(text) for text in texts]


def _iter_features(text: str) -> Iterable[tuple[str, float]]:
    normalized = " ".join(text.lower().split())
    if not normalized:
        yield "<empty>", 1.0
        return

    for token in normalized.split(" "):
        if token:
            yield f"tok:{token}", 1.0

    padded = f" {normalized} "
    if len(padded) < 3:
        yield f"char:{padded.strip()}", 0.5
        return

    for index in range(len(padded) - 2):
        yield f"tri:{padded[index:index + 3]}", 0.5
