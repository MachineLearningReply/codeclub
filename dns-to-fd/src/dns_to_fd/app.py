import contextlib
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import create_async_engine
from starlette.applications import Starlette
from starlette.routing import BaseRoute, Mount

from dns_to_fd.api.v1.controllers import document_routes, user_routes
from dns_to_fd.settings import app_settings
from dns_to_fd.models import Base


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    engine = create_async_engine(url=app_settings.db_connection_string, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    await engine.dispose()
    yield



routes: list[BaseRoute] = [
    Mount("/api/v1/", routes=[*user_routes, *document_routes]),
]

app = Starlette(debug=True, routes=routes, lifespan=lifespan)
