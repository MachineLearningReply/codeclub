from __future__ import annotations

from dns_to_fd.models import Document

from .base_repo import AsyncSQLBaseRepository


class DocumentRepository(AsyncSQLBaseRepository[Document]): ...
