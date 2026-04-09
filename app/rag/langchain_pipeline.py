from __future__ import annotations

from pathlib import Path
from typing import Iterable

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS, SKLearnVectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import get_settings


class LocalHashEmbeddings(Embeddings):
    def __init__(self, dimension: int = 64):
        self.dimension = dimension

    def _encode(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for index, char in enumerate(text.lower()):
            slot = (ord(char) + index) % self.dimension
            vector[slot] += 1.0
        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._encode(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._encode(text)


def get_embeddings() -> Embeddings:
    settings = get_settings()
    if settings.embedding_provider == "local":
        return LocalHashEmbeddings()
    return HuggingFaceEmbeddings(model_name=settings.embedding_model)


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=120)


def load_source_documents(file_path: str) -> list[Document]:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path)).load()
    if suffix in {".md", ".markdown"}:
        return TextLoader(str(path), encoding="utf-8").load()
    return TextLoader(str(path), encoding="utf-8").load()


def split_documents(documents: Iterable[Document]) -> list[Document]:
    splitter = get_text_splitter()
    return splitter.split_documents(list(documents))


def load_vector_store():
    settings = get_settings()
    path = settings.vector_store_path
    if not path.exists():
        return None
    if settings.vector_store_backend == "sklearn":
        persist_path = path / "sklearn_store.json"
        if not persist_path.exists():
            return None
        return SKLearnVectorStore(get_embeddings(), persist_path=str(persist_path), serializer="json")
    return FAISS.load_local(str(path), get_embeddings(), allow_dangerous_deserialization=True)


def persist_vector_store(vector_store) -> None:
    settings = get_settings()
    path = settings.vector_store_path
    path.mkdir(parents=True, exist_ok=True)
    if settings.vector_store_backend == "sklearn":
        vector_store.persist()
        return
    vector_store.save_local(str(path))


def build_or_update_vector_store(documents: list[Document]):
    settings = get_settings()
    existing = load_vector_store()
    if existing is None:
        if settings.vector_store_backend == "sklearn":
            persist_path = settings.vector_store_path / "sklearn_store.json"
            vector_store = SKLearnVectorStore.from_documents(
                documents,
                get_embeddings(),
                persist_path=str(persist_path),
                serializer="json",
            )
        else:
            vector_store = FAISS.from_documents(documents, get_embeddings())
    else:
        existing.add_documents(documents)
        vector_store = existing
    persist_vector_store(vector_store)
    return vector_store
