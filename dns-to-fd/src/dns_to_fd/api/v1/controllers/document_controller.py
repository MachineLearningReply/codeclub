from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
import io

from azure.identity.aio import ClientSecretCredential
from starlette import status
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from dns_to_fd.api.deps import DBSession, get_entra_id_claims
from dns_to_fd.models import Document, Role, User
from dns_to_fd.object_store.azure_blob_storage import AzureBlobStorage
from dns_to_fd.object_store.interface import ObjectStore

# from dns_to_fd.parser import Document as ParsedDocument
from dns_to_fd.parser import Parser, PDFParser
from dns_to_fd.repositories import DocumentRepository, UserRepository
from dns_to_fd.settings import app_settings

document_repo = DocumentRepository(Document)
user_repo = UserRepository(User)


_stores: list[ObjectStore] = []

def make_add_document(parser: Parser) -> Callable[[Request], Awaitable[JSONResponse]]:
    async def add_document(request: Request) -> JSONResponse:
        async with request.form(max_files=1000, max_fields=1000, max_part_size=1024 * 1024) as form_data:
            user_id = request.path_params["user_id"]
            store = create_obj_store()
            _stores.append(store)
            claims = await get_entra_id_claims(request)
            if Role.USER.value not in claims.roles:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            async with DBSession() as session:
                user = await user_repo.read(item_id=user_id, session=session)
                if str(user.object_id) != claims.oid:
                    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")

            file = form_data["file"]
            if not isinstance(file, UploadFile):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Expected file upload",
                )

            content = await file.read()
            document = await parser.parse_bytes(content)
            full_md_content = "\f".join(page.markdown for page in document.pages)

            document_id = uuid.uuid4()

            blob_info = await store.upload(io.BytesIO(full_md_content.encode("utf-8")), name=document_id.hex)

            async with DBSession() as session:
                document = await document_repo.create(
                    data=Document(
                        id=document_id,
                        uploader_id=user.id,
                        name=file.filename,
                        uri=blob_info.url,
                        size=blob_info.size,
                        content=full_md_content,
                    ),
                    session=session,
                )
            return JSONResponse(
                {
                    "document_id": str(document.id),
                },
                status_code=status.HTTP_201_CREATED,
            )

    return add_document

# def make_get_document_url(store: ObjectStore) -> Callable[[Request], Awaitable[JSONResponse]]:
#     async def add_document(request: Request) -> JSONResponse:
#         async with request.form(max_files=1000, max_fields=1000, max_part_size=1024 * 1024) as form_data:
#             user_id = request.path_params["user_id"]
#             document_id = request.path_params["document_id"]
#
#             claims = await get_entra_id_claims(request)
#             if Role.USER.value not in claims.roles:
#                 raise HTTPException(
#                     status_code=status.HTTP_401_UNAUTHORIZED,
#                 )
#
#             async with DBSession() as session:
#                 user = await user_repo.read(item_id=user_id, session=session)
#                 if user.object_id != claims.oid:
#                     raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")
#
#
#
#             blob_info = upload_task.result()
#             parsed = parsing_task.result()
#
#             async with DBSession() as session:
#                 document = await document_repo.create(
#                     data=Document(
#                         uploader_id=user.id,
#                         name=file.filename or "document",
#                         uri=blob_info.url,
#                         size=blob_info.size,
#                         content="\n".join(page.markdown for page in parsed.pages),
#                     ),
#                     session=session,
#                 )
#             return JSONResponse(
#                 {
#                     "document_id": document.id,
#                     "uri": document.uri,
#                 },
#                 status_code=status.HTTP_201_CREATED,
#             )


async def get_document(request: Request) -> JSONResponse:
    async with request.form(max_files=1000, max_fields=1000, max_part_size=1024 * 1024):
        user_id = request.path_params["user_id"]
        document_id = request.path_params["document_id"]

        claims = await get_entra_id_claims(request)
        if Role.USER.value not in claims.roles:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        async with DBSession() as session:
            user = await user_repo.read(item_id=user_id, session=session)
            if str(user.object_id) != claims.oid:
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")

        async with DBSession() as session:
            document = await document_repo.read(item_id=document_id, session=session)

        return JSONResponse(
            {
                "document_id": str(document.id),
                "content": document.content,
                "name": document.name,
            }
        )

def make_delete_document() -> Callable[[Request], Awaitable[Response]]:
    async def delete_document(request: Request) -> Response:
        async with request.form(max_files=1000, max_fields=1000, max_part_size=1024 * 1024):
            user_id = request.path_params["user_id"]
            document_id = request.path_params["document_id"]
            object_store = create_obj_store()

            _stores.append(object_store)

            claims = await get_entra_id_claims(request)
            if Role.USER.value not in claims.roles:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            async with DBSession() as session:
                user = await user_repo.read(item_id=user_id, session=session)
                if str(user.object_id) != claims.oid:
                    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Forbidden")
                document = await document_repo.read(item_id=document_id, session=session)

            async with asyncio.TaskGroup() as tg, DBSession() as session:
                tg.create_task(document_repo.delete(item_id=document_id, session=session))
                tg.create_task(object_store.delete(blob_url=document.uri))

            return Response(status_code=status.HTTP_204_NO_CONTENT)

    return delete_document

parser = PDFParser()

def create_obj_store():

    object_store = AzureBlobStorage(
        config={
            "connection_string": app_settings.blob_storage_connection_string,
            "credential": ClientSecretCredential(
                tenant_id=app_settings.azure_tenant_id,
                client_id=app_settings.azure_client_id,
                client_secret=app_settings.azure_client_secret,
            ),
        },
        folder_name="dns-to-fd",
    )
    return object_store

routes = [
    Route(
        "/users/{user_id}/documents/",
        make_add_document(parser),
        methods=("POST",),
    ),
    Route(
        "/users/{user_id}/documents/{document_id}",
        get_document,
        methods=("GET",),
    ),
    Route(
        "/users/{user_id}/documents/{document_id}",
        make_delete_document(),
        methods=("DELETE",),
    ),
    # Route(
    #     "/users/{user_id}/documents/{document_id}/url",
    #     make_get_document_url(object_store),
    #     methods=("GET",),
    # ),
]
