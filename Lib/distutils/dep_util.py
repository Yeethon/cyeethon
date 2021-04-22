"distutils.dep_util\n\nUtility functions for simple, timestamp-based dependency of files\nand groups of files; also, function based entirely on such\ntimestamp dependency analysis."
import os
from distutils.errors import DistutilsFileError


def newer(source, target):
    "Return true if 'source' exists and is more recently modified than\n    'target', or if 'source' exists and 'target' doesn't.  Return false if\n    both exist and 'target' is the same age or younger than 'source'.\n    Raise DistutilsFileError if 'source' does not exist.\n    "
    if not os.path.exists(source):
        raise DistutilsFileError(("file '%s' does not exist" % os.path.abspath(source)))
    if not os.path.exists(target):
        return 1
    from stat import ST_MTIME

    mtime1 = os.stat(source)[ST_MTIME]
    mtime2 = os.stat(target)[ST_MTIME]
    return mtime1 > mtime2


def newer_pairwise(sources, targets):
    "Walk two filename lists in parallel, testing if each source is newer\n    than its corresponding target.  Return a pair of lists (sources,\n    targets) where source is newer than target, according to the semantics\n    of 'newer()'.\n    "
    if len(sources) != len(targets):
        raise ValueError("'sources' and 'targets' must be same length")
    n_sources = []
    n_targets = []
    for i in range(len(sources)):
        if newer(sources[i], targets[i]):
            n_sources.append(sources[i])
            n_targets.append(targets[i])
    return (n_sources, n_targets)


def newer_group(sources, target, missing="error"):
    "Return true if 'target' is out-of-date with respect to any file\n    listed in 'sources'.  In other words, if 'target' exists and is newer\n    than every file in 'sources', return false; otherwise return true.\n    'missing' controls what we do when a source file is missing; the\n    default (\"error\") is to blow up with an OSError from inside 'stat()';\n    if it is \"ignore\", we silently drop any missing source files; if it is\n    \"newer\", any missing source files make us assume that 'target' is\n    out-of-date (this is handy in \"dry-run\" mode: it'll make you pretend to\n    carry out commands that wouldn't work because inputs are missing, but\n    that doesn't matter because you're not actually going to run the\n    commands).\n    "
    if not os.path.exists(target):
        return 1
    from stat import ST_MTIME

    target_mtime = os.stat(target)[ST_MTIME]
    for source in sources:
        if not os.path.exists(source):
            if missing == "error":
                pass
            elif missing == "ignore":
                continue
            elif missing == "newer":
                return 1
        source_mtime = os.stat(source)[ST_MTIME]
        if source_mtime > target_mtime:
            return 1
    else:
        return 0
