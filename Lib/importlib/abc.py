"Abstract base classes related to import."
from . import _bootstrap_external
from . import machinery

try:
    import _frozen_importlib
except ImportError as exc:
    if exc.name != "_frozen_importlib":
        raise
    _frozen_importlib = None
try:
    import _frozen_importlib_external
except ImportError:
    _frozen_importlib_external = _bootstrap_external
from ._abc import Loader
import abc
import warnings
from typing import BinaryIO, Iterable, Text
from typing import Protocol, runtime_checkable


def _register(abstract_cls, *classes):
    for cls in classes:
        abstract_cls.register(cls)
        if _frozen_importlib is not None:
            try:
                frozen_cls = getattr(_frozen_importlib, cls.__name__)
            except AttributeError:
                frozen_cls = getattr(_frozen_importlib_external, cls.__name__)
            abstract_cls.register(frozen_cls)


class Finder(metaclass=abc.ABCMeta):
    "Legacy abstract base class for import finders.\n\n    It may be subclassed for compatibility with legacy third party\n    reimplementations of the import system.  Otherwise, finder\n    implementations should derive from the more specific MetaPathFinder\n    or PathEntryFinder ABCs.\n\n    Deprecated since Python 3.3\n    "

    def __init__(self):
        warnings.warn(
            "the Finder ABC is deprecated and slated for removal in Python 3.12; use MetaPathFinder or PathEntryFinder instead",
            DeprecationWarning,
        )

    @abc.abstractmethod
    def find_module(self, fullname, path=None):
        "An abstract method that should find a module.\n        The fullname is a str and the optional path is a str or None.\n        Returns a Loader object or None.\n        "
        warnings.warn(
            "importlib.abc.Finder along with its find_module() method are deprecated and slated for removal in Python 3.12; use MetaPathFinder.find_spec() or PathEntryFinder.find_spec() instead",
            DeprecationWarning,
        )


class MetaPathFinder(metaclass=abc.ABCMeta):
    "Abstract base class for import finders on sys.meta_path."

    def find_module(self, fullname, path):
        "Return a loader for the module.\n\n        If no module is found, return None.  The fullname is a str and\n        the path is a list of strings or None.\n\n        This method is deprecated since Python 3.4 in favor of\n        finder.find_spec(). If find_spec() exists then backwards-compatible\n        functionality is provided for this method.\n\n        "
        warnings.warn(
            "MetaPathFinder.find_module() is deprecated since Python 3.4 in favor of MetaPathFinder.find_spec() and is slated for removal in Python 3.12",
            DeprecationWarning,
            stacklevel=2,
        )
        if not hasattr(self, "find_spec"):
            return None
        found = self.find_spec(fullname, path)
        return found.loader if (found is not None) else None

    def invalidate_caches(self):
        "An optional method for clearing the finder's cache, if any.\n        This method is used by importlib.invalidate_caches().\n        "


_register(
    MetaPathFinder,
    machinery.BuiltinImporter,
    machinery.FrozenImporter,
    machinery.PathFinder,
    machinery.WindowsRegistryFinder,
)


class PathEntryFinder(metaclass=abc.ABCMeta):
    "Abstract base class for path entry finders used by PathFinder."

    def find_loader(self, fullname):
        "Return (loader, namespace portion) for the path entry.\n\n        The fullname is a str.  The namespace portion is a sequence of\n        path entries contributing to part of a namespace package. The\n        sequence may be empty.  If loader is not None, the portion will\n        be ignored.\n\n        The portion will be discarded if another path entry finder\n        locates the module as a normal module or package.\n\n        This method is deprecated since Python 3.4 in favor of\n        finder.find_spec(). If find_spec() is provided than backwards-compatible\n        functionality is provided.\n        "
        warnings.warn(
            "PathEntryFinder.find_loader() is deprecated since Python 3.4 in favor of PathEntryFinder.find_spec() (available since 3.4)",
            DeprecationWarning,
            stacklevel=2,
        )
        if not hasattr(self, "find_spec"):
            return (None, [])
        found = self.find_spec(fullname)
        if found is not None:
            if not found.submodule_search_locations:
                portions = []
            else:
                portions = found.submodule_search_locations
            return (found.loader, portions)
        else:
            return (None, [])

    find_module = _bootstrap_external._find_module_shim

    def invalidate_caches(self):
        "An optional method for clearing the finder's cache, if any.\n        This method is used by PathFinder.invalidate_caches().\n        "


