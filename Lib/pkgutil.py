"Utilities to support packages."
from collections import namedtuple
from functools import singledispatch as simplegeneric
import importlib
import importlib.util
import importlib.machinery
import os
import os.path
import sys
from types import ModuleType
import warnings

__all__ = [
    "get_importer",
    "iter_importers",
    "get_loader",
    "find_loader",
    "walk_packages",
    "iter_modules",
    "get_data",
    "ImpImporter",
    "ImpLoader",
    "read_code",
    "extend_path",
    "ModuleInfo",
]
ModuleInfo = namedtuple("ModuleInfo", "module_finder name ispkg")
ModuleInfo.__doc__ = "A namedtuple with minimal info about a module."


def _get_spec(finder, name):
    "Return the finder-specific module spec."
    try:
        find_spec = finder.find_spec
    except AttributeError:
        loader = finder.find_module(name)
        if loader is None:
            return None
        return importlib.util.spec_from_loader(name, loader)
    else:
        return find_spec(name)


def read_code(stream):
    import marshal

    magic = stream.read(4)
    if magic != importlib.util.MAGIC_NUMBER:
        return None
    stream.read(12)
    return marshal.load(stream)


def walk_packages(path=None, prefix="", onerror=None):
    "Yields ModuleInfo for all modules recursively\n    on path, or, if path is None, all accessible modules.\n\n    'path' should be either None or a list of paths to look for\n    modules in.\n\n    'prefix' is a string to output on the front of every module name\n    on output.\n\n    Note that this function must import all *packages* (NOT all\n    modules!) on the given path, in order to access the __path__\n    attribute to find submodules.\n\n    'onerror' is a function which gets called with one argument (the\n    name of the package which was being imported) if any exception\n    occurs while trying to import a package.  If no onerror function is\n    supplied, ImportErrors are caught and ignored, while all other\n    exceptions are propagated, terminating the search.\n\n    Examples:\n\n    # list all modules python can access\n    walk_packages()\n\n    # list all submodules of ctypes\n    walk_packages(ctypes.__path__, ctypes.__name__+'.')\n    "

    def seen(p, m={}):
        if p in m:
            return True
        m[p] = True

    for info in iter_modules(path, prefix):
        (yield info)
        if info.ispkg:
            try:
                __import__(info.name)
            except ImportError:
                if onerror is not None:
                    onerror(info.name)
            except Exception:
                if onerror is not None:
                    onerror(info.name)
                else:
                    raise
            else:
                path = getattr(sys.modules[info.name], "__path__", None) or []
                path = [p for p in path if (not seen(p))]
                (yield from walk_packages(path, (info.name + "."), onerror))


def iter_modules(path=None, prefix=""):
    "Yields ModuleInfo for all submodules on path,\n    or, if path is None, all top-level modules on sys.path.\n\n    'path' should be either None or a list of paths to look for\n    modules in.\n\n    'prefix' is a string to output on the front of every module name\n    on output.\n    "
    if path is None:
        importers = iter_importers()
    elif isinstance(path, str):
        raise ValueError("path must be None or list of paths to look for modules in")
    else:
        importers = map(get_importer, path)
    yielded = {}
    for i in importers:
        for (name, ispkg) in iter_importer_modules(i, prefix):
            if name not in yielded:
                yielded[name] = 1
                (yield ModuleInfo(i, name, ispkg))


@simplegeneric
def iter_importer_modules(importer, prefix=""):
    if not hasattr(importer, "iter_modules"):
        return []
    return importer.iter_modules(prefix)


