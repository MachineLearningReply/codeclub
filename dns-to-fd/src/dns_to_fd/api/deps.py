from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
import datetime
from enum import StrEnum
import threading
from types import TracebackType
from typing import TYPE_CHECKING, Any, Protocol

from async_lru import alru_cache
from httpx import AsyncClient, Client
import jwt
from msgspec import Struct
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import Request

from dns_to_fd.settings import app_settings

__all__ = [
    "Role", "EntraOIDCAuthenticator", "AuthHeader", "Claims", "AuthScheme", "DBSession", "get_entra_id_claims"
]


if TYPE_CHECKING:
    from azure.core.credentials import AccessToken, TokenCredential
    from azure.core.credentials_async import AsyncTokenCredential


engine = create_async_engine(url=app_settings.db_connection_string, future=True)
session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)


class AuthorizationError(Exception): ...


class TokenProviderError(Exception): ...


class DBSession:
    def __init__(self) -> None:
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        self.session = session_factory()
        await self.session.__aenter__()
        return self.session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        session = self.session
        if session is None:
            raise RuntimeError("Database session was not initialized")

        if exc_type is not None:
            await session.rollback()
        else:
            await session.commit()

        await session.__aexit__(exc_type, exc_val, exc_tb)


class TokenProvider(Protocol):
    def get_token(self) -> AccessToken: ...

    async def aget_token(self) -> AccessToken: ...


class AzureTokenProvider(TokenProvider):
    def __init__(
        self,
        scopes: Sequence[str] = ("https://graph.microsoft.com/.default",),
        buffer_seconds: int = 300,
        credential: TokenCredential | None = None,
        acredential: AsyncTokenCredential | None = None,
    ):
        self._credential = credential
        self._acredential = acredential
        self.scopes = scopes
        self._buffer_seconds = buffer_seconds

        self._thread_lock = threading.Lock()
        self._alock = asyncio.Lock()
        self._current_token: AccessToken | None = None

        assert self._credential or self._acredential

    def get_token(self) -> AccessToken:
        if self._credential is None:
            raise RuntimeError("No synchronous credential provided. Use aget_token() instead.")

        with self._thread_lock:
            if self._current_token and not self._is_token_expired(self._current_token):
                return self._current_token

            try:
                self._current_token = self._credential.get_token(*self.scopes)
                return self._current_token
            except Exception as e:
                raise TokenProviderError from e

    async def aget_token(self) -> AccessToken:
        if self._acredential is None:
            raise RuntimeError("No asynchronous credential provided. Use get_token() instead.")

        if self._current_token and not self._is_token_expired(self._current_token):
            return self._current_token

        async with self._alock:
            if self._current_token and not self._is_token_expired(self._current_token):
                return self._current_token

            try:
                new_token = await self._acredential.get_token(*self.scopes)
                self._current_token = new_token
                return new_token
            except Exception as e:
                raise TokenProviderError from e

    def _is_token_expired(self, token: AccessToken | None) -> bool:
        if not token:
            return True

        current_time = datetime.datetime.now(datetime.UTC).timestamp()
        expiry_with_buffer = token.expires_on - self._buffer_seconds
        return current_time >= expiry_with_buffer


class Role(StrEnum):
    ADMIN = "Admin"
    CONTRIBUTOR = "Contributor"
    READER = "Reader"


class AuthScheme(StrEnum):
    BEARER = "Bearer"


class AuthHeader(Struct):
    scheme: AuthScheme | str  # HACK: type checking
    value: str


class Claims(Struct):
    iss: str
    aud: str
    exp: int
    iat: int
    nbf: int
    sub: str
    tid: str
    aid: str
    oid: str
    roles: list[str]


