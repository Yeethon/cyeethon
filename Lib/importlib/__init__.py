"A pure Python implementation of import."
__all__ = ["__import__", "import_module", "invalidate_caches", "reload"]
import _imp
import sys

try:
    import _frozen_importlib as _bootstrap
except ImportError:
    from . import _bootstrap

    _bootstrap._setup(sys, _imp)
else:
    _bootstrap.__name__ = "importlib._bootstrap"
    _bootstrap.__package__ = "importlib"
    try:
        _bootstrap.__file__ = __file__.replace("__init__.py", "_bootstrap.py")
    except NameError:
        pass
    sys.modules["importlib._bootstrap"] = _bootstrap
try:
    import _frozen_importlib_external as _bootstrap_external
except ImportError:
    from . import _bootstrap_external

    _bootstrap_external._set_bootstrap_module(_bootstrap)
    _bootstrap._bootstrap_external = _bootstrap_external
else:
    _bootstrap_external.__name__ = "importlib._bootstrap_external"
    _bootstrap_external.__package__ = "importlib"
    try:
        _bootstrap_external.__file__ = __file__.replace(
            "__init__.py", "_bootstrap_external.py"
        )
    except NameError:
        pass
    sys.modules["importlib._bootstrap_external"] = _bootstrap_external
_pack_uint32 = _bootstrap_external._pack_uint32
_unpack_uint32 = _bootstrap_external._unpack_uint32
import warnings
from ._bootstrap import __import__


def invalidate_caches():
    "Call the invalidate_caches() method on all meta path finders stored in\n    sys.meta_path (where implemented)."
    for finder in sys.meta_path:
        if hasattr(finder, "invalidate_caches"):
            finder.invalidate_caches()


def find_loader(name, path=None):
    "Return the loader for the specified module.\n\n    This is a backward-compatible wrapper around find_spec().\n\n    This function is deprecated in favor of importlib.util.find_spec().\n\n    "
    warnings.warn(
        "Deprecated since Python 3.4 and slated for removal in Python 3.10; use importlib.util.find_spec() instead",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        loader = sys.modules[name].__loader__
        if loader is None:
            raise ValueError("{}.__loader__ is None".format(name))
        else:
            return loader
    except KeyError:
        pass
    except AttributeError:
        raise ValueError("{}.__loader__ is not set".format(name)) from None
    spec = _bootstrap._find_spec(name, path)
    if spec is None:
        return None
    if spec.loader is None:
        if spec.submodule_search_locations is None:
            raise ImportError("spec for {} missing loader".format(name), name=name)
        raise ImportError("namespace packages do not have loaders", name=name)
    return spec.loader


def import_module(name, package=None):
    "Import a module.\n\n    The 'package' argument is required when performing a relative import. It\n    specifies the package to use as the anchor point from which to resolve the\n    relative import to an absolute import.\n\n    "
    level = 0
    if name.startswith("."):
        if not package:
            msg = "the 'package' argument is required to perform a relative import for {!r}"
            raise TypeError(msg.format(name))
        for character in name:
            if character != ".":
                break
            level += 1
    return _bootstrap._gcd_import(name[level:], package, level)


_RELOADING = {}


def reload(module):
    "Reload the module and return it.\n\n    The module must have been successfully imported before.\n\n    "
    try:
        name = module.__spec__.name
    except AttributeError:
        try:
            name = module.__name__
        except AttributeError:
            raise TypeError("reload() argument must be a module")
    if sys.modules.get(name) is not module:
        msg = "module {} not in sys.modules"
        raise ImportError(msg.format(name), name=name)
    if name in _RELOADING:
        return _RELOADING[name]
    _RELOADING[name] = module
    try:
        parent_name = name.rpartition(".")[0]
        if parent_name:
            try:
                parent = sys.modules[parent_name]
            except KeyError:
                msg = "parent {!r} not in sys.modules"
                raise ImportError(msg.format(parent_name), name=parent_name) from None
            else:
                pkgpath = parent.__path__
        else:
            pkgpath = None
        target = module
        spec = module.__spec__ = _bootstrap._find_spec(name, pkgpath, target)
        if spec is None:
            raise ModuleNotFoundError(
                f"spec not found for the module {name!r}", name=name
            )
        _bootstrap._exec(spec, module)
        return sys.modules[name]
    finally:
        try:
            del _RELOADING[name]
        except KeyError:
            pass
