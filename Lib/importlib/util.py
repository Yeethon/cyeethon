"Utility code for constructing importers, etc."
from ._abc import Loader
from ._bootstrap import module_from_spec
from ._bootstrap import _resolve_name
from ._bootstrap import spec_from_loader
from ._bootstrap import _find_spec
from ._bootstrap_external import MAGIC_NUMBER
from ._bootstrap_external import _RAW_MAGIC_NUMBER
from ._bootstrap_external import cache_from_source
from ._bootstrap_external import decode_source
from ._bootstrap_external import source_from_cache
from ._bootstrap_external import spec_from_file_location
from contextlib import contextmanager
import _imp
import functools
import sys
import types
import warnings


def source_hash(source_bytes):
    "Return the hash of *source_bytes* as used in hash-based pyc files."
    return _imp.source_hash(_RAW_MAGIC_NUMBER, source_bytes)


def resolve_name(name, package):
    "Resolve a relative module name to an absolute one."
    if not name.startswith("."):
        return name
    elif not package:
        raise ImportError(
            f"no package specified for {repr(name)} (required for relative module names)"
        )
    level = 0
    for character in name:
        if character != ".":
            break
        level += 1
    return _resolve_name(name[level:], package, level)


def _find_spec_from_path(name, path=None):
    "Return the spec for the specified module.\n\n    First, sys.modules is checked to see if the module was already imported. If\n    so, then sys.modules[name].__spec__ is returned. If that happens to be\n    set to None, then ValueError is raised. If the module is not in\n    sys.modules, then sys.meta_path is searched for a suitable spec with the\n    value of 'path' given to the finders. None is returned if no spec could\n    be found.\n\n    Dotted names do not have their parent packages implicitly imported. You will\n    most likely need to explicitly import all parent packages in the proper\n    order for a submodule to get the correct spec.\n\n    "
    if name not in sys.modules:
        return _find_spec(name, path)
    else:
        module = sys.modules[name]
        if module is None:
            return None
        try:
            spec = module.__spec__
        except AttributeError:
            raise ValueError("{}.__spec__ is not set".format(name)) from None
        else:
            if spec is None:
                raise ValueError("{}.__spec__ is None".format(name))
            return spec


def find_spec(name, package=None):
    "Return the spec for the specified module.\n\n    First, sys.modules is checked to see if the module was already imported. If\n    so, then sys.modules[name].__spec__ is returned. If that happens to be\n    set to None, then ValueError is raised. If the module is not in\n    sys.modules, then sys.meta_path is searched for a suitable spec with the\n    value of 'path' given to the finders. None is returned if no spec could\n    be found.\n\n    If the name is for submodule (contains a dot), the parent module is\n    automatically imported.\n\n    The name and package arguments work the same as importlib.import_module().\n    In other words, relative module names (with leading dots) work.\n\n    "
    fullname = resolve_name(name, package) if name.startswith(".") else name
    if fullname not in sys.modules:
        parent_name = fullname.rpartition(".")[0]
        if parent_name:
            parent = __import__(parent_name, fromlist=["__path__"])
            try:
                parent_path = parent.__path__
            except AttributeError as e:
                raise ModuleNotFoundError(
                    f"__path__ attribute not found on {parent_name!r} while trying to find {fullname!r}",
                    name=fullname,
                ) from e
        else:
            parent_path = None
        return _find_spec(fullname, parent_path)
    else:
        module = sys.modules[fullname]
        if module is None:
            return None
        try:
            spec = module.__spec__
        except AttributeError:
            raise ValueError("{}.__spec__ is not set".format(name)) from None
        else:
            if spec is None:
                raise ValueError("{}.__spec__ is None".format(name))
            return spec


@contextmanager
def _module_to_load(name):
    is_reload = name in sys.modules
    module = sys.modules.get(name)
    if not is_reload:
        module = type(sys)(name)
        module.__initializing__ = True
        sys.modules[name] = module
    try:
        (yield module)
    except Exception:
        if not is_reload:
            try:
                del sys.modules[name]
            except KeyError:
                pass
    finally:
        module.__initializing__ = False


