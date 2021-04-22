import contextlib
import importlib
import importlib.util
import os
import sys
import unittest
import warnings
from .os_helper import unlink


@contextlib.contextmanager
def _ignore_deprecated_imports(ignore=True):
    "Context manager to suppress package and module deprecation\n    warnings when importing them.\n\n    If ignore is False, this context manager has no effect.\n    "
    if ignore:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", ".+ (module|package)", DeprecationWarning)
            (yield)
    else:
        (yield)


def unload(name):
    try:
        del sys.modules[name]
    except KeyError:
        pass


def forget(modname):
    "'Forget' a module was ever imported.\n\n    This removes the module from sys.modules and deletes any PEP 3147/488 or\n    legacy .pyc files.\n    "
    unload(modname)
    for dirname in sys.path:
        source = os.path.join(dirname, (modname + ".py"))
        unlink((source + "c"))
        for opt in ("", 1, 2):
            unlink(importlib.util.cache_from_source(source, optimization=opt))


def make_legacy_pyc(source):
    "Move a PEP 3147/488 pyc file to its legacy pyc location.\n\n    :param source: The file system path to the source file.  The source file\n        does not need to exist, however the PEP 3147/488 pyc file must exist.\n    :return: The file system path to the legacy pyc file.\n    "
    pyc_file = importlib.util.cache_from_source(source)
    up_one = os.path.dirname(os.path.abspath(source))
    legacy_pyc = os.path.join(up_one, (source + "c"))
    os.rename(pyc_file, legacy_pyc)
    return legacy_pyc


def import_module(name, deprecated=False, *, required_on=()):
    "Import and return the module to be tested, raising SkipTest if\n    it is not available.\n\n    If deprecated is True, any module or package deprecation messages\n    will be suppressed. If a module is required on a platform but optional for\n    others, set required_on to an iterable of platform prefixes which will be\n    compared against sys.platform.\n    "
    with _ignore_deprecated_imports(deprecated):
        try:
            return importlib.import_module(name)
        except ImportError as msg:
            if sys.platform.startswith(tuple(required_on)):
                raise
            raise unittest.SkipTest(str(msg))


def _save_and_remove_module(name, orig_modules):
    "Helper function to save and remove a module from sys.modules\n\n    Raise ImportError if the module can't be imported.\n    "
    if name not in sys.modules:
        __import__(name)
        del sys.modules[name]
    for modname in list(sys.modules):
        if (modname == name) or modname.startswith((name + ".")):
            orig_modules[modname] = sys.modules[modname]
            del sys.modules[modname]


def _save_and_block_module(name, orig_modules):
    "Helper function to save and block a module in sys.modules\n\n    Return True if the module was in sys.modules, False otherwise.\n    "
    saved = True
    try:
        orig_modules[name] = sys.modules[name]
    except KeyError:
        saved = False
    sys.modules[name] = None
    return saved


def import_fresh_module(name, fresh=(), blocked=(), deprecated=False):
    "Import and return a module, deliberately bypassing sys.modules.\n\n    This function imports and returns a fresh copy of the named Python module\n    by removing the named module from sys.modules before doing the import.\n    Note that unlike reload, the original module is not affected by\n    this operation.\n\n    *fresh* is an iterable of additional module names that are also removed\n    from the sys.modules cache before doing the import.\n\n    *blocked* is an iterable of module names that are replaced with None\n    in the module cache during the import to ensure that attempts to import\n    them raise ImportError.\n\n    The named module and any modules named in the *fresh* and *blocked*\n    parameters are saved before starting the import and then reinserted into\n    sys.modules when the fresh import is complete.\n\n    Module and package deprecation messages are suppressed during this import\n    if *deprecated* is True.\n\n    This function will raise ImportError if the named module cannot be\n    imported.\n    "
    with _ignore_deprecated_imports(deprecated):
        orig_modules = {}
        names_to_remove = []
        _save_and_remove_module(name, orig_modules)
        try:
            for fresh_name in fresh:
                _save_and_remove_module(fresh_name, orig_modules)
            for blocked_name in blocked:
                if not _save_and_block_module(blocked_name, orig_modules):
                    names_to_remove.append(blocked_name)
            fresh_module = importlib.import_module(name)
        except ImportError:
            fresh_module = None
        finally:
            for (orig_name, module) in orig_modules.items():
                sys.modules[orig_name] = module
            for name_to_remove in names_to_remove:
                del sys.modules[name_to_remove]
        return fresh_module


class CleanImport(object):
    'Context manager to force import to return a new module reference.\n\n    This is useful for testing module-level behaviours, such as\n    the emission of a DeprecationWarning on import.\n\n    Use like this:\n\n        with CleanImport("foo"):\n            importlib.import_module("foo") # new reference\n    '

    def __init__(self, *module_names):
        self.original_modules = sys.modules.copy()
        for module_name in module_names:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                if module.__name__ != module_name:
                    del sys.modules[module.__name__]
                del sys.modules[module_name]

    def __enter__(self):
        return self

    def __exit__(self, *ignore_exc):
        sys.modules.update(self.original_modules)


class DirsOnSysPath(object):
    "Context manager to temporarily add directories to sys.path.\n\n    This makes a copy of sys.path, appends any directories given\n    as positional arguments, then reverts sys.path to the copied\n    settings when the context ends.\n\n    Note that *all* sys.path modifications in the body of the\n    context manager, including replacement of the object,\n    will be reverted at the end of the block.\n    "

    def __init__(self, *paths):
        self.original_value = sys.path[:]
        self.original_object = sys.path
        sys.path.extend(paths)

    def __enter__(self):
        return self

    def __exit__(self, *ignore_exc):
        sys.path = self.original_object
        sys.path[:] = self.original_value


def modules_setup():
    return (sys.modules.copy(),)


def modules_cleanup(oldmodules):
    encodings = [(k, v) for (k, v) in sys.modules.items() if k.startswith("encodings.")]
    sys.modules.clear()
    sys.modules.update(encodings)
    sys.modules.update(oldmodules)