_register(PathEntryFinder, machinery.FileFinder)


class ResourceLoader(Loader):
    "Abstract base class for loaders which can return data from their\n    back-end storage.\n\n    This ABC represents one of the optional protocols specified by PEP 302.\n\n    "

    @abc.abstractmethod
    def get_data(self, path):
        "Abstract method which when implemented should return the bytes for\n        the specified path.  The path must be a str."
        raise OSError


class InspectLoader(Loader):
    "Abstract base class for loaders which support inspection about the\n    modules they can load.\n\n    This ABC represents one of the optional protocols specified by PEP 302.\n\n    "

    def is_package(self, fullname):
        "Optional method which when implemented should return whether the\n        module is a package.  The fullname is a str.  Returns a bool.\n\n        Raises ImportError if the module cannot be found.\n        "
        raise ImportError

    def get_code(self, fullname):
        "Method which returns the code object for the module.\n\n        The fullname is a str.  Returns a types.CodeType if possible, else\n        returns None if a code object does not make sense\n        (e.g. built-in module). Raises ImportError if the module cannot be\n        found.\n        "
        source = self.get_source(fullname)
        if source is None:
            return None
        return self.source_to_code(source)

    @abc.abstractmethod
    def get_source(self, fullname):
        "Abstract method which should return the source code for the\n        module.  The fullname is a str.  Returns a str.\n\n        Raises ImportError if the module cannot be found.\n        "
        raise ImportError

    @staticmethod
    def source_to_code(data, path="<string>"):
        "Compile 'data' into a code object.\n\n        The 'data' argument can be anything that compile() can handle. The'path'\n        argument should be where the data was retrieved (when applicable)."
        return compile(data, path, "exec", dont_inherit=True)

    exec_module = _bootstrap_external._LoaderBasics.exec_module
    load_module = _bootstrap_external._LoaderBasics.load_module


_register(InspectLoader, machinery.BuiltinImporter, machinery.FrozenImporter)


class ExecutionLoader(InspectLoader):
    "Abstract base class for loaders that wish to support the execution of\n    modules as scripts.\n\n    This ABC represents one of the optional protocols specified in PEP 302.\n\n    "

    @abc.abstractmethod
    def get_filename(self, fullname):
        "Abstract method which should return the value that __file__ is to be\n        set to.\n\n        Raises ImportError if the module cannot be found.\n        "
        raise ImportError

    def get_code(self, fullname):
        "Method to return the code object for fullname.\n\n        Should return None if not applicable (e.g. built-in module).\n        Raise ImportError if the module cannot be found.\n        "
        source = self.get_source(fullname)
        if source is None:
            return None
        try:
            path = self.get_filename(fullname)
        except ImportError:
            return self.source_to_code(source)
        else:
            return self.source_to_code(source, path)


_register(ExecutionLoader, machinery.ExtensionFileLoader)


class FileLoader(_bootstrap_external.FileLoader, ResourceLoader, ExecutionLoader):
    "Abstract base class partially implementing the ResourceLoader and\n    ExecutionLoader ABCs."


_register(FileLoader, machinery.SourceFileLoader, machinery.SourcelessFileLoader)


