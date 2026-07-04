from __future__ import annotations

from typing import IO, Any, Protocol

import msgspec

type SizeMB = float
type BlobUrl = str
type Blob = IO[bytes]


class BlobInfo(msgspec.Struct):
    url: BlobUrl
    size: SizeMB


class ObjectStore(Protocol):
    config: dict[str, Any]
    folder_name: str

    async def upload(self, blob: Blob, name: str) -> BlobInfo: ...

    async def read(self, blob: BlobInfo) -> Blob: ...

    async def delete(self, blob_url: BlobUrl) -> None: ...
