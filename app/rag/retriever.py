from __future__ import annotations

from dataclasses import dataclass

from app.rag.langchain_pipeline import load_vector_store


@dataclass
class RetrievedEvidence:
    chunk_id: str
    doc_id: str
    content: str
    source_path: str
    score: float


class ProtocolRetriever:
    version = "langchain-vectorstore-v1"

    def __init__(self) -> None:
        self.store = load_vector_store()

    def retrieve(self, query: str, pathway: str | None = None, k: int = 4) -> list[RetrievedEvidence]:
        if self.store is None:
            return []
        available = getattr(getattr(self.store, "_neighbors", None), "n_samples_fit_", k)
        search_k = max(1, min(k, available))
        results = self.store.similarity_search_with_relevance_scores(query, k=search_k)
        evidence: list[RetrievedEvidence] = []
        for index, (doc, score) in enumerate(results):
            metadata = doc.metadata
            if pathway and metadata.get("pathway") != pathway:
                continue
            if not metadata.get("approved_for_use", True):
                continue
            evidence.append(
                RetrievedEvidence(
                    chunk_id=metadata.get("chunk_id", f"chunk_{index}"),
                    doc_id=metadata.get("doc_id", "unknown"),
                    content=doc.page_content,
                    source_path=metadata.get("url_or_path", ""),
                    score=max(0.0, float(score)),
                )
            )
        return evidence
