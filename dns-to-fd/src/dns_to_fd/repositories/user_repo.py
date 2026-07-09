from __future__ import annotations

from dns_to_fd.models import User

from .base_repo import AsyncSQLBaseRepository


class UserRepository(AsyncSQLBaseRepository[User]): ...
