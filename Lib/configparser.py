"Configuration file parser.\n\nA configuration file consists of sections, lead by a \"[section]\" header,\nand followed by \"name: value\" entries, with continuations and such in\nthe style of RFC 822.\n\nIntrinsic defaults can be specified by passing them into the\nConfigParser constructor as a dictionary.\n\nclass:\n\nConfigParser -- responsible for parsing a list of\n                    configuration files, and managing the parsed database.\n\n    methods:\n\n    __init__(defaults=None, dict_type=_default_dict, allow_no_value=False,\n             delimiters=('=', ':'), comment_prefixes=('#', ';'),\n             inline_comment_prefixes=None, strict=True,\n             empty_lines_in_values=True, default_section='DEFAULT',\n             interpolation=<unset>, converters=<unset>):\n        Create the parser. When `defaults' is given, it is initialized into the\n        dictionary or intrinsic defaults. The keys must be strings, the values\n        must be appropriate for %()s string interpolation.\n\n        When `dict_type' is given, it will be used to create the dictionary\n        objects for the list of sections, for the options within a section, and\n        for the default values.\n\n        When `delimiters' is given, it will be used as the set of substrings\n        that divide keys from values.\n\n        When `comment_prefixes' is given, it will be used as the set of\n        substrings that prefix comments in empty lines. Comments can be\n        indented.\n\n        When `inline_comment_prefixes' is given, it will be used as the set of\n        substrings that prefix comments in non-empty lines.\n\n        When `strict` is True, the parser won't allow for any section or option\n        duplicates while reading from a single source (file, string or\n        dictionary). Default is True.\n\n        When `empty_lines_in_values' is False (default: True), each empty line\n        marks the end of an option. Otherwise, internal empty lines of\n        a multiline option are kept as part of the value.\n\n        When `allow_no_value' is True (default: False), options without\n        values are accepted; the value presented for these is None.\n\n        When `default_section' is given, the name of the special section is\n        named accordingly. By default it is called ``\"DEFAULT\"`` but this can\n        be customized to point to any other valid section name. Its current\n        value can be retrieved using the ``parser_instance.default_section``\n        attribute and may be modified at runtime.\n\n        When `interpolation` is given, it should be an Interpolation subclass\n        instance. It will be used as the handler for option value\n        pre-processing when using getters. RawConfigParser objects don't do\n        any sort of interpolation, whereas ConfigParser uses an instance of\n        BasicInterpolation. The library also provides a ``zc.buildbot``\n        inspired ExtendedInterpolation implementation.\n\n        When `converters` is given, it should be a dictionary where each key\n        represents the name of a type converter and each value is a callable\n        implementing the conversion from string to the desired datatype. Every\n        converter gets its corresponding get*() method on the parser object and\n        section proxies.\n\n    sections()\n        Return all the configuration section names, sans DEFAULT.\n\n    has_section(section)\n        Return whether the given section exists.\n\n    has_option(section, option)\n        Return whether the given option exists in the given section.\n\n    options(section)\n        Return list of configuration options for the named section.\n\n    read(filenames, encoding=None)\n        Read and parse the iterable of named configuration files, given by\n        name.  A single filename is also allowed.  Non-existing files\n        are ignored.  Return list of successfully read files.\n\n    read_file(f, filename=None)\n        Read and parse one configuration file, given as a file object.\n        The filename defaults to f.name; it is only used in error\n        messages (if f has no `name' attribute, the string `<???>' is used).\n\n    read_string(string)\n        Read configuration from a given string.\n\n    read_dict(dictionary)\n        Read configuration from a dictionary. Keys are section names,\n        values are dictionaries with keys and values that should be present\n        in the section. If the used dictionary type preserves order, sections\n        and their keys will be added in order. Values are automatically\n        converted to strings.\n\n    get(section, option, raw=False, vars=None, fallback=_UNSET)\n        Return a string value for the named option.  All % interpolations are\n        expanded in the return values, based on the defaults passed into the\n        constructor and the DEFAULT section.  Additional substitutions may be\n        provided using the `vars' argument, which must be a dictionary whose\n        contents override any pre-existing defaults. If `option' is a key in\n        `vars', the value from `vars' is used.\n\n    getint(section, options, raw=False, vars=None, fallback=_UNSET)\n        Like get(), but convert value to an integer.\n\n    getfloat(section, options, raw=False, vars=None, fallback=_UNSET)\n        Like get(), but convert value to a float.\n\n    getboolean(section, options, raw=False, vars=None, fallback=_UNSET)\n        Like get(), but convert value to a boolean (currently case\n        insensitively defined as 0, false, no, off for False, and 1, true,\n        yes, on for True).  Returns False or True.\n\n    items(section=_UNSET, raw=False, vars=None)\n        If section is given, return a list of tuples with (name, value) for\n        each option in the section. Otherwise, return a list of tuples with\n        (section_name, section_proxy) for each section, including DEFAULTSECT.\n\n    remove_section(section)\n        Remove the given file section and all its options.\n\n    remove_option(section, option)\n        Remove the given option from the given section.\n\n    set(section, option, value)\n        Set the given option.\n\n    write(fp, space_around_delimiters=True)\n        Write the configuration state in .ini format. If\n        `space_around_delimiters' is True (the default), delimiters\n        between keys and values are surrounded by spaces.\n"
from collections.abc import MutableMapping
from collections import ChainMap as _ChainMap
import functools
import io
import itertools
import os
import re
import sys
import warnings

