from abc import abstractmethod
from typing import Protocol, runtime_checkable, Sequence
from pydantic import BaseModel
import uuid

from fastapi import UploadFile

class Chunk(BaseModel):
    id: uuid.UUID
    content: str
    embedding: Sequence[float]


@runtime_checkable
class VectorStore(Protocol):
    """Vector store interface"""

    @abstractmethod
    def __init__(self, current_user_id: str):
        self.current_user_id = current_user_id
        """Initialize the vector store"""
        pass

    @abstractmethod
    async def add(
        self,
        files: list[UploadFile],
        document_converter_backend: str | None = None,
        upload_file: bool = False,
    ) -> list[int]:
        """Add a document to the vector store"""
        pass

    @abstractmethod
    async def delete(self, document_ids: list[int]) -> bool:
        """Delete a document from the vector store"""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        num_chunks: int = 5,
        user_id: str | None = None,
        document_ids: list[int] | None = None,
    ) -> list[Chunk]:
        """Search the vector store for the most similar documents"""
        pass