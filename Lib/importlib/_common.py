import os
import pathlib
import tempfile
import functools
import contextlib
import types
import importlib
from typing import Union, Any, Optional
from .abc import ResourceReader
from ._adapters import wrap_spec

Package = Union[(types.ModuleType, str)]


def files(package):
    "\n    Get a Traversable resource from a package\n    "
    return from_package(get_package(package))


def normalize_path(path):
    "Normalize a path by ensuring it is a string.\n\n    If the resulting string contains path separators, an exception is raised.\n    "
    str_path = str(path)
    (parent, file_name) = os.path.split(str_path)
    if parent:
        raise ValueError("{!r} must be only a file name".format(path))
    return file_name


def get_resource_reader(package):
    "\n    Return the package's loader if it's a ResourceReader.\n    "
    spec = package.__spec__
    reader = getattr(spec.loader, "get_resource_reader", None)
    if reader is None:
        return None
    return reader(spec.name)


def resolve(cand):
    return cand if isinstance(cand, types.ModuleType) else importlib.import_module(cand)


def get_package(package):
    "Take a package name or module object and return the module.\n\n    Raise an exception if the resolved module is not a package.\n    "
    resolved = resolve(package)
    if wrap_spec(resolved).submodule_search_locations is None:
        raise TypeError("{!r} is not a package".format(package))
    return resolved


def from_package(package):
    "\n    Return a Traversable object for the given package.\n\n    "
    spec = wrap_spec(package)
    reader = spec.loader.get_resource_reader(spec.name)
    return reader.files()


@contextlib.contextmanager
def _tempfile(reader, suffix=""):
    (fd, raw_path) = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(fd, reader())
        os.close(fd)
        del reader
        (yield pathlib.Path(raw_path))
    finally:
        try:
            os.remove(raw_path)
        except FileNotFoundError:
            pass


@functools.singledispatch
def as_file(path):
    "\n    Given a Traversable object, return that object as a\n    path on the local file system in a context manager.\n    "
    return _tempfile(path.read_bytes, suffix=path.name)


@as_file.register(pathlib.Path)
@contextlib.contextmanager
def _(path):
    "\n    Degenerate behavior for pathlib.Path objects.\n    "
    (yield path)
