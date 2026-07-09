from __future__ import annotations

import json

import msgspec
from msgspec import Struct
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from dns_to_fd.api.deps import DBSession, get_entra_id_claims
from dns_to_fd.models import Role, User
from dns_to_fd.repositories import UserRepository


class UserCreateSchema(Struct):
    name: str
    role: list[Role]


user_repo = UserRepository(model=User)


async def add_user(request: Request) -> JSONResponse:

    body = await request.body()
    json_body = json.loads(body)
    user_info: UserCreateSchema = msgspec.convert(json_body, UserCreateSchema)
    claims = await get_entra_id_claims(request)
    if Role.ADMIN.value not in claims.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        )

    async with DBSession() as session:
        user = await user_repo.create(
            User(
                name=user_info.name,
                role=user_info.role,
                object_id=claims.oid,
            ),
            session=session,
        )

    return JSONResponse(
        content={
            "id": str(user.id),
            "role": user.role,
            "name": user.name,
        },
        status_code=status.HTTP_201_CREATED,
    )


async def delete_user(request: Request) -> Response:

    user_id: str = request.path_params["user_id"]
    claims = await get_entra_id_claims(request)
    if Role.ADMIN.value not in claims.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        )

    async with DBSession() as session:
        await user_repo.delete(item_id=user_id, session=session)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def get_user(request: Request) -> JSONResponse:

    user_id: str = request.path_params["user_id"]
    claims = await get_entra_id_claims(request)
    if Role.ADMIN.value not in claims.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
        )

    async with DBSession() as session:
        user = await user_repo.read(item_id=user_id, session=session)

    return JSONResponse(
        content={
            "id": str(user.id),
            "role": user.role,
            "name": user.name,
        }
    )


routes = [
    Route("/users", add_user, methods=["POST"]),
    Route("/users/{user_id}", delete_user, methods=["DELETE"]),
    Route("/users/{user_id}", get_user, methods=["GET"]),
]