def _iter_file_finder_modules(importer, prefix=""):
    if (importer.path is None) or (not os.path.isdir(importer.path)):
        return
    yielded = {}
    import inspect

    try:
        filenames = os.listdir(importer.path)
    except OSError:
        filenames = []
    filenames.sort()
    for fn in filenames:
        modname = inspect.getmodulename(fn)
        if (modname == "__init__") or (modname in yielded):
            continue
        path = os.path.join(importer.path, fn)
        ispkg = False
        if (not modname) and os.path.isdir(path) and ("." not in fn):
            modname = fn
            try:
                dircontents = os.listdir(path)
            except OSError:
                dircontents = []
            for fn in dircontents:
                subname = inspect.getmodulename(fn)
                if subname == "__init__":
                    ispkg = True
                    break
            else:
                continue
        if modname and ("." not in modname):
            yielded[modname] = 1
            (yield ((prefix + modname), ispkg))


iter_importer_modules.register(
    importlib.machinery.FileFinder, _iter_file_finder_modules
)


def _import_imp():
    global imp
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        imp = importlib.import_module("imp")


class ImpImporter:
    'PEP 302 Finder that wraps Python\'s "classic" import algorithm\n\n    ImpImporter(dirname) produces a PEP 302 finder that searches that\n    directory.  ImpImporter(None) produces a PEP 302 finder that searches\n    the current sys.path, plus any modules that are frozen or built-in.\n\n    Note that ImpImporter does not currently support being used by placement\n    on sys.meta_path.\n    '

    def __init__(self, path=None):
        global imp
        warnings.warn(
            "This emulation is deprecated and slated for removal in Python 3.12; use 'importlib' instead",
            DeprecationWarning,
        )
        _import_imp()
        self.path = path

    def find_module(self, fullname, path=None):
        subname = fullname.split(".")[(-1)]
        if (subname != fullname) and (self.path is None):
            return None
        if self.path is None:
            path = None
        else:
            path = [os.path.realpath(self.path)]
        try:
            (file, filename, etc) = imp.find_module(subname, path)
        except ImportError:
            return None
        return ImpLoader(fullname, file, filename, etc)

    def iter_modules(self, prefix=""):
        if (self.path is None) or (not os.path.isdir(self.path)):
            return
        yielded = {}
        import inspect

        try:
            filenames = os.listdir(self.path)
        except OSError:
            filenames = []
        filenames.sort()
        for fn in filenames:
            modname = inspect.getmodulename(fn)
            if (modname == "__init__") or (modname in yielded):
                continue
            path = os.path.join(self.path, fn)
            ispkg = False
            if (not modname) and os.path.isdir(path) and ("." not in fn):
                modname = fn
                try:
                    dircontents = os.listdir(path)
                except OSError:
                    dircontents = []
                for fn in dircontents:
                    subname = inspect.getmodulename(fn)
                    if subname == "__init__":
                        ispkg = True
                        break
                else:
                    continue
            if modname and ("." not in modname):
                yielded[modname] = 1
                (yield ((prefix + modname), ispkg))


