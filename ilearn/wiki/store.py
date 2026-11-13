"""File-backed wiki page + edge store with BM25 index rebuild."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from ilearn.wiki.bm25 import BM25Index, tokenize
from ilearn.wiki.models import WikiEdge, WikiPage


class WikiStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._pages_path = self.root / "pages.jsonl"
        self._edges_path = self.root / "edges.jsonl"
        self._lock = threading.RLock()
        self._pages: dict[str, WikiPage] = {}
        self._edges: list[WikiEdge] = []
        self._index: BM25Index | None = None
        self._order: list[str] = []
        self._load()

    def _load(self) -> None:
        if self._pages_path.exists():
            for line in self._pages_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                page = WikiPage.model_validate_json(line)
                self._pages[page.page_id] = page
        if self._edges_path.exists():
            for line in self._edges_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._edges.append(WikiEdge.model_validate_json(line))
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        self._order = sorted(self._pages.keys())
        corpus = [tokenize(self._pages[pid].searchable_text()) for pid in self._order]
        self._index = BM25Index(corpus)

    def _rewrite_pages(self) -> None:
        with self._pages_path.open("w", encoding="utf-8") as fh:
            for pid in sorted(self._pages):
                fh.write(self._pages[pid].model_dump_json() + "\n")

    def _rewrite_edges(self) -> None:
        with self._edges_path.open("w", encoding="utf-8") as fh:
            for edge in self._edges:
                fh.write(edge.model_dump_json() + "\n")

    def upsert(self, page: WikiPage) -> WikiPage:
        with self._lock:
            self._pages[page.page_id] = page
            self._rewrite_pages()
            self._rebuild_index()
            return page

    def upsert_many(self, pages: list[WikiPage]) -> int:
        with self._lock:
            for page in pages:
                self._pages[page.page_id] = page
            self._rewrite_pages()
            self._rebuild_index()
            return len(pages)

    def add_edge(self, edge: WikiEdge) -> WikiEdge:
        with self._lock:
            key = (edge.left_page_id, edge.right_page_id, edge.skill_id, edge.relation)
            for existing in self._edges:
                ek = (
                    existing.left_page_id,
                    existing.right_page_id,
                    existing.skill_id,
                    existing.relation,
                )
                if ek == key or (
                    existing.right_page_id,
                    existing.left_page_id,
                    existing.skill_id,
                    existing.relation,
                ) == key:
                    return existing
            self._edges.append(edge)
            self._rewrite_edges()
            return edge

    def get(self, page_id: str) -> WikiPage | None:
        return self._pages.get(page_id)

    def list_pages(self) -> list[WikiPage]:
        return [self._pages[pid] for pid in sorted(self._pages)]

    def neighbors(self, page_id: str) -> list[str]:
        out: list[str] = []
        for e in self._edges:
            if e.left_page_id == page_id:
                out.append(e.right_page_id)
            elif e.right_page_id == page_id:
                out.append(e.left_page_id)
        return out

    def search_bm25(self, query: str, *, top_k: int = 5) -> list[tuple[WikiPage, float]]:
        with self._lock:
            if not self._index or not self._order:
                return []
            q = tokenize(query)
            ranked = self._index.rank(q, top_k=top_k)
            return [(self._pages[self._order[i]], score) for i, score in ranked]

    def rebuild_skill_graph(self) -> int:
        """Connect pages that share a skill_id."""
        with self._lock:
            existing = {
                (
                    min(e.left_page_id, e.right_page_id),
                    max(e.left_page_id, e.right_page_id),
                    e.skill_id,
                    e.relation,
                )
                for e in self._edges
            }
            by_skill: dict[str, list[str]] = {}
            for page in self._pages.values():
                for sid in page.skill_ids:
                    by_skill.setdefault(sid, []).append(page.page_id)
            added = 0
            for skill_id, page_ids in by_skill.items():
                unique = sorted(set(page_ids))
                for i, left in enumerate(unique):
                    for right in unique[i + 1 :]:
                        key = (left, right, skill_id, "shares_skill")
                        if key in existing:
                            continue
                        self._edges.append(
                            WikiEdge(
                                left_page_id=left,
                                right_page_id=right,
                                relation="shares_skill",
                                skill_id=skill_id,
                            )
                        )
                        existing.add(key)
                        added += 1
            if added:
                self._rewrite_edges()
            return added
