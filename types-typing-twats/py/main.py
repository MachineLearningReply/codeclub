################################################
"""Everything is an expression"""
import asyncio
import dis

from flask import Flask

x = 2
print(dis.dis('x = 2'))

# Typically, variables are containers that have binding to an expression '2', which evaluates to 2 (placed on stack)
# In Python, 2 is evaluated to a PyLongObject (heap-allocated int object that contains ob_digit array holding data in a C uint32_t[]) and then 'x' is bound to that PyObject* in the current namespace/environment

################################################
"""New types"""

def _pos_int(cls, v: int):
    if v <= 0:
        raise ValueError('Value must be positive')
    return int.__new__(cls, v)

PositiveInt = type('PositiveInt', (int,), {'__new__': _pos_int})

################################################
"""Static Checks to support Runtime Checks"""
from fastapi import FastAPI, Depends
from pydantic import BaseModel


class DB:
    def __init__(self):
        pass
    async def insert_user(self, user_id: int, email: str):
        pass

async def get_db() -> DB:
    return DB()


class CreateUserRequest(BaseModel):
    email: str
    user_id: int

app = FastAPI()
@app.post("/users")
async def create_user(request: CreateUserRequest, db: DB = Depends(get_db)):
    user_id = request.user_id
    email = request.email
    await db.insert_user(user_id, email)
    return {'status': 'ok'}

################################################
"""Function types"""

from collections.abc import Callable, Sequence


def apply_twice(f: Callable[[int], int], x: int) -> int:
    return f(f(x))
################################################
"""Strong Typing as opposed to JS"""

def is_premium(users):
    return users > "100"

#print(is_premium(42))
#print(is_premium(200))
###############################################
"""Bottom Type"""

from typing import Never, NoReturn, \
    Container  # https://typing.python.org/en/latest/guides/unreachable.html#never-and-noreturn

def assert_never(arg: Never) -> Never:
    raise AssertionError("Expected code to be unreachable")

# can never be called
#def func() -> int:
#    assert_never(2)

def stop() -> NoReturn:
    raise RuntimeError('no way')

###############################################
"""Top Type"""
def func(x: object):
    return x

print(func(2))
##############################################
"""Width Subtyping"""

from typing import TypedDict
from math import sqrt

class Point1D(TypedDict):
    x: int

class Point2D(TypedDict):
    x: int
    y: int

class Point3D(TypedDict):
    x: int
    y: int
    z: int  # extra field — Point3D is wider than Point2D, so Point3D <: Point2D

def distance_from_origin(point: Point2D) -> float:
    return sqrt(point["x"]**2 + point["y"]**2)

point_3d: Point3D = {"x": 3, "y": 4, "z": 5}
distance_from_origin(point_3d)  # width subtyping: more fields = subtype

#############################################
"""Nominal vs Structural"""

# nominal
class Cache:
    ...

class Redis(Cache):
    ...

# structural
class ObjectStore:
    def add(self): ...

class AzureBlobStorage:
    def add(self): ...

##############################################
"""Variance"""
from collections.abc import Container

# Covariance: Producer Types

class DataStore:
    ...

class S3Bucket(DataStore):
    ...

class DataStoreCollection:
    def get(self) -> DataStore:
        return DataStore()

class ObjectStoreCollection:
    def get(self) -> S3Bucket:
        return S3Bucket()

######################################
"""LSP Violation"""

from dataclasses import dataclass
from typing import ClassVar, Any
from datetime import datetime

@dataclass(frozen=True)
class Entity:
    id: int

class Repository:
    def save(self, entity: Entity) -> None:
        """Idempotent method to save Entity"""
        raise NotImplementedError


class AuditedRepository(Repository):

    audited_log: ClassVar[list[str]] = []

    def __init__(self, db: Any) -> None:
        self.db = db

    def save(self, entity: Entity):
        self.db.save(entity)
        self.audited_log.append(f"Saved {entity.id} at {datetime.now()}")
        # NOT IDEMPOTENT — creates duplicate audit entries!
##########################################
"""Gradually typing Flask"""

from flask import Flask, jsonify, abort
from typing import TypedDict, Required


class _StubDB:
    def query(self, sql: str, *args: object) -> Any:
        raise NotImplementedError


flask_app = Flask(__name__)
stub_db = _StubDB()

# Step 0: Untyped — no annotations, opaque to a type checker
@flask_app.route("/v0/users/<user_id>")
def get_user_v0(user_id):
    user = stub_db.query("SELECT * FROM users WHERE id = ?", user_id)
    return jsonify(user)

# Step 1: Add Any — opts in to type checking without committing to specifics
@flask_app.route("/v1/users/<user_id>")
def get_user_v1(user_id: str) -> Any:
    user = stub_db.query("SELECT * FROM users WHERE id = ?", user_id)
    return jsonify(user)