class ImpLoader:
    'PEP 302 Loader that wraps Python\'s "classic" import algorithm\n    '
    code = source = None

    def __init__(self, fullname, file, filename, etc):
        warnings.warn(
            "This emulation is deprecated and slated for removal in Python 3.12; use 'importlib' instead",
            DeprecationWarning,
        )
        _import_imp()
        self.file = file
        self.filename = filename
        self.fullname = fullname
        self.etc = etc

    def load_module(self, fullname):
        self._reopen()
        try:
            mod = imp.load_module(fullname, self.file, self.filename, self.etc)
        finally:
            if self.file:
                self.file.close()
        return mod

    def get_data(self, pathname):
        with open(pathname, "rb") as file:
            return file.read()

    def _reopen(self):
        if self.file and self.file.closed:
            mod_type = self.etc[2]
            if mod_type == imp.PY_SOURCE:
                self.file = open(self.filename, "r")
            elif mod_type in (imp.PY_COMPILED, imp.C_EXTENSION):
                self.file = open(self.filename, "rb")

    def _fix_name(self, fullname):
        if fullname is None:
            fullname = self.fullname
        elif fullname != self.fullname:
            raise ImportError(
                (
                    "Loader for module %s cannot handle module %s"
                    % (self.fullname, fullname)
                )
            )
        return fullname

    def is_package(self, fullname):
        fullname = self._fix_name(fullname)
        return self.etc[2] == imp.PKG_DIRECTORY

    def get_code(self, fullname=None):
        fullname = self._fix_name(fullname)
        if self.code is None:
            mod_type = self.etc[2]
            if mod_type == imp.PY_SOURCE:
                source = self.get_source(fullname)
                self.code = compile(source, self.filename, "exec")
            elif mod_type == imp.PY_COMPILED:
                self._reopen()
                try:
                    self.code = read_code(self.file)
                finally:
                    self.file.close()
            elif mod_type == imp.PKG_DIRECTORY:
                self.code = self._get_delegate().get_code()
        return self.code

    def get_source(self, fullname=None):
        fullname = self._fix_name(fullname)
        if self.source is None:
            mod_type = self.etc[2]
            if mod_type == imp.PY_SOURCE:
                self._reopen()
                try:
                    self.source = self.file.read()
                finally:
                    self.file.close()
            elif mod_type == imp.PY_COMPILED:
                if os.path.exists(self.filename[:(-1)]):
                    with open(self.filename[:(-1)], "r") as f:
                        self.source = f.read()
            elif mod_type == imp.PKG_DIRECTORY:
                self.source = self._get_delegate().get_source()
        return self.source

    def _get_delegate(self):
        finder = ImpImporter(self.filename)
        spec = _get_spec(finder, "__init__")
        return spec.loader

    def get_filename(self, fullname=None):
        fullname = self._fix_name(fullname)
        mod_type = self.etc[2]
        if mod_type == imp.PKG_DIRECTORY:
            return self._get_delegate().get_filename()
        elif mod_type in (imp.PY_SOURCE, imp.PY_COMPILED, imp.C_EXTENSION):
            return self.filename
        return None


try:
    import zipimport
    from zipimport import zipimporter

    def iter_zipimport_modules(importer, prefix=""):
        dirlist = sorted(zipimport._zip_directory_cache[importer.archive])
        _prefix = importer.prefix
        plen = len(_prefix)
        yielded = {}
        import inspect

        for fn in dirlist:
            if not fn.startswith(_prefix):
                continue
            fn = fn[plen:].split(os.sep)
            if (len(fn) == 2) and fn[1].startswith("__init__.py"):
                if fn[0] not in yielded:
                    yielded[fn[0]] = 1
                    (yield ((prefix + fn[0]), True))
            if len(fn) != 1:
                continue
            modname = inspect.getmodulename(fn[0])
            if modname == "__init__":
                continue
            if modname and ("." not in modname) and (modname not in yielded):
                yielded[modname] = 1
                (yield ((prefix + modname), False))

    iter_importer_modules.register(zipimporter, iter_zipimport_modules)
except ImportError:
    pass


def get_importer(path_item):
    "Retrieve a finder for the given path item\n\n    The returned finder is cached in sys.path_importer_cache\n    if it was newly created by a path hook.\n\n    The cache (or part of it) can be cleared manually if a\n    rescan of sys.path_hooks is necessary.\n    "
    try:
        importer = sys.path_importer_cache[path_item]
    except KeyError:
        for path_hook in sys.path_hooks:
            try:
                importer = path_hook(path_item)
                sys.path_importer_cache.setdefault(path_item, importer)
                break
            except ImportError:
                pass
        else:
            importer = None
    return importer


def iter_importers(fullname=""):
    "Yield finders for the given module name\n\n    If fullname contains a '.', the finders will be for the package\n    containing fullname, otherwise they will be all registered top level\n    finders (i.e. those on both sys.meta_path and sys.path_hooks).\n\n    If the named module is in a package, that package is imported as a side\n    effect of invoking this function.\n\n    If no module name is specified, all top level finders are produced.\n    "
    if fullname.startswith("."):
        msg = "Relative module name {!r} not supported".format(fullname)
        raise ImportError(msg)
    if "." in fullname:
        pkg_name = fullname.rpartition(".")[0]
        pkg = importlib.import_module(pkg_name)
        path = getattr(pkg, "__path__", None)
        if path is None:
            return
    else:
        (yield from sys.meta_path)
        path = sys.path
    for item in path:
        (yield get_importer(item))


