from typing import Protocol, Any
from msgspec import Struct


# Dynamic vs Static Protocols

class CacheData(Struct):
    key: str
    value: Any


class CacheInterface(Protocol):
    async def aget(self, key: str) -> CacheData:
        ...

    async def aset(self, entry: Any) -> None:
        ...


class RedisCache:
    async def aget(self, key: int) -> CacheData:
        return CacheData(key=key, value='value')

    async def aset(self, entry: Any) -> None:
        return

async def func (cache : CacheInterface) -> None :
    await asyncio.gather ( cache . aget (’key1 ’), cache . aget (’key2 ’))

