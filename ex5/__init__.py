"""Reference implementation of the .ex5 file format, spec version 1.1."""

from .core import (
    Ex5,
    Ex5Error,
    ValidationError,
    EncryptionNotSupported,
    PermissionDenied,
    SPEC_VERSION,
)
from . import schema
from . import sync

__version__ = SPEC_VERSION
__all__ = [
    "Ex5",
    "Ex5Error",
    "ValidationError",
    "EncryptionNotSupported",
    "PermissionDenied",
    "SPEC_VERSION",
    "schema",
    "sync",
]