__all__ = [
    "NoSectionError",
    "DuplicateOptionError",
    "DuplicateSectionError",
    "NoOptionError",
    "InterpolationError",
    "InterpolationDepthError",
    "InterpolationMissingOptionError",
    "InterpolationSyntaxError",
    "ParsingError",
    "MissingSectionHeaderError",
    "ConfigParser",
    "SafeConfigParser",
    "RawConfigParser",
    "Interpolation",
    "BasicInterpolation",
    "ExtendedInterpolation",
    "LegacyInterpolation",
    "SectionProxy",
    "ConverterMapping",
    "DEFAULTSECT",
    "MAX_INTERPOLATION_DEPTH",
]
_default_dict = dict
DEFAULTSECT = "DEFAULT"
MAX_INTERPOLATION_DEPTH = 10


class Error(Exception):
    "Base class for ConfigParser exceptions."

    def __init__(self, msg=""):
        self.message = msg
        Exception.__init__(self, msg)

    def __repr__(self):
        return self.message

    __str__ = __repr__


class NoSectionError(Error):
    "Raised when no section matches a requested option."

    def __init__(self, section):
        Error.__init__(self, ("No section: %r" % (section,)))
        self.section = section
        self.args = (section,)


class DuplicateSectionError(Error):
    "Raised when a section is repeated in an input source.\n\n    Possible repetitions that raise this exception are: multiple creation\n    using the API or in strict parsers when a section is found more than once\n    in a single input file, string or dictionary.\n    "

    def __init__(self, section, source=None, lineno=None):
        msg = [repr(section), " already exists"]
        if source is not None:
            message = ["While reading from ", repr(source)]
            if lineno is not None:
                message.append(" [line {0:2d}]".format(lineno))
            message.append(": section ")
            message.extend(msg)
            msg = message
        else:
            msg.insert(0, "Section ")
        Error.__init__(self, "".join(msg))
        self.section = section
        self.source = source
        self.lineno = lineno
        self.args = (section, source, lineno)


class DuplicateOptionError(Error):
    "Raised by strict parsers when an option is repeated in an input source.\n\n    Current implementation raises this exception only when an option is found\n    more than once in a single file, string or dictionary.\n    "

    def __init__(self, section, option, source=None, lineno=None):
        msg = [repr(option), " in section ", repr(section), " already exists"]
        if source is not None:
            message = ["While reading from ", repr(source)]
            if lineno is not None:
                message.append(" [line {0:2d}]".format(lineno))
            message.append(": option ")
            message.extend(msg)
            msg = message
        else:
            msg.insert(0, "Option ")
        Error.__init__(self, "".join(msg))
        self.section = section
        self.option = option
        self.source = source
        self.lineno = lineno
        self.args = (section, option, source, lineno)


class NoOptionError(Error):
    "A requested option was not found."

    def __init__(self, option, section):
        Error.__init__(self, ("No option %r in section: %r" % (option, section)))
        self.option = option
        self.section = section
        self.args = (option, section)


class InterpolationError(Error):
    "Base class for interpolation-related exceptions."

    def __init__(self, option, section, msg):
        Error.__init__(self, msg)
        self.option = option
        self.section = section
        self.args = (option, section, msg)


class InterpolationMissingOptionError(InterpolationError):
    "A string substitution required a setting which was not available."

    def __init__(self, option, section, rawval, reference):
        msg = "Bad value substitution: option {!r} in section {!r} contains an interpolation key {!r} which is not a valid option name. Raw value: {!r}".format(
            option, section, reference, rawval
        )
        InterpolationError.__init__(self, option, section, msg)
        self.reference = reference
        self.args = (option, section, rawval, reference)


class InterpolationSyntaxError(InterpolationError):
    "Raised when the source text contains invalid syntax.\n\n    Current implementation raises this exception when the source text into\n    which substitutions are made does not conform to the required syntax.\n    "


class InterpolationDepthError(InterpolationError):
    "Raised when substitutions are nested too deeply."

    def __init__(self, option, section, rawval):
        msg = "Recursion limit exceeded in value substitution: option {!r} in section {!r} contains an interpolation key which cannot be substituted in {} steps. Raw value: {!r}".format(
            option, section, MAX_INTERPOLATION_DEPTH, rawval
        )
        InterpolationError.__init__(self, option, section, msg)
        self.args = (option, section, rawval)


