"""Durable context and knowledge fabric above trusted memory.

Knowledge is data, not authority. Retrieval preserves provenance, freshness,
classification and source authority and never creates Platform permissions.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from .store import StateStore


class KnowledgeTrust(StrEnum):
    UNTRUSTED = "untrusted"
    VERIFIED = "verified"
    QUARANTINED = "quarantined"


class KnowledgeClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    source_id: str
    workspace_id: str
    name: str
    authority_rank: int = 0
    freshness_seconds: int = 86400
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    document_id: str
    source_id: str
    workspace_id: str
    uri: str
    title: str
    content: str
    collected_at: datetime
    source_version: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    classification: KnowledgeClassification = KnowledgeClassification.INTERNAL
    trust: KnowledgeTrust = KnowledgeTrust.UNTRUSTED
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    workspace_id: str
    ordinal: int
    content: str
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeHit:
    chunk_id: str
    document_id: str
    source_id: str
    uri: str
    title: str
    content: str
    score: float
    authority_rank: int
    collected_at: datetime
    valid_until: datetime | None
    classification: KnowledgeClassification
    trust: KnowledgeTrust
    provenance: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class KnowledgeContext:
    hits: tuple[KnowledgeHit, ...]
    total_characters: int


class KnowledgeFabric:
    """Registers sources/documents and performs deterministic local retrieval."""

    def __init__(self, store: StateStore) -> None:
        self.store = store

    def register_source(self, source: KnowledgeSource, *, now: datetime | None = None) -> None:
        if source.authority_rank < 0:
            raise ValueError("authority_rank must be non-negative")
        if source.freshness_seconds < 1:
            raise ValueError("freshness_seconds must be positive")
        current = self._now(now)
        self.store.put_knowledge_source(
            (
                source.source_id,
                source.workspace_id,
                source.name,
                source.authority_rank,
                source.freshness_seconds,
                json.dumps(dict(source.metadata or {}), sort_keys=True),
                current.isoformat(),
                current.isoformat(),
            )
        )

    def ingest(
        self,
        document: KnowledgeDocument,
        *,
        chunk_size: int = 1200,
        now: datetime | None = None,
    ) -> tuple[KnowledgeChunk, ...]:
        source = self.store.get_knowledge_source(document.source_id)
        if source is None:
            raise KeyError(document.source_id)
        if source["workspace_id"] != document.workspace_id:
            raise ValueError("knowledge source workspace mismatch")
        if chunk_size < 200 or chunk_size > 8000:
            raise ValueError("chunk_size must be between 200 and 8000")
        if document.trust is KnowledgeTrust.QUARANTINED:
            raise ValueError("quarantined knowledge cannot be ingested into active fabric")
        if document.classification is KnowledgeClassification.RESTRICTED:
            raise ValueError("restricted knowledge requires an explicit enterprise connector")
        current = self._now(now)
        digest = self._digest(document.content)
        self.store.put_knowledge_document(
            (
                document.document_id,
                document.source_id,
                document.workspace_id,
                document.uri,
                document.title,
                document.content,
                digest,
                document.source_version,
                document.collected_at.astimezone(UTC).isoformat(),
                document.valid_from.astimezone(UTC).isoformat() if document.valid_from else None,
                document.valid_until.astimezone(UTC).isoformat() if document.valid_until else None,
                document.classification.value,
                document.trust.value,
                json.dumps(dict(document.metadata or {}), sort_keys=True),
                current.isoformat(),
            )
        )
        chunks = tuple(
            KnowledgeChunk(
                chunk_id=self._digest(f"{document.document_id}:{index}:{chunk}"),
                document_id=document.document_id,
                workspace_id=document.workspace_id,
                ordinal=index,
                content=chunk,
            )
            for index, chunk in enumerate(self._chunk(document.content, chunk_size))
        )
        for chunk in chunks:
            self.store.put_knowledge_chunk(
                (
                    chunk.chunk_id,
                    chunk.document_id,
                    chunk.workspace_id,
                    chunk.ordinal,
                    chunk.content,
                    self._digest(chunk.content),
                    json.dumps(dict(chunk.metadata or {}), sort_keys=True),
                )
            )
        return chunks

    def retrieve(
        self,
        workspace_id: str,
        query: str,
        *,
        maximum_classification: KnowledgeClassification = KnowledgeClassification.INTERNAL,
        include_untrusted: bool = True,
        now: datetime | None = None,
        limit: int = 10,
    ) -> KnowledgeContext:
        terms = tuple(dict.fromkeys(re.findall(r"[a-z0-9_]{2,}", query.lower())))
        if not terms:
            return KnowledgeContext((), 0)
        current = self._now(now)
        rows = self.store.search_knowledge_chunks(workspace_id, terms[:3], min(limit * 5, 200))
        hits: list[KnowledgeHit] = []
        for row in rows:
            classification = KnowledgeClassification(str(row["classification"]))
            if self._classification_rank(classification) > self._classification_rank(
                maximum_classification
            ):
                continue
            trust = KnowledgeTrust(str(row["trust"]))
            if trust is KnowledgeTrust.QUARANTINED or (
                trust is KnowledgeTrust.UNTRUSTED and not include_untrusted
            ):
                continue
            content = str(row["content"])
            tokens = set(re.findall(r"[a-z0-9_]{2,}", content.lower()))
            lexical = sum(1 for term in terms if term in tokens) / len(terms)
            collected = datetime.fromisoformat(str(row["collected_at"]))
            age = max(0.0, (current - collected).total_seconds())
            freshness = 1.0 / (1.0 + age / max(1, int(row["freshness_seconds"])))
            authority = min(1.0, int(row["authority_rank"]) / 100.0)
            score = lexical * 0.65 + freshness * 0.20 + authority * 0.15
            hits.append(
                KnowledgeHit(
                    chunk_id=str(row["chunk_id"]),
                    document_id=str(row["document_id"]),
                    source_id=str(row["source_id"]),
                    uri=str(row["uri"]),
                    title=str(row["title"]),
                    content=content,
                    score=score,
                    authority_rank=int(row["authority_rank"]),
                    collected_at=collected,
                    valid_until=(
                        datetime.fromisoformat(str(row["valid_until"]))
                        if row["valid_until"]
                        else None
                    ),
                    classification=classification,
                    trust=trust,
                    provenance={
                        "source_name": str(row["source_name"]),
                        "source_id": str(row["source_id"]),
                        "document_id": str(row["document_id"]),
                        "uri": str(row["uri"]),
                        "collected_at": str(row["collected_at"]),
                        "content_digest": self._digest(content),
                    },
                )
            )
        hits.sort(key=lambda hit: (-hit.score, -hit.authority_rank, hit.chunk_id))
        return KnowledgeContext(tuple(hits[:limit]), sum(len(hit.content) for hit in hits[:limit]))

    def assemble_context(
        self,
        workspace_id: str,
        query: str,
        *,
        max_characters: int = 6000,
        maximum_classification: KnowledgeClassification = KnowledgeClassification.INTERNAL,
        include_untrusted: bool = True,
        now: datetime | None = None,
        limit: int = 10,
    ) -> KnowledgeContext:
        if max_characters < 1:
            raise ValueError("max_characters must be positive")
        context = self.retrieve(
            workspace_id,
            query,
            maximum_classification=maximum_classification,
            include_untrusted=include_untrusted,
            now=now,
            limit=limit,
        )
        selected: list[KnowledgeHit] = []
        total = 0
        for hit in context.hits:
            if total + len(hit.content) > max_characters:
                continue
            selected.append(hit)
            total += len(hit.content)
        return KnowledgeContext(tuple(selected), total)

    @staticmethod
    def _chunk(content: str, size: int) -> Sequence[str]:
        words = content.split()
        chunks: list[str] = []
        current: list[str] = []
        length = 0
        for word in words:
            if current and length + len(word) + 1 > size:
                chunks.append(" ".join(current))
                current, length = [], 0
            current.append(word)
            length += len(word) + (1 if current else 0)
        if current:
            chunks.append(" ".join(current))
        return chunks or ("",)

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def _classification_rank(value: KnowledgeClassification) -> int:
        return {
            KnowledgeClassification.PUBLIC: 0,
            KnowledgeClassification.INTERNAL: 1,
            KnowledgeClassification.CONFIDENTIAL: 2,
            KnowledgeClassification.RESTRICTED: 3,
        }[value]

    @staticmethod
    def _now(value: datetime | None) -> datetime:
        current = value or datetime.now(UTC)
        if current.tzinfo is None:
            raise ValueError("knowledge time must be timezone-aware")
        return current.astimezone(UTC)
