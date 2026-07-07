from collections.abc import AsyncIterator
import contextlib

from sqlalchemy.ext.asyncio import create_async_engine
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import BaseRoute, Mount, Route

from dns_to_fd.api.v1.controllers import document_routes, user_routes
from dns_to_fd.models import Base
from dns_to_fd.settings import app_settings


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    engine = create_async_engine(url=app_settings.db_connection_string, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    await engine.dispose()
    yield


async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


routes: list[BaseRoute] = [
    Route("/healthz", healthz, methods=["GET"]),
    Mount("/api/v1/", routes=[*user_routes, *document_routes]),
]

app = Starlette(debug=True, routes=routes, lifespan=lifespan)