def get_loader(module_or_name):
    'Get a "loader" object for module_or_name\n\n    Returns None if the module cannot be found or imported.\n    If the named module is not already imported, its containing package\n    (if any) is imported, in order to establish the package __path__.\n    '
    if module_or_name in sys.modules:
        module_or_name = sys.modules[module_or_name]
        if module_or_name is None:
            return None
    if isinstance(module_or_name, ModuleType):
        module = module_or_name
        loader = getattr(module, "__loader__", None)
        if loader is not None:
            return loader
        if getattr(module, "__spec__", None) is None:
            return None
        fullname = module.__name__
    else:
        fullname = module_or_name
    return find_loader(fullname)


def find_loader(fullname):
    'Find a "loader" object for fullname\n\n    This is a backwards compatibility wrapper around\n    importlib.util.find_spec that converts most failures to ImportError\n    and only returns the loader rather than the full spec\n    '
    if fullname.startswith("."):
        msg = "Relative module name {!r} not supported".format(fullname)
        raise ImportError(msg)
    try:
        spec = importlib.util.find_spec(fullname)
    except (ImportError, AttributeError, TypeError, ValueError) as ex:
        msg = "Error while finding loader for {!r} ({}: {})"
        raise ImportError(msg.format(fullname, type(ex), ex)) from ex
    return spec.loader if (spec is not None) else None


def extend_path(path, name):
    "Extend a package's path.\n\n    Intended use is to place the following code in a package's __init__.py:\n\n        from pkgutil import extend_path\n        __path__ = extend_path(__path__, __name__)\n\n    This will add to the package's __path__ all subdirectories of\n    directories on sys.path named after the package.  This is useful\n    if one wants to distribute different parts of a single logical\n    package as multiple directories.\n\n    It also looks for *.pkg files beginning where * matches the name\n    argument.  This feature is similar to *.pth files (see site.py),\n    except that it doesn't special-case lines starting with 'import'.\n    A *.pkg file is trusted at face value: apart from checking for\n    duplicates, all entries found in a *.pkg file are added to the\n    path, regardless of whether they are exist the filesystem.  (This\n    is a feature.)\n\n    If the input path is not a list (as is the case for frozen\n    packages) it is returned unchanged.  The input path is not\n    modified; an extended copy is returned.  Items are only appended\n    to the copy at the end.\n\n    It is assumed that sys.path is a sequence.  Items of sys.path that\n    are not (unicode or 8-bit) strings referring to existing\n    directories are ignored.  Unicode items of sys.path that cause\n    errors when used as filenames may cause this function to raise an\n    exception (in line with os.path.isdir() behavior).\n    "
    if not isinstance(path, list):
        return path
    sname_pkg = name + ".pkg"
    path = path[:]
    (parent_package, _, final_name) = name.rpartition(".")
    if parent_package:
        try:
            search_path = sys.modules[parent_package].__path__
        except (KeyError, AttributeError):
            return path
    else:
        search_path = sys.path
    for dir in search_path:
        if not isinstance(dir, str):
            continue
        finder = get_importer(dir)
        if finder is not None:
            portions = []
            if hasattr(finder, "find_spec"):
                spec = finder.find_spec(final_name)
                if spec is not None:
                    portions = spec.submodule_search_locations or []
            elif hasattr(finder, "find_loader"):
                (_, portions) = finder.find_loader(final_name)
            for portion in portions:
                if portion not in path:
                    path.append(portion)
        pkgfile = os.path.join(dir, sname_pkg)
        if os.path.isfile(pkgfile):
            try:
                f = open(pkgfile)
            except OSError as msg:
                sys.stderr.write(("Can't open %s: %s\n" % (pkgfile, msg)))
            else:
                with f:
                    for line in f:
                        line = line.rstrip("\n")
                        if (not line) or line.startswith("#"):
                            continue
                        path.append(line)
    return path


