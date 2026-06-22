from __future__ import annotations

from typing import Protocol
import uuid

from sqlalchemy.ext.asyncio.session import AsyncSession

from dns_to_fd.models import Base


class AsyncSQLRepositoryProtocol[ModelType: Base](Protocol):
    model: type[ModelType]

    async def create(
        self,
        data: ModelType,
        session: AsyncSession,
    ) -> ModelType: ...

    async def delete(
        self,
        item_id: uuid.UUID,
        session: AsyncSession,
    ) -> None: ...

    async def read(
        self,
        item_id: uuid.UUID,
        session: AsyncSession,
        expunge: bool = False,
    ) -> ModelType: ...

    async def update(
        self,
        data: ModelType,
        session: AsyncSession,
    ) -> ModelType: ...


class AsyncSQLBaseRepository[ModelType: Base](AsyncSQLRepositoryProtocol[ModelType]):
    def __init__(self, model: type[ModelType]):

        self.model = model

    async def create(
        self,
        data: ModelType,
        session: AsyncSession,
    ) -> ModelType:

        session.add(data)
        await session.flush()
        await session.refresh(data)

        return data