# Step 2: Narrow to a concrete TypedDict — type checker can now verify the shape
class UserDict(TypedDict):
    id: Required[int]
    username: str
    email: str

@flask_app.route("/v2/users/<user_id>")
def get_user_v2(user_id: str) -> UserDict:
    user = stub_db.query("SELECT * FROM users WHERE id = ?", user_id)
    if user is None:
        abort(404)
    return user  # type checker verifies this matches UserDict

##########################################
# Explicit Opt-In

from abc import ABC, abstractmethod
from decimal import Decimal

class PaymentProcessor(ABC):
    @abstractmethod
    def process_payment(self, amount: Decimal) -> str:
        ...

    @abstractmethod
    def refund(self, transaction_id: str) -> None:
        ...


class StripeProcessor(PaymentProcessor):
    def process_payment(self, amount: Decimal) -> str:
        return "a string"

    def refund(self, transaction_id: str) -> None:
        return

#####################################
class PaymentProcessor(ABC):
    @abstractmethod
    def process_payment(self, amount: Decimal) -> str: ...

class ThirdPartyPayment:  # Doesn't inherit from PaymentProcessor
    def process_payment(self, amount: Decimal) -> str:
        print(amount)
        return "external_txn"

# Register as virtual subclass
PaymentProcessor.register(ThirdPartyPayment)

print(isinstance(ThirdPartyPayment(), PaymentProcessor))  # True

#########################################
""" Structural Subtyping - implicit compatibility"""

from typing import Protocol, Any, runtime_checkable
from msgspec import Struct

class CacheData(Struct):
    key: str
    value: Any

class CacheInterface(Protocol):
    async def aget(self, key: str) -> CacheData: ...

    async def aset(self, entry: Any) -> None: ...

    # async def f(self): pass


class RedisCache(CacheInterface):
    async def aget(self, key: str) -> CacheData:
        return CacheData(key=key, value='value')
    async def aset(self, entry: Any) -> None: return

async def func(cache: CacheInterface) -> None:
    await asyncio.gather(cache.aget('key1'), cache.aget('key2'))
    # await cache.f()

func(RedisCache())


#########################################
"""Protocol in Action"""

from typing import Protocol, Any, ClassVar
import logging


class Plugin(Protocol):

    def initialize(self, config: dict[str, Any]) -> None: ...

    def process(self, data: dict[str, Any]) -> dict[str, Any]: ...

    def cleanup(self) -> None: ...


class PluginManager:
    def __init__(self):
        self._plugins: list[Plugin] = []

    def register(self, plugin: Plugin) -> None:
        self._plugins.append(plugin)
        plugin.initialize({})

    def process_all(self, data: dict[str, Any]) -> dict[str, Any]:
        result = dict(data)
        for plugin in self._plugins:
            result = plugin.process(result)
        return result



# Third-party plugins can be added without modifying PluginManager
class LoggingPlugin:  # No inheritance from Plugin!

    def initialize(self, config: dict[str, Any]) -> None:
        self.logger = logging.getLogger(LoggingPlugin.__name__)

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        self.logger.info(f"Processing: {data}")
        return data

    def cleanup(self) -> None:
        del self.logger

# Type checker verifies LoggingPlugin satisfies Plugin
manager = PluginManager()
manager.register(LoggingPlugin())

##############################
"""Generics"""

# PEP 484
from typing import TypeVar, Generic

T = TypeVar("T")
#
# def identity(x: T) -> T:
#     return x

# PEP 695
def identity[T](x: T) -> T:
    return x

class Box(Generic[T]):
    ...

# New style
# class Box[T]:
#     ...

# Pep 484
from typing import TypeVar

class Comparable(Protocol):
    def __lt__(self, other: Any) -> bool: ...

# PEP 695
def minimum[T: Comparable](x: T, y: T) -> T:
    return x if x < y else y

class Something[T: (str, float)]:
    t = T
    def func(self, x: T) -> None:
        print(x)
        return


################################
"""collections"""
################################

from collections.abc import Sequence
import collections
from typing import Any

class CustomSequence(Sequence):
    def __init__(self, obj: Sequence[Any]):
        self._internal = obj

    def __len__(self) -> int:
        return len(self._internal)

    def __getitem__(self, idx: int):
        return self._internal[idx+1]

    def __contains__(self, value: Any) -> bool:
        return value in self._internal

seq = CustomSequence(('h', 'e', 'l', 'l', '\\0'))
print(isinstance(seq, collections.abc.Sized))
print(isinstance(seq, collections.abc.Container))
print(isinstance(seq, Sequence))


import abc










from collections.abc import Sized, Container, Sequence