class ParsingError(Error):
    "Raised when a configuration file does not follow legal syntax."

    def __init__(self, source=None, filename=None):
        if filename and source:
            raise ValueError(
                "Cannot specify both `filename' and `source'. Use `source'."
            )
        elif (not filename) and (not source):
            raise ValueError("Required argument `source' not given.")
        elif filename:
            source = filename
        Error.__init__(self, ("Source contains parsing errors: %r" % source))
        self.source = source
        self.errors = []
        self.args = (source,)

    @property
    def filename(self):
        "Deprecated, use `source'."
        warnings.warn(
            "The 'filename' attribute will be removed in future versions.  Use 'source' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.source

    @filename.setter
    def filename(self, value):
        "Deprecated, user `source'."
        warnings.warn(
            "The 'filename' attribute will be removed in future versions.  Use 'source' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.source = value

    def append(self, lineno, line):
        self.errors.append((lineno, line))
        self.message += "\n\t[line %2d]: %s" % (lineno, line)


class MissingSectionHeaderError(ParsingError):
    "Raised when a key-value pair is found before any section header."

    def __init__(self, filename, lineno, line):
        Error.__init__(
            self,
            (
                "File contains no section headers.\nfile: %r, line: %d\n%r"
                % (filename, lineno, line)
            ),
        )
        self.source = filename
        self.lineno = lineno
        self.line = line
        self.args = (filename, lineno, line)


_UNSET = object()


class Interpolation:
    "Dummy interpolation that passes the value through with no changes."

    def before_get(self, parser, section, option, value, defaults):
        return value

    def before_set(self, parser, section, option, value):
        return value

    def before_read(self, parser, section, option, value):
        return value

    def before_write(self, parser, section, option, value):
        return value


class BasicInterpolation(Interpolation):
    'Interpolation as implemented in the classic ConfigParser.\n\n    The option values can contain format strings which refer to other values in\n    the same section, or values in the special default section.\n\n    For example:\n\n        something: %(dir)s/whatever\n\n    would resolve the "%(dir)s" to the value of dir.  All reference\n    expansions are done late, on demand. If a user needs to use a bare % in\n    a configuration file, she can escape it by writing %%. Other % usage\n    is considered a user error and raises `InterpolationSyntaxError\'.'
    _KEYCRE = re.compile("%\\(([^)]+)\\)s")

    def before_get(self, parser, section, option, value, defaults):
        L = []
        self._interpolate_some(parser, option, L, value, section, defaults, 1)
        return "".join(L)

    def before_set(self, parser, section, option, value):
        tmp_value = value.replace("%%", "")
        tmp_value = self._KEYCRE.sub("", tmp_value)
        if "%" in tmp_value:
            raise ValueError(
                (
                    "invalid interpolation syntax in %r at position %d"
                    % (value, tmp_value.find("%"))
                )
            )
        return value

    def _interpolate_some(self, parser, option, accum, rest, section, map, depth):
        rawval = parser.get(section, option, raw=True, fallback=rest)
        if depth > MAX_INTERPOLATION_DEPTH:
            raise InterpolationDepthError(option, section, rawval)
        while rest:
            p = rest.find("%")
            if p < 0:
                accum.append(rest)
                return
            if p > 0:
                accum.append(rest[:p])
                rest = rest[p:]
            c = rest[1:2]
            if c == "%":
                accum.append("%")
                rest = rest[2:]
            elif c == "(":
                m = self._KEYCRE.match(rest)
                if m is None:
                    raise InterpolationSyntaxError(
                        option,
                        section,
                        ("bad interpolation variable reference %r" % rest),
                    )
                var = parser.optionxform(m.group(1))
                rest = rest[m.end() :]
                try:
                    v = map[var]
                except KeyError:
                    raise InterpolationMissingOptionError(
                        option, section, rawval, var
                    ) from None
                if "%" in v:
                    self._interpolate_some(
                        parser, option, accum, v, section, map, (depth + 1)
                    )
                else:
                    accum.append(v)
            else:
                raise InterpolationSyntaxError(
                    option,
                    section,
                    ("'%%' must be followed by '%%' or '(', found: %r" % (rest,)),
                )


class ExtendedInterpolation(Interpolation):
    "Advanced variant of interpolation, supports the syntax used by\n    `zc.buildout'. Enables interpolation between sections."
    _KEYCRE = re.compile("\\$\\{([^}]+)\\}")

    def before_get(self, parser, section, option, value, defaults):
        L = []
        self._interpolate_some(parser, option, L, value, section, defaults, 1)
        return "".join(L)

    def before_set(self, parser, section, option, value):
        tmp_value = value.replace("$$", "")
        tmp_value = self._KEYCRE.sub("", tmp_value)
        if "$" in tmp_value:
            raise ValueError(
                (
                    "invalid interpolation syntax in %r at position %d"
                    % (value, tmp_value.find("$"))
                )
            )
        return value

    def _interpolate_some(self, parser, option, accum, rest, section, map, depth):
        rawval = parser.get(section, option, raw=True, fallback=rest)
        if depth > MAX_INTERPOLATION_DEPTH:
            raise InterpolationDepthError(option, section, rawval)
        while rest:
            p = rest.find("$")
            if p < 0:
                accum.append(rest)
                return
            if p > 0:
                accum.append(rest[:p])
                rest = rest[p:]
            c = rest[1:2]
            if c == "$":
                accum.append("$")
                rest = rest[2:]
            elif c == "{":
                m = self._KEYCRE.match(rest)
                if m is None:
                    raise InterpolationSyntaxError(
                        option,
                        section,
                        ("bad interpolation variable reference %r" % rest),
                    )
                path = m.group(1).split(":")
                rest = rest[m.end() :]
                sect = section
                opt = option
                try:
                    if len(path) == 1:
                        opt = parser.optionxform(path[0])
                        v = map[opt]
                    elif len(path) == 2:
                        sect = path[0]
                        opt = parser.optionxform(path[1])
                        v = parser.get(sect, opt, raw=True)
                    else:
                        raise InterpolationSyntaxError(
                            option, section, ("More than one ':' found: %r" % (rest,))
                        )
                except (KeyError, NoSectionError, NoOptionError):
                    raise InterpolationMissingOptionError(
                        option, section, rawval, ":".join(path)
                    ) from None
                if "$" in v:
                    self._interpolate_some(
                        parser,
                        opt,
                        accum,
                        v,
                        sect,
                        dict(parser.items(sect, raw=True)),
                        (depth + 1),
                    )
                else:
                    accum.append(v)
            else:
                raise InterpolationSyntaxError(
                    option,
                    section,
                    ("'$' must be followed by '$' or '{', found: %r" % (rest,)),
                )


class LegacyInterpolation(Interpolation):
    "Deprecated interpolation used in old versions of ConfigParser.\n    Use BasicInterpolation or ExtendedInterpolation instead."
    _KEYCRE = re.compile("%\\(([^)]*)\\)s|.")

    def before_get(self, parser, section, option, value, vars):
        rawval = value
        depth = MAX_INTERPOLATION_DEPTH
        while depth:
            depth -= 1
            if value and ("%(" in value):
                replace = functools.partial(self._interpolation_replace, parser=parser)
                value = self._KEYCRE.sub(replace, value)
                try:
                    value = value % vars
                except KeyError as e:
                    raise InterpolationMissingOptionError(
                        option, section, rawval, e.args[0]
                    ) from None
            else:
                break
        if value and ("%(" in value):
            raise InterpolationDepthError(option, section, rawval)
        return value

    def before_set(self, parser, section, option, value):
        return value

    @staticmethod
    def _interpolation_replace(match, parser):
        s = match.group(1)
        if s is None:
            return match.group()
        else:
            return "%%(%s)s" % parser.optionxform(s)


class RawConfigParser(MutableMapping):
    "ConfigParser that does not do interpolation."
    _SECT_TMPL = "\n        \\[                                 # [\n        (?P<header>[^]]+)                  # very permissive!\n        \\]                                 # ]\n        "
    _OPT_TMPL = "\n        (?P<option>.*?)                    # very permissive!\n        \\s*(?P<vi>{delim})\\s*              # any number of space/tab,\n                                           # followed by any of the\n                                           # allowed delimiters,\n                                           # followed by any space/tab\n        (?P<value>.*)$                     # everything up to eol\n        "
    _OPT_NV_TMPL = "\n        (?P<option>.*?)                    # very permissive!\n        \\s*(?:                             # any number of space/tab,\n        (?P<vi>{delim})\\s*                 # optionally followed by\n                                           # any of the allowed\n                                           # delimiters, followed by any\n                                           # space/tab\n        (?P<value>.*))?$                   # everything up to eol\n        "
    _DEFAULT_INTERPOLATION = Interpolation()
    SECTCRE = re.compile(_SECT_TMPL, re.VERBOSE)
    OPTCRE = re.compile(_OPT_TMPL.format(delim="=|:"), re.VERBOSE)
    OPTCRE_NV = re.compile(_OPT_NV_TMPL.format(delim="=|:"), re.VERBOSE)
    NONSPACECRE = re.compile("\\S")
    BOOLEAN_STATES = {
        "1": True,
        "yes": True,
        "true": True,
        "on": True,
        "0": False,
        "no": False,
        "false": False,
        "off": False,
    }

    def __init__(
        self,
        defaults=None,
        dict_type=_default_dict,
        allow_no_value=False,
        *,
        delimiters=("=", ":"),
        comment_prefixes=("#", ";"),
        inline_comment_prefixes=None,
        strict=True,
        empty_lines_in_values=True,
        default_section=DEFAULTSECT,
        interpolation=_UNSET,
        converters=_UNSET
    ):
        self._dict = dict_type
        self._sections = self._dict()
        self._defaults = self._dict()
        self._converters = ConverterMapping(self)
        self._proxies = self._dict()
        self._proxies[default_section] = SectionProxy(self, default_section)
        self._delimiters = tuple(delimiters)
        if delimiters == ("=", ":"):
            self._optcre = self.OPTCRE_NV if allow_no_value else self.OPTCRE
        else:
            d = "|".join((re.escape(d) for d in delimiters))
            if allow_no_value:
                self._optcre = re.compile(self._OPT_NV_TMPL.format(delim=d), re.VERBOSE)
            else:
                self._optcre = re.compile(self._OPT_TMPL.format(delim=d), re.VERBOSE)
        self._comment_prefixes = tuple((comment_prefixes or ()))
        self._inline_comment_prefixes = tuple((inline_comment_prefixes or ()))
        self._strict = strict
        self._allow_no_value = allow_no_value
        self._empty_lines_in_values = empty_lines_in_values
        self.default_section = default_section
        self._interpolation = interpolation
        if self._interpolation is _UNSET:
            self._interpolation = self._DEFAULT_INTERPOLATION
        if self._interpolation is None:
            self._interpolation = Interpolation()
        if converters is not _UNSET:
            self._converters.update(converters)
        if defaults:
            self._read_defaults(defaults)

    def defaults(self):
        return self._defaults

    def sections(self):
        "Return a list of section names, excluding [DEFAULT]"
        return list(self._sections.keys())

    def add_section(self, section):
        "Create a new section in the configuration.\n\n        Raise DuplicateSectionError if a section by the specified name\n        already exists. Raise ValueError if name is DEFAULT.\n        "
        if section == self.default_section:
            raise ValueError(("Invalid section name: %r" % section))
        if section in self._sections:
            raise DuplicateSectionError(section)
        self._sections[section] = self._dict()
        self._proxies[section] = SectionProxy(self, section)

    def has_section(self, section):
        "Indicate whether the named section is present in the configuration.\n\n        The DEFAULT section is not acknowledged.\n        "
        return section in self._sections

    def options(self, section):
        "Return a list of option names for the given section name."
        try:
            opts = self._sections[section].copy()
        except KeyError:
            raise NoSectionError(section) from None
        opts.update(self._defaults)
        return list(opts.keys())

    def read(self, filenames, encoding=None):
        "Read and parse a filename or an iterable of filenames.\n\n        Files that cannot be opened are silently ignored; this is\n        designed so that you can specify an iterable of potential\n        configuration file locations (e.g. current directory, user's\n        home directory, systemwide directory), and all existing\n        configuration files in the iterable will be read.  A single\n        filename may also be given.\n\n        Return list of successfully read files.\n        "
        if isinstance(filenames, (str, bytes, os.PathLike)):
            filenames = [filenames]
        encoding = io.text_encoding(encoding)
        read_ok = []
        for filename in filenames:
            try:
                with open(filename, encoding=encoding) as fp:
                    self._read(fp, filename)
            except OSError:
                continue
            if isinstance(filename, os.PathLike):
                filename = os.fspath(filename)
            read_ok.append(filename)
        return read_ok

    def read_file(self, f, source=None):
        "Like read() but the argument must be a file-like object.\n\n        The `f' argument must be iterable, returning one line at a time.\n        Optional second argument is the `source' specifying the name of the\n        file being read. If not given, it is taken from f.name. If `f' has no\n        `name' attribute, `<???>' is used.\n        "
        if source is None:
            try:
                source = f.name
            except AttributeError:
                source = "<???>"
        self._read(f, source)

    def read_string(self, string, source="<string>"):
        "Read configuration from a given string."
        sfile = io.StringIO(string)
        self.read_file(sfile, source)

    def read_dict(self, dictionary, source="<dict>"):
        "Read configuration from a dictionary.\n\n        Keys are section names, values are dictionaries with keys and values\n        that should be present in the section. If the used dictionary type\n        preserves order, sections and their keys will be added in order.\n\n        All types held in the dictionary are converted to strings during\n        reading, including section names, option names and keys.\n\n        Optional second argument is the `source' specifying the name of the\n        dictionary being read.\n        "
        elements_added = set()
        for (section, keys) in dictionary.items():
            section = str(section)
            try:
                self.add_section(section)
            except (DuplicateSectionError, ValueError):
                if self._strict and (section in elements_added):
                    raise
            elements_added.add(section)
            for (key, value) in keys.items():
                key = self.optionxform(str(key))
                if value is not None:
                    value = str(value)
                if self._strict and ((section, key) in elements_added):
                    raise DuplicateOptionError(section, key, source)
                elements_added.add((section, key))
                self.set(section, key, value)

    def readfp(self, fp, filename=None):
        "Deprecated, use read_file instead."
        warnings.warn(
            "This method will be removed in future versions.  Use 'parser.read_file()' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.read_file(fp, source=filename)

    def get(self, section, option, *, raw=False, vars=None, fallback=_UNSET):
        "Get an option value for a given section.\n\n        If `vars' is provided, it must be a dictionary. The option is looked up\n        in `vars' (if provided), `section', and in `DEFAULTSECT' in that order.\n        If the key is not found and `fallback' is provided, it is used as\n        a fallback value. `None' can be provided as a `fallback' value.\n\n        If interpolation is enabled and the optional argument `raw' is False,\n        all interpolations are expanded in the return values.\n\n        Arguments `raw', `vars', and `fallback' are keyword only.\n\n        The section DEFAULT is special.\n        "
        try:
            d = self._unify_values(section, vars)
        except NoSectionError:
            if fallback is _UNSET:
                raise
            else:
                return fallback
        option = self.optionxform(option)
        try:
            value = d[option]
        except KeyError:
            if fallback is _UNSET:
                raise NoOptionError(option, section)
            else:
                return fallback
        if raw or (value is None):
            return value
        else:
            return self._interpolation.before_get(self, section, option, value, d)

    def _get(self, section, conv, option, **kwargs):
        return conv(self.get(section, option, **kwargs))

    def _get_conv(
        self, section, option, conv, *, raw=False, vars=None, fallback=_UNSET, **kwargs
    ):
        try:
            return self._get(section, conv, option, raw=raw, vars=vars, **kwargs)
        except (NoSectionError, NoOptionError):
            if fallback is _UNSET:
                raise
            return fallback

    def getint(
        self, section, option, *, raw=False, vars=None, fallback=_UNSET, **kwargs
    ):
        return self._get_conv(
            section, option, int, raw=raw, vars=vars, fallback=fallback, **kwargs
        )

    def getfloat(
        self, section, option, *, raw=False, vars=None, fallback=_UNSET, **kwargs
    ):
        return self._get_conv(
            section, option, float, raw=raw, vars=vars, fallback=fallback, **kwargs
        )

    def getboolean(
        self, section, option, *, raw=False, vars=None, fallback=_UNSET, **kwargs
    ):
        return self._get_conv(
            section,
            option,
            self._convert_to_boolean,
            raw=raw,
            vars=vars,
            fallback=fallback,
            **kwargs
        )

    def items(self, section=_UNSET, raw=False, vars=None):
        "Return a list of (name, value) tuples for each option in a section.\n\n        All % interpolations are expanded in the return values, based on the\n        defaults passed into the constructor, unless the optional argument\n        `raw' is true.  Additional substitutions may be provided using the\n        `vars' argument, which must be a dictionary whose contents overrides\n        any pre-existing defaults.\n\n        The section DEFAULT is special.\n        "
        if section is _UNSET:
            return super().items()
        d = self._defaults.copy()
        try:
            d.update(self._sections[section])
        except KeyError:
            if section != self.default_section:
                raise NoSectionError(section)
        orig_keys = list(d.keys())
        if vars:
            for (key, value) in vars.items():
                d[self.optionxform(key)] = value
        value_getter = lambda option: self._interpolation.before_get(
            self, section, option, d[option], d
        )
        if raw:
            value_getter = lambda option: d[option]
        return [(option, value_getter(option)) for option in orig_keys]

    def popitem(self):
        "Remove a section from the parser and return it as\n        a (section_name, section_proxy) tuple. If no section is present, raise\n        KeyError.\n\n        The section DEFAULT is never returned because it cannot be removed.\n        "
        for key in self.sections():
            value = self[key]
            del self[key]
            return (key, value)
        raise KeyError

    def optionxform(self, optionstr):
        return optionstr.lower()

    def has_option(self, section, option):
        "Check for the existence of a given option in a given section.\n        If the specified `section' is None or an empty string, DEFAULT is\n        assumed. If the specified `section' does not exist, returns False."
        if (not section) or (section == self.default_section):
            option = self.optionxform(option)
            return option in self._defaults
        elif section not in self._sections:
            return False
        else:
            option = self.optionxform(option)
            return (option in self._sections[section]) or (option in self._defaults)

    def set(self, section, option, value=None):
        "Set an option."
        if value:
            value = self._interpolation.before_set(self, section, option, value)
        if (not section) or (section == self.default_section):
            sectdict = self._defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise NoSectionError(section) from None
        sectdict[self.optionxform(option)] = value

    def write(self, fp, space_around_delimiters=True):
        "Write an .ini-format representation of the configuration state.\n\n        If `space_around_delimiters' is True (the default), delimiters\n        between keys and values are surrounded by spaces.\n        "
        if space_around_delimiters:
            d = " {} ".format(self._delimiters[0])
        else:
            d = self._delimiters[0]
        if self._defaults:
            self._write_section(fp, self.default_section, self._defaults.items(), d)
        for section in self._sections:
            self._write_section(fp, section, self._sections[section].items(), d)

    def _write_section(self, fp, section_name, section_items, delimiter):
        "Write a single section to the specified `fp'."
        fp.write("[{}]\n".format(section_name))
        for (key, value) in section_items:
            value = self._interpolation.before_write(self, section_name, key, value)
            if (value is not None) or (not self._allow_no_value):
                value = delimiter + str(value).replace("\n", "\n\t")
            else:
                value = ""
            fp.write("{}{}\n".format(key, value))
        fp.write("\n")

    def remove_option(self, section, option):
        "Remove an option."
        if (not section) or (section == self.default_section):
            sectdict = self._defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise NoSectionError(section) from None
        option = self.optionxform(option)
        existed = option in sectdict
        if existed:
            del sectdict[option]
        return existed

    def remove_section(self, section):
        "Remove a file section."
        existed = section in self._sections
        if existed:
            del self._sections[section]
            del self._proxies[section]
        return existed

    def __getitem__(self, key):
        if (key != self.default_section) and (not self.has_section(key)):
            raise KeyError(key)
        return self._proxies[key]

    def __setitem__(self, key, value):
        if (key in self) and (self[key] is value):
            return
        if key == self.default_section:
            self._defaults.clear()
        elif key in self._sections:
            self._sections[key].clear()
        self.read_dict({key: value})

    def __delitem__(self, key):
        if key == self.default_section:
            raise ValueError("Cannot remove the default section.")
        if not self.has_section(key):
            raise KeyError(key)
        self.remove_section(key)

    def __contains__(self, key):
        return (key == self.default_section) or self.has_section(key)

    def __len__(self):
        return len(self._sections) + 1

    def __iter__(self):
        return itertools.chain((self.default_section,), self._sections.keys())

    def _read(self, fp, fpname):
        "Parse a sectioned configuration file.\n\n        Each section in a configuration file contains a header, indicated by\n        a name in square brackets (`[]'), plus key/value options, indicated by\n        `name' and `value' delimited with a specific substring (`=' or `:' by\n        default).\n\n        Values can span multiple lines, as long as they are indented deeper\n        than the first line of the value. Depending on the parser's mode, blank\n        lines may be treated as parts of multiline values or ignored.\n\n        Configuration files may include comments, prefixed by specific\n        characters (`#' and `;' by default). Comments may appear on their own\n        in an otherwise empty line or may be entered in lines holding values or\n        section names.\n        "
        elements_added = set()
        cursect = None
        sectname = None
        optname = None
        lineno = 0
        indent_level = 0
        e = None
        for (lineno, line) in enumerate(fp, start=1):
            comment_start = sys.maxsize
            inline_prefixes = {p: (-1) for p in self._inline_comment_prefixes}
            while (comment_start == sys.maxsize) and inline_prefixes:
                next_prefixes = {}
                for (prefix, index) in inline_prefixes.items():
                    index = line.find(prefix, (index + 1))
                    if index == (-1):
                        continue
                    next_prefixes[prefix] = index
                    if (index == 0) or ((index > 0) and line[(index - 1)].isspace()):
                        comment_start = min(comment_start, index)
                inline_prefixes = next_prefixes
            for prefix in self._comment_prefixes:
                if line.strip().startswith(prefix):
                    comment_start = 0
                    break
            if comment_start == sys.maxsize:
                comment_start = None
            value = line[:comment_start].strip()
            if not value:
                if self._empty_lines_in_values:
                    if (
                        (comment_start is None)
                        and (cursect is not None)
                        and optname
                        and (cursect[optname] is not None)
                    ):
                        cursect[optname].append("")
                else:
                    indent_level = sys.maxsize
                continue
            first_nonspace = self.NONSPACECRE.search(line)
            cur_indent_level = first_nonspace.start() if first_nonspace else 0
            if (cursect is not None) and optname and (cur_indent_level > indent_level):
                cursect[optname].append(value)
            else:
                indent_level = cur_indent_level
                mo = self.SECTCRE.match(value)
                if mo:
                    sectname = mo.group("header")
                    if sectname in self._sections:
                        if self._strict and (sectname in elements_added):
                            raise DuplicateSectionError(sectname, fpname, lineno)
                        cursect = self._sections[sectname]
                        elements_added.add(sectname)
                    elif sectname == self.default_section:
                        cursect = self._defaults
                    else:
                        cursect = self._dict()
                        self._sections[sectname] = cursect
                        self._proxies[sectname] = SectionProxy(self, sectname)
                        elements_added.add(sectname)
                    optname = None
                elif cursect is None:
                    raise MissingSectionHeaderError(fpname, lineno, line)
                else:
                    mo = self._optcre.match(value)
                    if mo:
                        (optname, vi, optval) = mo.group("option", "vi", "value")
                        if not optname:
                            e = self._handle_error(e, fpname, lineno, line)
                        optname = self.optionxform(optname.rstrip())
                        if self._strict and ((sectname, optname) in elements_added):
                            raise DuplicateOptionError(
                                sectname, optname, fpname, lineno
                            )
                        elements_added.add((sectname, optname))
                        if optval is not None:
                            optval = optval.strip()
                            cursect[optname] = [optval]
                        else:
                            cursect[optname] = None
                    else:
                        e = self._handle_error(e, fpname, lineno, line)
        self._join_multiline_values()
        if e:
            raise e

    def _join_multiline_values(self):
        defaults = (self.default_section, self._defaults)
        all_sections = itertools.chain((defaults,), self._sections.items())
        for (section, options) in all_sections:
            for (name, val) in options.items():
                if isinstance(val, list):
                    val = "\n".join(val).rstrip()
                options[name] = self._interpolation.before_read(
                    self, section, name, val
                )

    def _read_defaults(self, defaults):
        "Read the defaults passed in the initializer.\n        Note: values can be non-string."
        for (key, value) in defaults.items():
            self._defaults[self.optionxform(key)] = value

    def _handle_error(self, exc, fpname, lineno, line):
        if not exc:
            exc = ParsingError(fpname)
        exc.append(lineno, repr(line))
        return exc

    def _unify_values(self, section, vars):
        "Create a sequence of lookups with 'vars' taking priority over\n        the 'section' which takes priority over the DEFAULTSECT.\n\n        "
        sectiondict = {}
        try:
            sectiondict = self._sections[section]
        except KeyError:
            if section != self.default_section:
                raise NoSectionError(section) from None
        vardict = {}
        if vars:
            for (key, value) in vars.items():
                if value is not None:
                    value = str(value)
                vardict[self.optionxform(key)] = value
        return _ChainMap(vardict, sectiondict, self._defaults)

    def _convert_to_boolean(self, value):
        "Return a boolean value translating from other types if necessary.\n        "
        if value.lower() not in self.BOOLEAN_STATES:
            raise ValueError(("Not a boolean: %s" % value))
        return self.BOOLEAN_STATES[value.lower()]

    def _validate_value_types(self, *, section="", option="", value=""):
        "Raises a TypeError for non-string values.\n\n        The only legal non-string value if we allow valueless\n        options is None, so we need to check if the value is a\n        string if:\n        - we do not allow valueless options, or\n        - we allow valueless options but the value is not None\n\n        For compatibility reasons this method is not used in classic set()\n        for RawConfigParsers. It is invoked in every case for mapping protocol\n        access and in ConfigParser.set().\n        "
        if not isinstance(section, str):
            raise TypeError("section names must be strings")
        if not isinstance(option, str):
            raise TypeError("option keys must be strings")
        if (not self._allow_no_value) or value:
            if not isinstance(value, str):
                raise TypeError("option values must be strings")

    @property
    def converters(self):
        return self._converters


class ConfigParser(RawConfigParser):
    "ConfigParser implementing interpolation."
    _DEFAULT_INTERPOLATION = BasicInterpolation()

    def set(self, section, option, value=None):
        "Set an option.  Extends RawConfigParser.set by validating type and\n        interpolation syntax on the value."
        self._validate_value_types(option=option, value=value)
        super().set(section, option, value)

    def add_section(self, section):
        "Create a new section in the configuration.  Extends\n        RawConfigParser.add_section by validating if the section name is\n        a string."
        self._validate_value_types(section=section)
        super().add_section(section)

    def _read_defaults(self, defaults):
        "Reads the defaults passed in the initializer, implicitly converting\n        values to strings like the rest of the API.\n\n        Does not perform interpolation for backwards compatibility.\n        "
        try:
            hold_interpolation = self._interpolation
            self._interpolation = Interpolation()
            self.read_dict({self.default_section: defaults})
        finally:
            self._interpolation = hold_interpolation


class SafeConfigParser(ConfigParser):
    "ConfigParser alias for backwards compatibility purposes."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn(
            "The SafeConfigParser class has been renamed to ConfigParser in Python 3.2. This alias will be removed in future versions. Use ConfigParser directly instead.",
            DeprecationWarning,
            stacklevel=2,
        )


class SectionProxy(MutableMapping):
    "A proxy for a single section from a parser."

    def __init__(self, parser, name):
        "Creates a view on a section of the specified `name` in `parser`."
        self._parser = parser
        self._name = name
        for conv in parser.converters:
            key = "get" + conv
            getter = functools.partial(self.get, _impl=getattr(parser, key))
            setattr(self, key, getter)

    def __repr__(self):
        return "<Section: {}>".format(self._name)

    def __getitem__(self, key):
        if not self._parser.has_option(self._name, key):
            raise KeyError(key)
        return self._parser.get(self._name, key)

    def __setitem__(self, key, value):
        self._parser._validate_value_types(option=key, value=value)
        return self._parser.set(self._name, key, value)

    def __delitem__(self, key):
        if not (
            self._parser.has_option(self._name, key)
            and self._parser.remove_option(self._name, key)
        ):
            raise KeyError(key)

    def __contains__(self, key):
        return self._parser.has_option(self._name, key)

    def __len__(self):
        return len(self._options())

    def __iter__(self):
        return self._options().__iter__()

    def _options(self):
        if self._name != self._parser.default_section:
            return self._parser.options(self._name)
        else:
            return self._parser.defaults()

    @property
    def parser(self):
        return self._parser

    @property
    def name(self):
        return self._name

    def get(self, option, fallback=None, *, raw=False, vars=None, _impl=None, **kwargs):
        "Get an option value.\n\n        Unless `fallback` is provided, `None` will be returned if the option\n        is not found.\n\n        "
        if not _impl:
            _impl = self._parser.get
        return _impl(
            self._name, option, raw=raw, vars=vars, fallback=fallback, **kwargs
        )


class ConverterMapping(MutableMapping):
    "Enables reuse of get*() methods between the parser and section proxies.\n\n    If a parser class implements a getter directly, the value for the given\n    key will be ``None``. The presence of the converter name here enables\n    section proxies to find and use the implementation on the parser class.\n    "
    GETTERCRE = re.compile("^get(?P<name>.+)$")

    def __init__(self, parser):
        self._parser = parser
        self._data = {}
        for getter in dir(self._parser):
            m = self.GETTERCRE.match(getter)
            if (not m) or (not callable(getattr(self._parser, getter))):
                continue
            self._data[m.group("name")] = None

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        try:
            k = "get" + key
        except TypeError:
            raise ValueError("Incompatible key: {} (type: {})".format(key, type(key)))
        if k == "get":
            raise ValueError('Incompatible key: cannot use "" as a name')
        self._data[key] = value
        func = functools.partial(self._parser._get_conv, conv=value)
        func.converter = value
        setattr(self._parser, k, func)
        for proxy in self._parser.values():
            getter = functools.partial(proxy.get, _impl=func)
            setattr(proxy, k, getter)

    def __delitem__(self, key):
        try:
            k = "get" + (key or None)
        except TypeError:
            raise KeyError(key)
        del self._data[key]
        for inst in itertools.chain((self._parser,), self._parser.values()):
            try:
                delattr(inst, k)
            except AttributeError:
                continue

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)
