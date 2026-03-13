"""
storage/vector_store.py — Shared Memory via ChromaDB.
Stores embeddings for RAG, evidence linking, and cross-agent memory.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8001"))


class VectorStore:
    """
    Thin wrapper around ChromaDB for shared agent memory.
    
    Collections:
    - "artifacts"  — stored task outputs (research, code, media)
    - "evidence"   — research claim citations
    - "messages"   — important inter-agent messages for RAG
    """

    def __init__(self):
        self.client = chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            settings=Settings(anonymized_telemetry=False),
        )
        self._ensure_collections()

    def _ensure_collections(self) -> None:
        for name in ["artifacts", "evidence", "messages"]:
            try:
                self.client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception as e:
                logger.error(f"Failed to create collection {name}: {e}")

    # ── Artifact storage ───────────────────────────────────────────────────

    def store_artifact(
        self,
        artifact_id: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> str:
        """Store an artifact embedding. Returns the vector ID."""
        col = self.client.get_collection("artifacts")
        col.upsert(
            ids=[artifact_id],
            documents=[content],
            metadatas=[{k: str(v) for k, v in metadata.items()}],
        )
        return artifact_id

    def search_artifacts(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[dict]:
        col = self.client.get_collection("artifacts")
        results = col.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        return self._format_results(results)

    # ── Evidence storage ───────────────────────────────────────────────────

    def store_evidence(
        self,
        claim: str,
        source_url: str,
        excerpt: str,
        task_id: str,
        agent_id: str,
        confidence: float,
    ) -> str:
        col = self.client.get_collection("evidence")
        evidence_id = hashlib.sha256(f"{claim}{source_url}".encode()).hexdigest()[:16]
        col.upsert(
            ids=[evidence_id],
            documents=[f"{claim}\n\n{excerpt}"],
            metadatas=[{
                "source_url": source_url,
                "task_id": task_id,
                "agent_id": agent_id,
                "confidence": str(confidence),
            }],
        )
        return evidence_id

    def search_evidence(self, query: str, n_results: int = 5) -> List[dict]:
        col = self.client.get_collection("evidence")
        results = col.query(query_texts=[query], n_results=n_results)
        return self._format_results(results)

    # ── Message storage ────────────────────────────────────────────────────

    def store_message(
        self,
        message_id: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> str:
        col = self.client.get_collection("messages")
        col.upsert(
            ids=[message_id],
            documents=[content],
            metadatas=[{k: str(v) for k, v in metadata.items()}],
        )
        return message_id

    def search_messages(self, query: str, n_results: int = 5) -> List[dict]:
        col = self.client.get_collection("messages")
        results = col.query(query_texts=[query], n_results=n_results)
        return self._format_results(results)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _format_results(self, results: dict) -> List[dict]:
        formatted = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            formatted.append({
                "id": doc_id,
                "content": docs[i] if i < len(docs) else "",
                "metadata": metas[i] if i < len(metas) else {},
                "similarity": 1 - (distances[i] if i < len(distances) else 1),
            })
        return formatted
