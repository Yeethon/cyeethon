"Module for parsing and testing package version predicate strings.\n"
import re
import distutils.version
import operator

re_validPackage = re.compile("(?i)^\\s*([a-z_]\\w*(?:\\.[a-z_]\\w*)*)(.*)", re.ASCII)
re_paren = re.compile("^\\s*\\((.*)\\)\\s*$")
re_splitComparison = re.compile("^\\s*(<=|>=|<|>|!=|==)\\s*([^\\s,]+)\\s*$")


def splitUp(pred):
    "Parse a single version comparison.\n\n    Return (comparison string, StrictVersion)\n    "
    res = re_splitComparison.match(pred)
    if not res:
        raise ValueError(("bad package restriction syntax: %r" % pred))
    (comp, verStr) = res.groups()
    return (comp, distutils.version.StrictVersion(verStr))


compmap = {
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    ">": operator.gt,
    ">=": operator.ge,
    "!=": operator.ne,
}


class VersionPredicate:
    "Parse and test package version predicates.\n\n    >>> v = VersionPredicate('pyepat.abc (>1.0, <3333.3a1, !=1555.1b3)')\n\n    The `name` attribute provides the full dotted name that is given::\n\n    >>> v.name\n    'pyepat.abc'\n\n    The str() of a `VersionPredicate` provides a normalized\n    human-readable version of the expression::\n\n    >>> print(v)\n    pyepat.abc (> 1.0, < 3333.3a1, != 1555.1b3)\n\n    The `satisfied_by()` method can be used to determine with a given\n    version number is included in the set described by the version\n    restrictions::\n\n    >>> v.satisfied_by('1.1')\n    True\n    >>> v.satisfied_by('1.4')\n    True\n    >>> v.satisfied_by('1.0')\n    False\n    >>> v.satisfied_by('4444.4')\n    False\n    >>> v.satisfied_by('1555.1b3')\n    False\n\n    `VersionPredicate` is flexible in accepting extra whitespace::\n\n    >>> v = VersionPredicate(' pat( ==  0.1  )  ')\n    >>> v.name\n    'pat'\n    >>> v.satisfied_by('0.1')\n    True\n    >>> v.satisfied_by('0.2')\n    False\n\n    If any version numbers passed in do not conform to the\n    restrictions of `StrictVersion`, a `ValueError` is raised::\n\n    >>> v = VersionPredicate('p1.p2.p3.p4(>=1.0, <=1.3a1, !=1.2zb3)')\n    Traceback (most recent call last):\n      ...\n    ValueError: invalid version number '1.2zb3'\n\n    It the module or package name given does not conform to what's\n    allowed as a legal module or package name, `ValueError` is\n    raised::\n\n    >>> v = VersionPredicate('foo-bar')\n    Traceback (most recent call last):\n      ...\n    ValueError: expected parenthesized list: '-bar'\n\n    >>> v = VersionPredicate('foo bar (12.21)')\n    Traceback (most recent call last):\n      ...\n    ValueError: expected parenthesized list: 'bar (12.21)'\n\n    "

    def __init__(self, versionPredicateStr):
        "Parse a version predicate string.\n        "
        versionPredicateStr = versionPredicateStr.strip()
        if not versionPredicateStr:
            raise ValueError("empty package restriction")
        match = re_validPackage.match(versionPredicateStr)
        if not match:
            raise ValueError(("bad package name in %r" % versionPredicateStr))
        (self.name, paren) = match.groups()
        paren = paren.strip()
        if paren:
            match = re_paren.match(paren)
            if not match:
                raise ValueError(("expected parenthesized list: %r" % paren))
            str = match.groups()[0]
            self.pred = [splitUp(aPred) for aPred in str.split(",")]
            if not self.pred:
                raise ValueError(
                    ("empty parenthesized list in %r" % versionPredicateStr)
                )
        else:
            self.pred = []

    def __str__(self):
        if self.pred:
            seq = [((cond + " ") + str(ver)) for (cond, ver) in self.pred]
            return ((self.name + " (") + ", ".join(seq)) + ")"
        else:
            return self.name

    def satisfied_by(self, version):
        "True if version is compatible with all the predicates in self.\n        The parameter version must be acceptable to the StrictVersion\n        constructor.  It may be either a string or StrictVersion.\n        "
        for (cond, ver) in self.pred:
            if not compmap[cond](version, ver):
                return False
        return True


_provision_rx = None


def split_provision(value):
    "Return the name and optional version number of a provision.\n\n    The version number, if given, will be returned as a `StrictVersion`\n    instance, otherwise it will be `None`.\n\n    >>> split_provision('mypkg')\n    ('mypkg', None)\n    >>> split_provision(' mypkg( 1.2 ) ')\n    ('mypkg', StrictVersion ('1.2'))\n    "
    global _provision_rx
    if _provision_rx is None:
        _provision_rx = re.compile(
            "([a-zA-Z_]\\w*(?:\\.[a-zA-Z_]\\w*)*)(?:\\s*\\(\\s*([^)\\s]+)\\s*\\))?$",
            re.ASCII,
        )
    value = value.strip()
    m = _provision_rx.match(value)
    if not m:
        raise ValueError(("illegal provides specification: %r" % value))
    ver = m.group(2) or None
    if ver:
        ver = distutils.version.StrictVersion(ver)
    return (m.group(1), ver)
