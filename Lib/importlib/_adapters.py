from contextlib import suppress
from . import abc


class SpecLoaderAdapter:
    "\n    Adapt a package spec to adapt the underlying loader.\n    "

    def __init__(self, spec, adapter=(lambda spec: spec.loader)):
        self.spec = spec
        self.loader = adapter(spec)

    def __getattr__(self, name):
        return getattr(self.spec, name)


class TraversableResourcesLoader:
    "\n    Adapt a loader to provide TraversableResources.\n    "

    def __init__(self, spec):
        self.spec = spec

    def get_resource_reader(self, name):
        return DegenerateFiles(self.spec)._native()


class DegenerateFiles:
    "\n    Adapter for an existing or non-existant resource reader\n    to provide a degenerate .files().\n    "

    class Path(abc.Traversable):
        def iterdir(self):
            return iter(())

        def is_dir(self):
            return False

        is_file = exists = is_dir

        def joinpath(self, other):
            return DegenerateFiles.Path()

        def name(self):
            return ""

        def open(self):
            raise ValueError()

    def __init__(self, spec):
        self.spec = spec

    @property
    def _reader(self):
        with suppress(AttributeError):
            return self.spec.loader.get_resource_reader(self.spec.name)

    def _native(self):
        "\n        Return the native reader if it supports files().\n        "
        reader = self._reader
        return reader if hasattr(reader, "files") else self

    def __getattr__(self, attr):
        return getattr(self._reader, attr)

    def files(self):
        return DegenerateFiles.Path()


def wrap_spec(package):
    "\n    Construct a package spec with traversable compatibility\n    on the spec/loader/reader.\n    "
    return SpecLoaderAdapter(package.__spec__, TraversableResourcesLoader)
