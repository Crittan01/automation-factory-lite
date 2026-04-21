from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re


TOKEN_RE = re.compile(r'[a-zA-Z0-9_]{3,}')
MAX_SNIPPET_LEN = 280


@dataclass
class _Doc:
    path: str
    text: str
    tokens: set[str]


@dataclass
class KnowledgeHit:
    path: str
    score: int
    snippet: str


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text)}


def _snippet(text: str, query_tokens: set[str]) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ''
    best_line = lines[0]
    best_score = -1
    for line in lines:
        score = len(query_tokens & _tokenize(line))
        if score > best_score:
            best_score = score
            best_line = line
    return best_line[:MAX_SNIPPET_LEN]


def _knowledge_roots(root_dir: str) -> list[Path]:
    root = Path(root_dir)
    return [
        root / 'README.md',
        root / 'AGENTS.md',
        root / 'docs',
        root / 'services' / 'orchestrator' / 'README.md',
    ]


def _collect_documents(root_dir: str) -> list[Path]:
    docs: list[Path] = []
    for entry in _knowledge_roots(root_dir):
        if not entry.exists():
            continue
        if entry.is_file():
            docs.append(entry)
            continue
        docs.extend(sorted(path for path in entry.rglob('*.md') if path.is_file()))
    # Deduplicate while preserving order.
    unique: list[Path] = []
    seen: set[str] = set()
    for path in docs:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


@lru_cache(maxsize=8)
def _index(root_dir: str) -> list[_Doc]:
    indexed: list[_Doc] = []
    for path in _collect_documents(root_dir):
        try:
            raw = path.read_text(encoding='utf-8')
        except Exception:
            continue
        text = raw.strip()
        if text == '':
            continue
        indexed.append(
            _Doc(
                path=str(path),
                text=text,
                tokens=_tokenize(text),
            )
        )
    return indexed


def knowledge_stats(root_dir: str) -> dict:
    docs = _index(root_dir)
    return {
        'documents_indexed': len(docs),
        'retrieval_mode': 'keyword_overlap',
        'vector_store': 'none',
    }


def query_knowledge(root_dir: str, query: str, limit: int = 3) -> list[KnowledgeHit]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: list[KnowledgeHit] = []
    for doc in _index(root_dir):
        score = len(query_tokens & doc.tokens)
        if score <= 0:
            continue
        scored.append(
            KnowledgeHit(
                path=doc.path,
                score=score,
                snippet=_snippet(doc.text, query_tokens),
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[: max(1, min(limit, 10))]
