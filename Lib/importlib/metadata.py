import os
import re
import abc
import csv
import sys
import email
import pathlib
import zipfile
import operator
import warnings
import functools
import itertools
import posixpath
import collections
from ._itertools import unique_everseen
from configparser import ConfigParser
from contextlib import suppress
from importlib import import_module
from importlib.abc import MetaPathFinder
from itertools import starmap
from typing import Any, List, Mapping, Optional, Protocol, TypeVar, Union

__all__ = [
    "Distribution",
    "DistributionFinder",
    "PackageNotFoundError",
    "distribution",
    "distributions",
    "entry_points",
    "files",
    "metadata",
    "packages_distributions",
    "requires",
    "version",
]


class PackageNotFoundError(ModuleNotFoundError):
    "The package was not found."

    def __str__(self):
        tmpl = "No package metadata was found for {self.name}"
        return tmpl.format(**locals())

    @property
    def name(self):
        (name,) = self.args
        return name


class EntryPoint(collections.namedtuple("EntryPointBase", "name value group")):
    "An entry point as defined by Python packaging conventions.\n\n    See `the packaging docs on entry points\n    <https://packaging.python.org/specifications/entry-points/>`_\n    for more information.\n    "
    pattern = re.compile(
        "(?P<module>[\\w.]+)\\s*(:\\s*(?P<attr>[\\w.]+))?\\s*(?P<extras>\\[.*\\])?\\s*$"
    )
    "\n    A regular expression describing the syntax for an entry point,\n    which might look like:\n\n        - module\n        - package.module\n        - package.module:attribute\n        - package.module:object.attribute\n        - package.module:attr [extra1, extra2]\n\n    Other combinations are possible as well.\n\n    The expression is lenient about whitespace around the ':',\n    following the attr, and following any extras.\n    "
    dist: Optional["Distribution"] = None

    def load(self):
        "Load the entry point from its definition. If only a module\n        is indicated by the value, return that module. Otherwise,\n        return the named object.\n        "
        match = self.pattern.match(self.value)
        module = import_module(match.group("module"))
        attrs = filter(None, (match.group("attr") or "").split("."))
        return functools.reduce(getattr, attrs, module)

    @property
    def module(self):
        match = self.pattern.match(self.value)
        return match.group("module")

    @property
    def attr(self):
        match = self.pattern.match(self.value)
        return match.group("attr")

    @property
    def extras(self):
        match = self.pattern.match(self.value)
        return list(re.finditer("\\w+", (match.group("extras") or "")))

    @classmethod
    def _from_config(cls, config):
        return (
            cls(name, value, group)
            for group in config.sections()
            for (name, value) in config.items(group)
        )

    @classmethod
    def _from_text(cls, text):
        config = ConfigParser(delimiters="=")
        config.optionxform = str
        config.read_string(text)
        return cls._from_config(config)

    def _for(self, dist):
        self.dist = dist
        return self

    def __iter__(self):
        "\n        Supply iter so one may construct dicts of EntryPoints by name.\n        "
        msg = (
            "Construction of dict of EntryPoints is deprecated in favor of EntryPoints."
        )
        warnings.warn(msg, DeprecationWarning)
        return iter((self.name, self))

    def __reduce__(self):
        return (self.__class__, (self.name, self.value, self.group))

    def matches(self, **params):
        attrs = (getattr(self, param) for param in params)
        return all(map(operator.eq, params.values(), attrs))


class EntryPoints(tuple):
    "\n    An immutable collection of selectable EntryPoint objects.\n    "
    __slots__ = ()

    def __getitem__(self, name):
        "\n        Get the EntryPoint in self matching name.\n        "
        try:
            return next(iter(self.select(name=name)))
        except StopIteration:
            raise KeyError(name)

    def select(self, **params):
        "\n        Select entry points from self that match the\n        given parameters (typically group and/or name).\n        "
        return EntryPoints((ep for ep in self if ep.matches(**params)))

    @property
    def names(self):
        "\n        Return the set of all names of all entry points.\n        "
        return set((ep.name for ep in self))

    @property
    def groups(self):
        "\n        Return the set of all groups of all entry points.\n\n        For coverage while SelectableGroups is present.\n        >>> EntryPoints().groups\n        set()\n        "
        return set((ep.group for ep in self))

    @classmethod
    def _from_text_for(cls, text, dist):
        return cls((ep._for(dist) for ep in EntryPoint._from_text(text)))


