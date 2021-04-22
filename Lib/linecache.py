"Cache lines from Python source files.\n\nThis is intended to read lines from modules imported -- hence if a filename\nis not found, it will look down the module search path for a file by\nthat name.\n"
import functools
import sys
import os
import tokenize

__all__ = ["getline", "clearcache", "checkcache", "lazycache"]
cache = {}


def clearcache():
    "Clear the cache entirely."
    cache.clear()


def getline(filename, lineno, module_globals=None):
    "Get a line for a Python source file from the cache.\n    Update the cache if it doesn't contain an entry for this file already."
    lines = getlines(filename, module_globals)
    if 1 <= lineno <= len(lines):
        return lines[(lineno - 1)]
    return ""


def getlines(filename, module_globals=None):
    "Get the lines for a Python source file from the cache.\n    Update the cache if it doesn't contain an entry for this file already."
    if filename in cache:
        entry = cache[filename]
        if len(entry) != 1:
            return cache[filename][2]
    try:
        return updatecache(filename, module_globals)
    except MemoryError:
        clearcache()
        return []


def checkcache(filename=None):
    "Discard cache entries that are out of date.\n    (This is not checked upon each call!)"
    if filename is None:
        filenames = list(cache.keys())
    elif filename in cache:
        filenames = [filename]
    else:
        return
    for filename in filenames:
        entry = cache[filename]
        if len(entry) == 1:
            continue
        (size, mtime, lines, fullname) = entry
        if mtime is None:
            continue
        try:
            stat = os.stat(fullname)
        except OSError:
            cache.pop(filename, None)
            continue
        if (size != stat.st_size) or (mtime != stat.st_mtime):
            cache.pop(filename, None)


def updatecache(filename, module_globals=None):
    "Update a cache entry and return its list of lines.\n    If something's wrong, print a message, discard the cache entry,\n    and return an empty list."
    if filename in cache:
        if len(cache[filename]) != 1:
            cache.pop(filename, None)
    if (not filename) or (filename.startswith("<") and filename.endswith(">")):
        return []
    fullname = filename
    try:
        stat = os.stat(fullname)
    except OSError:
        basename = filename
        if lazycache(filename, module_globals):
            try:
                data = cache[filename][0]()
            except (ImportError, OSError):
                pass
            else:
                if data is None:
                    return []
                cache[filename] = (
                    len(data),
                    None,
                    [(line + "\n") for line in data.splitlines()],
                    fullname,
                )
                return cache[filename][2]
        if os.path.isabs(filename):
            return []
        for dirname in sys.path:
            try:
                fullname = os.path.join(dirname, basename)
            except (TypeError, AttributeError):
                continue
            try:
                stat = os.stat(fullname)
                break
            except OSError:
                pass
        else:
            return []
    try:
        with tokenize.open(fullname) as fp:
            lines = fp.readlines()
    except OSError:
        return []
    if lines and (not lines[(-1)].endswith("\n")):
        lines[(-1)] += "\n"
    (size, mtime) = (stat.st_size, stat.st_mtime)
    cache[filename] = (size, mtime, lines, fullname)
    return lines


def lazycache(filename, module_globals):
    "Seed the cache for filename with module_globals.\n\n    The module loader will be asked for the source only when getlines is\n    called, not immediately.\n\n    If there is an entry in the cache already, it is not altered.\n\n    :return: True if a lazy load is registered in the cache,\n        otherwise False. To register such a load a module loader with a\n        get_source method must be found, the filename must be a cachable\n        filename, and the filename must not be already cached.\n    "
    if filename in cache:
        if len(cache[filename]) == 1:
            return True
        else:
            return False
    if (not filename) or (filename.startswith("<") and filename.endswith(">")):
        return False
    if module_globals and ("__name__" in module_globals):
        name = module_globals["__name__"]
        if (loader := module_globals.get("__loader__")) is None:
            if (spec := module_globals.get("__spec__")) :
                try:
                    loader = spec.loader
                except AttributeError:
                    pass
        get_source = getattr(loader, "get_source", None)
        if name and get_source:
            get_lines = functools.partial(get_source, name)
            cache[filename] = (get_lines,)
            return True
    return False