def _required_str_claim(claims: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = claims.get(key)
        if isinstance(value, str):
            return value
    raise AuthorizationError(f"Missing or invalid token claim: {'/'.join(keys)}")


def _required_int_claim(claims: Mapping[str, Any], key: str) -> int:
    value = claims.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise AuthorizationError(f"Missing or invalid token claim: {key}")


def _required_roles_claim(claims: Mapping[str, Any]) -> list[str]:
    roles = claims.get("roles")
    if roles is None:
        raise AuthorizationError("Missing token roles claim")
    if not isinstance(roles, list):
        raise AuthorizationError("Invalid token roles claim")

    role_values: list[str] = []
    for role in roles:
        if not isinstance(role, str):
            raise AuthorizationError("Invalid token roles claim")
        role_values.append(role)
    return role_values


@alru_cache
async def get_jwt_keys(jwks_url: str) -> dict[str, jwt.PyJWK]:
    async with AsyncClient() as client:
        resp = await client.get(jwks_url)
        resp.raise_for_status()

    jwks = resp.json()
    return {key["kid"]: jwt.PyJWK.from_dict(key) for key in jwks["keys"]}


class EntraOIDCAuthenticator(BaseModel):
    tenant_id: str
    client_id: str
    jwks_url: str | None = None
    authorization_url: str | None = None
    token_url: str | None = None
    config_url: str | None = None

    def model_post_init(self, context: Any) -> None:
        config_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/v2.0/.well-known/openid-configuration"
        )
        self.config_url = config_url

        with Client() as client:
            resp = client.get(config_url)
            resp.raise_for_status()
            open_id_config = resp.json()

        if not self.jwks_url:
            jwks_url = (
                open_id_config.get("jwks_uri", None)
                or f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
            )
            self.jwks_url = jwks_url

        if not self.authorization_url:
            authorization_url = (
                open_id_config.get("authorization_endpoint", None)
                or f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
            )
            self.authorization_url = authorization_url

        if not self.token_url:
            token_url = (
                open_id_config["token_endpoint"]
                or f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            )
            self.token_url = token_url

    async def _load_signing_keys(self) -> dict[str, jwt.PyJWK]:
        return await get_jwt_keys(self.jwks_url)

    async def get_claims(self, header: AuthHeader) -> Claims:
        if header.scheme != AuthScheme.BEARER:
            raise ValueError(f"Invalid authorization scheme {header.scheme}")

        token = header.value
        try:
            unverified_claims = jwt.decode(token, options={"verify_signature": False})
            version = unverified_claims.get("ver", "1.0")
            if version == "2.0":
                expected_iss = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            else:
                expected_iss = f"https://sts.windows.net/{self.tenant_id}/"

            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if not isinstance(kid, str):
                raise AuthorizationError("Invalid token key ID")
            jwk = (await self._load_signing_keys()).get(kid)
            if not jwk:
                raise AuthorizationError("Invalid token key ID")

            public_key = jwk.key
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=[f"api://{self.client_id}", self.client_id],
                issuer=expected_iss,
                options={
                    "verify_aud": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                    "verify_signature": True,
                    "verify_iat": True,
                },
            )
        except jwt.exceptions.DecodeError:
            raise AuthorizationError("Invalid token format") from None
        except jwt.exceptions.ExpiredSignatureError:
            raise AuthorizationError("Token has expired") from None
        except jwt.exceptions.InvalidIssuerError:
            raise AuthorizationError(f"Invalid issuer {expected_iss = }") from None
        except Exception as e:
            raise AuthorizationError("Could not decode token") from e

        verified_claims = Claims(
            iss=_required_str_claim(claims, "iss"),
            aud=_required_str_claim(claims, "aud"),
            exp=_required_int_claim(claims, "exp"),
            iat=_required_int_claim(claims, "iat"),
            nbf=_required_int_claim(claims, "nbf"),
            sub=_required_str_claim(claims, "sub"),
            tid=_required_str_claim(claims, "tid"),
            aid=_required_str_claim(claims, "appid", "azp"),
            oid=_required_str_claim(claims, "oid"),
            roles=_required_roles_claim(claims),
        )

        return verified_claims


entraid_authenticator = EntraOIDCAuthenticator(
    tenant_id=app_settings.azure_tenant_id,
    client_id=app_settings.azure_client_id,
)


async def get_entra_id_claims(request: Request) -> Claims:
    auth = request.headers.get("authorization")
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Auth Header")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Auth Header")

    return await entraid_authenticator.get_claims(
        AuthHeader(
            scheme=AuthScheme.BEARER,
            value=auth.removeprefix("Bearer "),
        )
    )