def flake8_bypass(func):
    import inspect

    is_flake8 = any(
        (("flake8" in str(frame.filename)) for frame in inspect.stack()[:5])
    )
    return func if (not is_flake8) else (lambda: None)


class Deprecated:
    "\n    Compatibility add-in for mapping to indicate that\n    mapping behavior is deprecated.\n\n    >>> recwarn = getfixture('recwarn')\n    >>> class DeprecatedDict(Deprecated, dict): pass\n    >>> dd = DeprecatedDict(foo='bar')\n    >>> dd.get('baz', None)\n    >>> dd['foo']\n    'bar'\n    >>> list(dd)\n    ['foo']\n    >>> list(dd.keys())\n    ['foo']\n    >>> 'foo' in dd\n    True\n    >>> list(dd.values())\n    ['bar']\n    >>> len(recwarn)\n    1\n    "
    _warn = functools.partial(
        warnings.warn,
        "SelectableGroups dict interface is deprecated. Use select.",
        DeprecationWarning,
        stacklevel=2,
    )

    def __getitem__(self, name):
        self._warn()
        return super().__getitem__(name)

    def get(self, name, default=None):
        flake8_bypass(self._warn)()
        return super().get(name, default)

    def __iter__(self):
        self._warn()
        return super().__iter__()

    def __contains__(self, *args):
        self._warn()
        return super().__contains__(*args)

    def keys(self):
        self._warn()
        return super().keys()

    def values(self):
        self._warn()
        return super().values()


class SelectableGroups(dict):
    "\n    A backward- and forward-compatible result from\n    entry_points that fully implements the dict interface.\n    "

    @classmethod
    def load(cls, eps):
        by_group = operator.attrgetter("group")
        ordered = sorted(eps, key=by_group)
        grouped = itertools.groupby(ordered, by_group)
        return cls(((group, EntryPoints(eps)) for (group, eps) in grouped))

    @property
    def _all(self):
        "\n        Reconstruct a list of all entrypoints from the groups.\n        "
        return EntryPoints(itertools.chain.from_iterable(self.values()))

    @property
    def groups(self):
        return self._all.groups

    @property
    def names(self):
        "\n        for coverage:\n        >>> SelectableGroups().names\n        set()\n        "
        return self._all.names

    def select(self, **params):
        if not params:
            return self
        return self._all.select(**params)


class PackagePath(pathlib.PurePosixPath):
    "A reference to a path in a package"

    def read_text(self, encoding="utf-8"):
        with self.locate().open(encoding=encoding) as stream:
            return stream.read()

    def read_binary(self):
        with self.locate().open("rb") as stream:
            return stream.read()

    def locate(self):
        "Return a path-like object for this path"
        return self.dist.locate_file(self)


class FileHash:
    def __init__(self, spec):
        (self.mode, _, self.value) = spec.partition("=")

    def __repr__(self):
        return "<FileHash mode: {} value: {}>".format(self.mode, self.value)


_T = TypeVar("_T")


class PackageMetadata(Protocol):
    def __len__(self) -> int:
        ...

    def __contains__(self, item: str) -> bool:
        ...

    def __getitem__(self, key: str) -> str:
        ...

    def get_all(self, name: str, failobj: _T = ...) -> Union[(List[Any], _T)]:
        "\n        Return all values associated with a possibly multi-valued key.\n        "


