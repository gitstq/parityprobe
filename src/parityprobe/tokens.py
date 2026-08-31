"""Transparent, dependency-free machine-reading cost estimator.

A real tokenizer (tiktoken / sentencepiece) needs bundled vocabularies.  To
stay zero-dependency and fully offline we use a documented approximation:

* each run of latin/digit characters counts as ~1 word token (long words are
  split at camelCase / snake_case / hyphen boundaries, matching how most BPE
  tokenizers behave);
* every CJK ideograph counts as one token;
* every run of punctuation counts as one token.

The formula, its limits and how it compares to cl100k_base are documented in
the README.  Numbers are always labelled ``estimated``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["CostEstimate", "estimate_cost"]

_WORD = re.compile(r"[A-Za-z0-9]+")
_CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
_PUNCT_RUN = re.compile(r"[^\w\s]", re.UNICODE)
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[0-9]+")


def _word_tokens(word: str) -> int:
    parts = _CAMEL.findall(word)
    return max(1, len(parts))


@dataclass
class CostEstimate:
    bytes_len: int
    chars: int
    words: int
    cjk_chars: int
    estimated_tokens: int
    punctuation_tokens: int

    def as_dict(self) -> dict:
        return {
            "bytes": self.bytes_len,
            "chars": self.chars,
            "words": self.words,
            "cjk_chars": self.cjk_chars,
            "punctuation_tokens": self.punctuation_tokens,
            "estimated_tokens": self.estimated_tokens,
        }


def estimate_cost(text: str, raw_bytes_len: int | None = None) -> CostEstimate:
    words = _WORD.findall(text)
    word_tokens = sum(_word_tokens(w) for w in words)
    cjk = len(_CJK.findall(text))
    punct = len(_PUNCT_RUN.findall(text))
    estimated = word_tokens + cjk + punct
    return CostEstimate(
        bytes_len=len(text.encode("utf-8")) if raw_bytes_len is None else raw_bytes_len,
        chars=len(text),
        words=len(words),
        cjk_chars=cjk,
        estimated_tokens=estimated,
        punctuation_tokens=punct,
    )
