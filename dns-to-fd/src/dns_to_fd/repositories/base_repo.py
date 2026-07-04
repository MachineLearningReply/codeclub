from __future__ import annotations

from typing import Any, Protocol
import uuid

from sqlalchemy import sql
from sqlalchemy.ext.asyncio.session import AsyncSession

from dns_to_fd.models import Base


class DBError(Exception): ...


class DBRecordNotFoundError(DBError): ...


class DBRecordDeletionError(DBError): ...


class DBRecordUpdateError(DBError): ...


class AsyncSQLRepositoryProtocol[ModelType: Base](Protocol):
    model: type[ModelType]

    async def create(
        self,
        data: ModelType,
        session: AsyncSession,
    ) -> ModelType: ...

    async def delete(
        self,
        item_id: uuid.UUID | str,
        session: AsyncSession,
    ) -> None: ...

    async def read(
        self,
        item_id: uuid.UUID | str,
        session: AsyncSession,
        expunge: bool = False,
    ) -> ModelType: ...

    async def update(
        self,
        item_id: uuid.UUID | str,
        data: dict[str, Any],
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

    async def read(
        self,
        item_id: uuid.UUID | str,
        session: AsyncSession,
        expunge: bool = False,
    ) -> ModelType:

        query = sql.select(self.model).where(self.model.id == item_id)
        query_result = await session.execute(query)
        obj = query_result.scalar_one_or_none()
        if obj is None:
            raise DBRecordNotFoundError
        return obj

    async def delete(
        self,
        item_id: uuid.UUID | str,
        session: AsyncSession,
    ) -> None:

        query = sql.select(self.model).where(self.model.id == item_id)
        query_result = await session.execute(query)
        obj = query_result.scalar_one_or_none()
        if obj is None:
            raise DBRecordNotFoundError
        try:
            await session.delete(obj)
        except Exception as e:
            raise DBRecordDeletionError from e

    async def update(
        self,
        item_id: uuid.UUID | str,
        data: dict[str, Any],
        session: AsyncSession,
    ) -> ModelType:

        existing = (
            await session.execute(sql.select(self.model).where(self.model.id == item_id))
        ).scalar_one_or_none()
        if existing is None:
            raise DBRecordNotFoundError

        try:
            for attr, value in data.items():
                setattr(existing, attr, value)

        except Exception as e:
            raise DBRecordUpdateError from e

        session.add(existing)
        await session.refresh(existing)

        return existing