class Distribution:
    "A Python distribution package."

    @abc.abstractmethod
    def read_text(self, filename):
        "Attempt to load metadata file given by the name.\n\n        :param filename: The name of the file in the distribution info.\n        :return: The text if found, otherwise None.\n        "

    @abc.abstractmethod
    def locate_file(self, path):
        "\n        Given a path to a file in this distribution, return a path\n        to it.\n        "

    @classmethod
    def from_name(cls, name):
        "Return the Distribution for the given package name.\n\n        :param name: The name of the distribution package to search for.\n        :return: The Distribution instance (or subclass thereof) for the named\n            package, if found.\n        :raises PackageNotFoundError: When the named package's distribution\n            metadata cannot be found.\n        "
        for resolver in cls._discover_resolvers():
            dists = resolver(DistributionFinder.Context(name=name))
            dist = next(iter(dists), None)
            if dist is not None:
                return dist
        else:
            raise PackageNotFoundError(name)

    @classmethod
    def discover(cls, **kwargs):
        "Return an iterable of Distribution objects for all packages.\n\n        Pass a ``context`` or pass keyword arguments for constructing\n        a context.\n\n        :context: A ``DistributionFinder.Context`` object.\n        :return: Iterable of Distribution objects for all packages.\n        "
        context = kwargs.pop("context", None)
        if context and kwargs:
            raise ValueError("cannot accept context and kwargs")
        context = context or DistributionFinder.Context(**kwargs)
        return itertools.chain.from_iterable(
            (resolver(context) for resolver in cls._discover_resolvers())
        )

    @staticmethod
    def at(path):
        "Return a Distribution for the indicated metadata path\n\n        :param path: a string or path-like object\n        :return: a concrete Distribution instance for the path\n        "
        return PathDistribution(pathlib.Path(path))

    @staticmethod
    def _discover_resolvers():
        "Search the meta_path for resolvers."
        declared = (
            getattr(finder, "find_distributions", None) for finder in sys.meta_path
        )
        return filter(None, declared)

    @classmethod
    def _local(cls, root="."):
        from pep517 import build, meta

        system = build.compat_system(root)
        builder = functools.partial(meta.build, source_dir=root, system=system)
        return PathDistribution(zipfile.Path(meta.build_as_zip(builder)))

    @property
    def metadata(self) -> PackageMetadata:
        "Return the parsed metadata for this Distribution.\n\n        The returned object will have keys that name the various bits of\n        metadata.  See PEP 566 for details.\n        "
        text = (
            self.read_text("METADATA")
            or self.read_text("PKG-INFO")
            or self.read_text("")
        )
        return email.message_from_string(text)

    @property
    def name(self):
        "Return the 'Name' metadata for the distribution package."
        return self.metadata["Name"]

    @property
    def version(self):
        "Return the 'Version' metadata for the distribution package."
        return self.metadata["Version"]

    @property
    def entry_points(self):
        return EntryPoints._from_text_for(self.read_text("entry_points.txt"), self)

    @property
    def files(self):
        "Files in this distribution.\n\n        :return: List of PackagePath for this distribution or None\n\n        Result is `None` if the metadata file that enumerates files\n        (i.e. RECORD for dist-info or SOURCES.txt for egg-info) is\n        missing.\n        Result may be empty if the metadata exists but is empty.\n        "
        file_lines = self._read_files_distinfo() or self._read_files_egginfo()

        def make_file(name, hash=None, size_str=None):
            result = PackagePath(name)
            result.hash = FileHash(hash) if hash else None
            result.size = int(size_str) if size_str else None
            result.dist = self
            return result

        return file_lines and list(starmap(make_file, csv.reader(file_lines)))

    def _read_files_distinfo(self):
        "\n        Read the lines of RECORD\n        "
        text = self.read_text("RECORD")
        return text and text.splitlines()

    def _read_files_egginfo(self):
        "\n        SOURCES.txt might contain literal commas, so wrap each line\n        in quotes.\n        "
        text = self.read_text("SOURCES.txt")
        return text and map('"{}"'.format, text.splitlines())

    @property
    def requires(self):
        "Generated requirements specified for this Distribution"
        reqs = self._read_dist_info_reqs() or self._read_egg_info_reqs()
        return reqs and list(reqs)

    def _read_dist_info_reqs(self):
        return self.metadata.get_all("Requires-Dist")

    def _read_egg_info_reqs(self):
        source = self.read_text("requires.txt")
        return source and self._deps_from_requires_text(source)

    @classmethod
    def _deps_from_requires_text(cls, source):
        section_pairs = cls._read_sections(source.splitlines())
        sections = {
            section: list(map(operator.itemgetter("line"), results))
            for (section, results) in itertools.groupby(
                section_pairs, operator.itemgetter("section")
            )
        }
        return cls._convert_egg_info_reqs_to_simple_reqs(sections)

    @staticmethod
    def _read_sections(lines):
        section = None
        for line in filter(None, lines):
            section_match = re.match("\\[(.*)\\]$", line)
            if section_match:
                section = section_match.group(1)
                continue
            (yield locals())

    @staticmethod
    def _convert_egg_info_reqs_to_simple_reqs(sections):
        "\n        Historically, setuptools would solicit and store 'extra'\n        requirements, including those with environment markers,\n        in separate sections. More modern tools expect each\n        dependency to be defined separately, with any relevant\n        extras and environment markers attached directly to that\n        requirement. This method converts the former to the\n        latter. See _test_deps_from_requires_text for an example.\n        "

        def make_condition(name):
            return name and 'extra == "{name}"'.format(name=name)

        def parse_condition(section):
            section = section or ""
            (extra, sep, markers) = section.partition(":")
            if extra and markers:
                markers = "({markers})".format(markers=markers)
            conditions = list(filter(None, [markers, make_condition(extra)]))
            return ("; " + " and ".join(conditions)) if conditions else ""

        for (section, deps) in sections.items():
            for dep in deps:
                (yield (dep + parse_condition(section)))