def set_package(fxn):
    "Set __package__ on the returned module.\n\n    This function is deprecated.\n\n    "

    @functools.wraps(fxn)
    def set_package_wrapper(*args, **kwargs):
        warnings.warn(
            "The import system now takes care of this automatically; this decorator is slated for removal in Python 3.12",
            DeprecationWarning,
            stacklevel=2,
        )
        module = fxn(*args, **kwargs)
        if getattr(module, "__package__", None) is None:
            module.__package__ = module.__name__
            if not hasattr(module, "__path__"):
                module.__package__ = module.__package__.rpartition(".")[0]
        return module

    return set_package_wrapper


def set_loader(fxn):
    "Set __loader__ on the returned module.\n\n    This function is deprecated.\n\n    "

    @functools.wraps(fxn)
    def set_loader_wrapper(self, *args, **kwargs):
        warnings.warn(
            "The import system now takes care of this automatically; this decorator is slated for removal in Python 3.12",
            DeprecationWarning,
            stacklevel=2,
        )
        module = fxn(self, *args, **kwargs)
        if getattr(module, "__loader__", None) is None:
            module.__loader__ = self
        return module

    return set_loader_wrapper


def module_for_loader(fxn):
    "Decorator to handle selecting the proper module for loaders.\n\n    The decorated function is passed the module to use instead of the module\n    name. The module passed in to the function is either from sys.modules if\n    it already exists or is a new module. If the module is new, then __name__\n    is set the first argument to the method, __loader__ is set to self, and\n    __package__ is set accordingly (if self.is_package() is defined) will be set\n    before it is passed to the decorated function (if self.is_package() does\n    not work for the module it will be set post-load).\n\n    If an exception is raised and the decorator created the module it is\n    subsequently removed from sys.modules.\n\n    The decorator assumes that the decorated function takes the module name as\n    the second argument.\n\n    "
    warnings.warn(
        "The import system now takes care of this automatically; this decorator is slated for removal in Python 3.12",
        DeprecationWarning,
        stacklevel=2,
    )

    @functools.wraps(fxn)
    def module_for_loader_wrapper(self, fullname, *args, **kwargs):
        with _module_to_load(fullname) as module:
            module.__loader__ = self
            try:
                is_package = self.is_package(fullname)
            except (ImportError, AttributeError):
                pass
            else:
                if is_package:
                    module.__package__ = fullname
                else:
                    module.__package__ = fullname.rpartition(".")[0]
            return fxn(self, module, *args, **kwargs)

    return module_for_loader_wrapper


class _LazyModule(types.ModuleType):
    "A subclass of the module type which triggers loading upon attribute access."

    def __getattribute__(self, attr):
        "Trigger the load of the module and return the attribute."
        self.__class__ = types.ModuleType
        original_name = self.__spec__.name
        attrs_then = self.__spec__.loader_state["__dict__"]
        attrs_now = self.__dict__
        attrs_updated = {}
        for (key, value) in attrs_now.items():
            if key not in attrs_then:
                attrs_updated[key] = value
            elif id(attrs_now[key]) != id(attrs_then[key]):
                attrs_updated[key] = value
        self.__spec__.loader.exec_module(self)
        if original_name in sys.modules:
            if id(self) != id(sys.modules[original_name]):
                raise ValueError(
                    f"module object for {original_name!r} substituted in sys.modules during a lazy load"
                )
        self.__dict__.update(attrs_updated)
        return getattr(self, attr)

    def __delattr__(self, attr):
        "Trigger the load and then perform the deletion."
        self.__getattribute__(attr)
        delattr(self, attr)


class LazyLoader(Loader):
    "A loader that creates a module which defers loading until attribute access."

    @staticmethod
    def __check_eager_loader(loader):
        if not hasattr(loader, "exec_module"):
            raise TypeError("loader must define exec_module()")

    @classmethod
    def factory(cls, loader):
        "Construct a callable which returns the eager loader made lazy."
        cls.__check_eager_loader(loader)
        return lambda *args, **kwargs: cls(loader(*args, **kwargs))

    def __init__(self, loader):
        self.__check_eager_loader(loader)
        self.loader = loader

    def create_module(self, spec):
        return self.loader.create_module(spec)

    def exec_module(self, module):
        "Make the module load lazily."
        module.__spec__.loader = self.loader
        module.__loader__ = self.loader
        loader_state = {}
        loader_state["__dict__"] = module.__dict__.copy()
        loader_state["__class__"] = module.__class__
        module.__spec__.loader_state = loader_state
        module.__class__ = _LazyModule
