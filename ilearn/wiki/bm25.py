"""Stdlib BM25 Okapi — no external deps (P4 acceptance)."""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+")
_CJK = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """Word tokens + CJK character bigrams (Chinese has no whitespace)."""
    raw = text or ""
    tokens: list[str] = []
    for t in _TOKEN_PATTERN.findall(raw):
        t = t.casefold()
        if t:
            tokens.append(t)
    for span in _CJK.findall(raw):
        if len(span) == 1:
            tokens.append(span)
        else:
            for i in range(len(span) - 1):
                tokens.append(span[i : i + 2])
    return tokens


class BM25Index:
    """In-memory BM25 Okapi over tokenized documents."""

    def __init__(self, corpus: list[list[str]], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.N = len(corpus)
        self.doc_len = [len(doc) for doc in corpus]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.df: Counter[str] = Counter()
        self.tf: list[Counter[str]] = []
        for doc in corpus:
            counts = Counter(doc)
            self.tf.append(counts)
            for term in counts:
                self.df[term] += 1

    def idf(self, term: str) -> float:
        n_qi = self.df.get(term, 0)
        return math.log(1.0 + (self.N - n_qi + 0.5) / (n_qi + 0.5))

    def score(self, query: list[str], doc_index: int) -> float:
        if self.N == 0 or self.avgdl <= 0:
            return 0.0
        score = 0.0
        dl = self.doc_len[doc_index]
        tf_map = self.tf[doc_index]
        for term in query:
            if term not in tf_map:
                continue
            freq = tf_map[term]
            denom = freq + self.k1 * (1.0 - self.b + self.b * dl / self.avgdl)
            score += self.idf(term) * (freq * (self.k1 + 1.0)) / denom
        return score

    def rank(self, query: list[str], top_k: int = 5) -> list[tuple[int, float]]:
        scored = [(i, self.score(query, i)) for i in range(self.N)]
        scored.sort(key=lambda x: (-x[1], x[0]))
        return [(i, s) for i, s in scored[:top_k] if s > 0]