class DistributionFinder(MetaPathFinder):
    "\n    A MetaPathFinder capable of discovering installed distributions.\n    "

    class Context:
        "\n        Keyword arguments presented by the caller to\n        ``distributions()`` or ``Distribution.discover()``\n        to narrow the scope of a search for distributions\n        in all DistributionFinders.\n\n        Each DistributionFinder may expect any parameters\n        and should attempt to honor the canonical\n        parameters defined below when appropriate.\n        "
        name = None
        "\n        Specific name for which a distribution finder should match.\n        A name of ``None`` matches all distributions.\n        "

        def __init__(self, **kwargs):
            vars(self).update(kwargs)

        @property
        def path(self):
            "\n            The path that a distribution finder should search.\n\n            Typically refers to Python package paths and defaults\n            to ``sys.path``.\n            "
            return vars(self).get("path", sys.path)

    @abc.abstractmethod
    def find_distributions(self, context=Context()):
        "\n        Find distributions.\n\n        Return an iterable of all Distribution instances capable of\n        loading the metadata for packages matching the ``context``,\n        a DistributionFinder.Context instance.\n        "


class FastPath:
    "\n    Micro-optimized class for searching a path for\n    children.\n    "

    def __init__(self, root):
        self.root = root
        self.base = os.path.basename(self.root).lower()

    def joinpath(self, child):
        return pathlib.Path(self.root, child)

    def children(self):
        with suppress(Exception):
            return os.listdir((self.root or ""))
        with suppress(Exception):
            return self.zip_children()
        return []

    def zip_children(self):
        zip_path = zipfile.Path(self.root)
        names = zip_path.root.namelist()
        self.joinpath = zip_path.joinpath
        return dict.fromkeys((child.split(posixpath.sep, 1)[0] for child in names))

    def search(self, name):
        return (
            self.joinpath(child)
            for child in self.children()
            if name.matches(child, self.base)
        )


class Prepared:
    "\n    A prepared search for metadata on a possibly-named package.\n    "
    normalized = None
    suffixes = ("dist-info", "egg-info")
    exact_matches = [""][:0]
    egg_prefix = ""
    versionless_egg_name = ""

    def __init__(self, name):
        self.name = name
        if name is None:
            return
        self.normalized = self.normalize(name)
        self.exact_matches = [
            ((self.normalized + ".") + suffix) for suffix in self.suffixes
        ]
        legacy_normalized = self.legacy_normalize(self.name)
        self.egg_prefix = legacy_normalized + "-"
        self.versionless_egg_name = legacy_normalized + ".egg"

    @staticmethod
    def normalize(name):
        "\n        PEP 503 normalization plus dashes as underscores.\n        "
        return re.sub("[-_.]+", "-", name).lower().replace("-", "_")

    @staticmethod
    def legacy_normalize(name):
        "\n        Normalize the package name as found in the convention in\n        older packaging tools versions and specs.\n        "
        return name.lower().replace("-", "_")

    def matches(self, cand, base):
        low = cand.lower()
        (pre, _, ext) = low.rpartition(".")
        (name, _, rest) = pre.partition("-")
        return (
            (low in self.exact_matches)
            or (
                (ext in self.suffixes)
                and (
                    (not self.normalized) or (name.replace(".", "_") == self.normalized)
                )
            )
            or (self.is_egg(base) and (low == "egg-info"))
        )

    def is_egg(self, base):
        return (base == self.versionless_egg_name) or (
            base.startswith(self.egg_prefix) and base.endswith(".egg")
        )