def get_data(package, resource):
    "Get a resource from a package.\n\n    This is a wrapper round the PEP 302 loader get_data API. The package\n    argument should be the name of a package, in standard module format\n    (foo.bar). The resource argument should be in the form of a relative\n    filename, using '/' as the path separator. The parent directory name '..'\n    is not allowed, and nor is a rooted name (starting with a '/').\n\n    The function returns a binary string, which is the contents of the\n    specified resource.\n\n    For packages located in the filesystem, which have already been imported,\n    this is the rough equivalent of\n\n        d = os.path.dirname(sys.modules[package].__file__)\n        data = open(os.path.join(d, resource), 'rb').read()\n\n    If the package cannot be located or loaded, or it uses a PEP 302 loader\n    which does not support get_data(), then None is returned.\n    "
    spec = importlib.util.find_spec(package)
    if spec is None:
        return None
    loader = spec.loader
    if (loader is None) or (not hasattr(loader, "get_data")):
        return None
    mod = sys.modules.get(package) or importlib._bootstrap._load(spec)
    if (mod is None) or (not hasattr(mod, "__file__")):
        return None
    parts = resource.split("/")
    parts.insert(0, os.path.dirname(mod.__file__))
    resource_name = os.path.join(*parts)
    return loader.get_data(resource_name)


_NAME_PATTERN = None


def resolve_name(name):
    "\n    Resolve a name to an object.\n\n    It is expected that `name` will be a string in one of the following\n    formats, where W is shorthand for a valid Python identifier and dot stands\n    for a literal period in these pseudo-regexes:\n\n    W(.W)*\n    W(.W)*:(W(.W)*)?\n\n    The first form is intended for backward compatibility only. It assumes that\n    some part of the dotted name is a package, and the rest is an object\n    somewhere within that package, possibly nested inside other objects.\n    Because the place where the package stops and the object hierarchy starts\n    can't be inferred by inspection, repeated attempts to import must be done\n    with this form.\n\n    In the second form, the caller makes the division point clear through the\n    provision of a single colon: the dotted name to the left of the colon is a\n    package to be imported, and the dotted name to the right is the object\n    hierarchy within that package. Only one import is needed in this form. If\n    it ends with the colon, then a module object is returned.\n\n    The function will return an object (which might be a module), or raise one\n    of the following exceptions:\n\n    ValueError - if `name` isn't in a recognised format\n    ImportError - if an import failed when it shouldn't have\n    AttributeError - if a failure occurred when traversing the object hierarchy\n                     within the imported package to get to the desired object)\n    "
    global _NAME_PATTERN
    if _NAME_PATTERN is None:
        import re

        dotted_words = "(?!\\d)(\\w+)(\\.(?!\\d)(\\w+))*"
        _NAME_PATTERN = re.compile(
            f"^(?P<pkg>{dotted_words})(?P<cln>:(?P<obj>{dotted_words})?)?$", re.UNICODE
        )
    m = _NAME_PATTERN.match(name)
    if not m:
        raise ValueError(f"invalid format: {name!r}")
    gd = m.groupdict()
    if gd.get("cln"):
        mod = importlib.import_module(gd["pkg"])
        parts = gd.get("obj")
        parts = parts.split(".") if parts else []
    else:
        parts = name.split(".")
        modname = parts.pop(0)
        mod = importlib.import_module(modname)
        while parts:
            p = parts[0]
            s = f"{modname}.{p}"
            try:
                mod = importlib.import_module(s)
                parts.pop(0)
                modname = s
            except ImportError:
                break
    result = mod
    for p in parts:
        result = getattr(result, p)
    return result
