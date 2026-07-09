import datetime
import enum
from typing import ClassVar
import uuid

from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    sql,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Role(enum.StrEnum):
    ADMIN = "App.Admin"
    USER = "App.User"


class Base(DeclarativeBase, AsyncAttrs):
    __abstract__: ClassVar[bool] = True
    metadata: ClassVar[MetaData] = MetaData(naming_convention=naming_convention)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql.func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql.func.now()
    )


class User(Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[list[Role]] = mapped_column(ARRAY(Enum(Role)), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(postgresql.UUID(as_uuid=True))

    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    __table_args__ = (UniqueConstraint("object_id"), Index("ix_index_role", "role"))


class Document(Base):
    __tablename__ = "documents"

    uploader_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    images: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="documents")

    __table_args__ = (UniqueConstraint("uri"), Index("ix_index_uploader_id", "uploader_id"))
