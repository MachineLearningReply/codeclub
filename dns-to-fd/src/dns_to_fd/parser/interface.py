from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import io
from typing import Protocol, TypedDict

type ContentT = bytes | io.BytesIO
type FileT = str


class NoContentFoundError(Exception): ...


@dataclass
class Page:
    content: str
    markdown: str
    tables: Sequence
    images: Sequence


@dataclass
class Document:
    pages: Sequence[Page]


class ParserConfig(TypedDict):
    extract_tables: bool
    extract_images: bool


class Parser(Protocol):
    config: ParserConfig

    async def parse_bytes(self, content: ContentT) -> Document: ...

    async def parse_file(self, file_path: FileT) -> Document: ...