class SourceLoader(_bootstrap_external.SourceLoader, ResourceLoader, ExecutionLoader):
    "Abstract base class for loading source code (and optionally any\n    corresponding bytecode).\n\n    To support loading from source code, the abstractmethods inherited from\n    ResourceLoader and ExecutionLoader need to be implemented. To also support\n    loading from bytecode, the optional methods specified directly by this ABC\n    is required.\n\n    Inherited abstractmethods not implemented in this ABC:\n\n        * ResourceLoader.get_data\n        * ExecutionLoader.get_filename\n\n    "

    def path_mtime(self, path):
        "Return the (int) modification time for the path (str)."
        if self.path_stats.__func__ is SourceLoader.path_stats:
            raise OSError
        return int(self.path_stats(path)["mtime"])

    def path_stats(self, path):
        "Return a metadata dict for the source pointed to by the path (str).\n        Possible keys:\n        - 'mtime' (mandatory) is the numeric timestamp of last source\n          code modification;\n        - 'size' (optional) is the size in bytes of the source code.\n        "
        if self.path_mtime.__func__ is SourceLoader.path_mtime:
            raise OSError
        return {"mtime": self.path_mtime(path)}

    def set_data(self, path, data):
        "Write the bytes to the path (if possible).\n\n        Accepts a str path and data as bytes.\n\n        Any needed intermediary directories are to be created. If for some\n        reason the file cannot be written because of permissions, fail\n        silently.\n        "


_register(SourceLoader, machinery.SourceFileLoader)


class ResourceReader(metaclass=abc.ABCMeta):
    "Abstract base class for loaders to provide resource reading support."

    @abc.abstractmethod
    def open_resource(self, resource: Text) -> BinaryIO:
        "Return an opened, file-like object for binary reading.\n\n        The 'resource' argument is expected to represent only a file name.\n        If the resource cannot be found, FileNotFoundError is raised.\n        "
        raise FileNotFoundError

    @abc.abstractmethod
    def resource_path(self, resource: Text) -> Text:
        "Return the file system path to the specified resource.\n\n        The 'resource' argument is expected to represent only a file name.\n        If the resource does not exist on the file system, raise\n        FileNotFoundError.\n        "
        raise FileNotFoundError

    @abc.abstractmethod
    def is_resource(self, path: Text) -> bool:
        "Return True if the named 'path' is a resource.\n\n        Files are resources, directories are not.\n        "
        raise FileNotFoundError

    @abc.abstractmethod
    def contents(self) -> Iterable[str]:
        "Return an iterable of entries in `package`."
        raise FileNotFoundError


@runtime_checkable
class Traversable(Protocol):
    "\n    An object with a subset of pathlib.Path methods suitable for\n    traversing directories and opening files.\n    "

    @abc.abstractmethod
    def iterdir(self):
        "\n        Yield Traversable objects in self\n        "

    def read_bytes(self):
        "\n        Read contents of self as bytes\n        "
        with self.open("rb") as strm:
            return strm.read()

    def read_text(self, encoding=None):
        "\n        Read contents of self as text\n        "
        with self.open(encoding=encoding) as strm:
            return strm.read()

    @abc.abstractmethod
    def is_dir(self) -> bool:
        "\n        Return True if self is a dir\n        "

    @abc.abstractmethod
    def is_file(self) -> bool:
        "\n        Return True if self is a file\n        "

    @abc.abstractmethod
    def joinpath(self, child):
        "\n        Return Traversable child in self\n        "

    def __truediv__(self, child):
        "\n        Return Traversable child in self\n        "
        return self.joinpath(child)

    @abc.abstractmethod
    def open(self, mode="r", *args, **kwargs):
        "\n        mode may be 'r' or 'rb' to open as text or binary. Return a handle\n        suitable for reading (same as pathlib.Path.open).\n\n        When opening as text, accepts encoding parameters such as those\n        accepted by io.TextIOWrapper.\n        "

    @abc.abstractproperty
    def name(self) -> str:
        "\n        The base name of this object without any parent references.\n        "


class TraversableResources(ResourceReader):
    "\n    The required interface for providing traversable\n    resources.\n    "

    @abc.abstractmethod
    def files(self):
        "Return a Traversable object for the loaded package."

    def open_resource(self, resource):
        return self.files().joinpath(resource).open("rb")

    def resource_path(self, resource):
        raise FileNotFoundError(resource)

    def is_resource(self, path):
        return self.files().joinpath(path).is_file()

    def contents(self):
        return (item.name for item in self.files().iterdir())