class MetadataPathFinder(DistributionFinder):
    @classmethod
    def find_distributions(cls, context=DistributionFinder.Context()):
        "\n        Find distributions.\n\n        Return an iterable of all Distribution instances capable of\n        loading the metadata for packages matching ``context.name``\n        (or all names if ``None`` indicated) along the paths in the list\n        of directories ``context.path``.\n        "
        found = cls._search_paths(context.name, context.path)
        return map(PathDistribution, found)

    @classmethod
    def _search_paths(cls, name, paths):
        "Find metadata directories in paths heuristically."
        prepared = Prepared(name)
        return itertools.chain.from_iterable(
            (path.search(prepared) for path in map(FastPath, paths))
        )


class PathDistribution(Distribution):
    def __init__(self, path):
        "Construct a distribution from a path to the metadata directory.\n\n        :param path: A pathlib.Path or similar object supporting\n                     .joinpath(), __div__, .parent, and .read_text().\n        "
        self._path = path

    def read_text(self, filename):
        with suppress(
            FileNotFoundError,
            IsADirectoryError,
            KeyError,
            NotADirectoryError,
            PermissionError,
        ):
            return self._path.joinpath(filename).read_text(encoding="utf-8")

    read_text.__doc__ = Distribution.read_text.__doc__

    def locate_file(self, path):
        return self._path.parent / path


def distribution(distribution_name):
    "Get the ``Distribution`` instance for the named package.\n\n    :param distribution_name: The name of the distribution package as a string.\n    :return: A ``Distribution`` instance (or subclass thereof).\n    "
    return Distribution.from_name(distribution_name)


def distributions(**kwargs):
    "Get all ``Distribution`` instances in the current environment.\n\n    :return: An iterable of ``Distribution`` instances.\n    "
    return Distribution.discover(**kwargs)


def metadata(distribution_name) -> PackageMetadata:
    "Get the metadata for the named package.\n\n    :param distribution_name: The name of the distribution package to query.\n    :return: A PackageMetadata containing the parsed metadata.\n    "
    return Distribution.from_name(distribution_name).metadata


def version(distribution_name):
    'Get the version string for the named package.\n\n    :param distribution_name: The name of the distribution package to query.\n    :return: The version string for the package as defined in the package\'s\n        "Version" metadata key.\n    '
    return distribution(distribution_name).version


def entry_points(**params) -> Union[(EntryPoints, SelectableGroups)]:
    "Return EntryPoint objects for all installed packages.\n\n    Pass selection parameters (group or name) to filter the\n    result to entry points matching those properties (see\n    EntryPoints.select()).\n\n    For compatibility, returns ``SelectableGroups`` object unless\n    selection parameters are supplied. In the future, this function\n    will return ``EntryPoints`` instead of ``SelectableGroups``\n    even when no selection parameters are supplied.\n\n    For maximum future compatibility, pass selection parameters\n    or invoke ``.select`` with parameters on the result.\n\n    :return: EntryPoints or SelectableGroups for all installed packages.\n    "
    unique = functools.partial(unique_everseen, key=operator.attrgetter("name"))
    eps = itertools.chain.from_iterable(
        (dist.entry_points for dist in unique(distributions()))
    )
    return SelectableGroups.load(eps).select(**params)


def files(distribution_name):
    "Return a list of files for the named package.\n\n    :param distribution_name: The name of the distribution package to query.\n    :return: List of files composing the distribution.\n    "
    return distribution(distribution_name).files


def requires(distribution_name):
    "\n    Return a list of requirements for the named package.\n\n    :return: An iterator of requirements, suitable for\n    packaging.requirement.Requirement.\n    "
    return distribution(distribution_name).requires


def packages_distributions() -> Mapping[(str, List[str])]:
    "\n    Return a mapping of top-level packages to their\n    distributions.\n\n    >>> import collections.abc\n    >>> pkgs = packages_distributions()\n    >>> all(isinstance(dist, collections.abc.Sequence) for dist in pkgs.values())\n    True\n    "
    pkg_to_dist = collections.defaultdict(list)
    for dist in distributions():
        for pkg in (dist.read_text("top_level.txt") or "").split():
            pkg_to_dist[pkg].append(dist.metadata["Name"])
    return dict(pkg_to_dist)
