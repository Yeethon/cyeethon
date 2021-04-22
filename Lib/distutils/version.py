"Provides classes to represent module version numbers (one class for\neach style of version numbering).  There are currently two such classes\nimplemented: StrictVersion and LooseVersion.\n\nEvery version number class implements the following interface:\n  * the 'parse' method takes a string and parses it to some internal\n    representation; if the string is an invalid version number,\n    'parse' raises a ValueError exception\n  * the class constructor takes an optional string argument which,\n    if supplied, is passed to 'parse'\n  * __str__ reconstructs the string that was passed to 'parse' (or\n    an equivalent string -- ie. one that will generate an equivalent\n    version number instance)\n  * __repr__ generates Python code to recreate the version number instance\n  * _cmp compares the current instance with either another instance\n    of the same class or a string (which will be parsed to an instance\n    of the same class, thus must follow the same rules)\n"
import re


class Version:
    "Abstract base class for version numbering classes.  Just provides\n    constructor (__init__) and reproducer (__repr__), because those\n    seem to be the same for all version numbering classes; and route\n    rich comparisons to _cmp.\n    "

    def __init__(self, vstring=None):
        if vstring:
            self.parse(vstring)

    def __repr__(self):
        return "%s ('%s')" % (self.__class__.__name__, str(self))

    def __eq__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c == 0

    def __lt__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c < 0

    def __le__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c <= 0

    def __gt__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c > 0

    def __ge__(self, other):
        c = self._cmp(other)
        if c is NotImplemented:
            return c
        return c >= 0


class StrictVersion(Version):
    "Version numbering for anal retentives and software idealists.\n    Implements the standard interface for version number classes as\n    described above.  A version number consists of two or three\n    dot-separated numeric components, with an optional \"pre-release\" tag\n    on the end.  The pre-release tag consists of the letter 'a' or 'b'\n    followed by a number.  If the numeric components of two version\n    numbers are equal, then one with a pre-release tag will always\n    be deemed earlier (lesser) than one without.\n\n    The following are valid version numbers (shown in the order that\n    would be obtained by sorting according to the supplied cmp function):\n\n        0.4       0.4.0  (these two are equivalent)\n        0.4.1\n        0.5a1\n        0.5b3\n        0.5\n        0.9.6\n        1.0\n        1.0.4a3\n        1.0.4b1\n        1.0.4\n\n    The following are examples of invalid version numbers:\n\n        1\n        2.7.2.2\n        1.3.a4\n        1.3pl1\n        1.3c4\n\n    The rationale for this version numbering system will be explained\n    in the distutils documentation.\n    "
    version_re = re.compile(
        "^(\\d+) \\. (\\d+) (\\. (\\d+))? ([ab](\\d+))?$", (re.VERBOSE | re.ASCII)
    )

    def parse(self, vstring):
        match = self.version_re.match(vstring)
        if not match:
            raise ValueError(("invalid version number '%s'" % vstring))
        (major, minor, patch, prerelease, prerelease_num) = match.group(1, 2, 4, 5, 6)
        if patch:
            self.version = tuple(map(int, [major, minor, patch]))
        else:
            self.version = tuple(map(int, [major, minor])) + (0,)
        if prerelease:
            self.prerelease = (prerelease[0], int(prerelease_num))
        else:
            self.prerelease = None

    def __str__(self):
        if self.version[2] == 0:
            vstring = ".".join(map(str, self.version[0:2]))
        else:
            vstring = ".".join(map(str, self.version))
        if self.prerelease:
            vstring = (vstring + self.prerelease[0]) + str(self.prerelease[1])
        return vstring

    def _cmp(self, other):
        if isinstance(other, str):
            other = StrictVersion(other)
        elif not isinstance(other, StrictVersion):
            return NotImplemented
        if self.version != other.version:
            if self.version < other.version:
                return -1
            else:
                return 1
        if (not self.prerelease) and (not other.prerelease):
            return 0
        elif self.prerelease and (not other.prerelease):
            return -1
        elif (not self.prerelease) and other.prerelease:
            return 1
        elif self.prerelease and other.prerelease:
            if self.prerelease == other.prerelease:
                return 0
            elif self.prerelease < other.prerelease:
                return -1
            else:
                return 1
        else:
            assert False, "never get here"


class LooseVersion(Version):
    'Version numbering for anarchists and software realists.\n    Implements the standard interface for version number classes as\n    described above.  A version number consists of a series of numbers,\n    separated by either periods or strings of letters.  When comparing\n    version numbers, the numeric components will be compared\n    numerically, and the alphabetic components lexically.  The following\n    are all valid version numbers, in no particular order:\n\n        1.5.1\n        1.5.2b2\n        161\n        3.10a\n        8.02\n        3.4j\n        1996.07.12\n        3.2.pl0\n        3.1.1.6\n        2g6\n        11g\n        0.960923\n        2.2beta29\n        1.13++\n        5.5.kw\n        2.0b1pl0\n\n    In fact, there is no such thing as an invalid version number under\n    this scheme; the rules for comparison are simple and predictable,\n    but may not always give the results you want (for some definition\n    of "want").\n    '
    component_re = re.compile("(\\d+ | [a-z]+ | \\.)", re.VERBOSE)

    def __init__(self, vstring=None):
        if vstring:
            self.parse(vstring)

    def parse(self, vstring):
        self.vstring = vstring
        components = [x for x in self.component_re.split(vstring) if (x and (x != "."))]
        for (i, obj) in enumerate(components):
            try:
                components[i] = int(obj)
            except ValueError:
                pass
        self.version = components

    def __str__(self):
        return self.vstring

    def __repr__(self):
        return "LooseVersion ('%s')" % str(self)

    def _cmp(self, other):
        if isinstance(other, str):
            other = LooseVersion(other)
        elif not isinstance(other, LooseVersion):
            return NotImplemented
        if self.version == other.version:
            return 0
        if self.version < other.version:
            return -1
        if self.version > other.version:
            return 1
