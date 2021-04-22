'Module doctest -- a framework for running examples in docstrings.\n\nIn simplest use, end each module M to be tested with:\n\ndef _test():\n    import doctest\n    doctest.testmod()\n\nif __name__ == "__main__":\n    _test()\n\nThen running the module as a script will cause the examples in the\ndocstrings to get executed and verified:\n\npython M.py\n\nThis won\'t display anything unless an example fails, in which case the\nfailing example(s) and the cause(s) of the failure(s) are printed to stdout\n(why not stderr? because stderr is a lame hack <0.2 wink>), and the final\nline of output is "Test failed.".\n\nRun it with the -v switch instead:\n\npython M.py -v\n\nand a detailed report of all examples tried is printed to stdout, along\nwith assorted summaries at the end.\n\nYou can force verbose mode by passing "verbose=True" to testmod, or prohibit\nit by passing "verbose=False".  In either of those cases, sys.argv is not\nexamined by testmod.\n\nThere are a variety of other ways to run doctests, including integration\nwith the unittest framework, and support for running non-Python text\nfiles containing doctests.  There are also many ways to override parts\nof doctest\'s default behaviors.  See the Library Reference Manual for\ndetails.\n'
__docformat__ = "reStructuredText en"
__all__ = [
    "register_optionflag",
    "DONT_ACCEPT_TRUE_FOR_1",
    "DONT_ACCEPT_BLANKLINE",
    "NORMALIZE_WHITESPACE",
    "ELLIPSIS",
    "SKIP",
    "IGNORE_EXCEPTION_DETAIL",
    "COMPARISON_FLAGS",
    "REPORT_UDIFF",
    "REPORT_CDIFF",
    "REPORT_NDIFF",
    "REPORT_ONLY_FIRST_FAILURE",
    "REPORTING_FLAGS",
    "FAIL_FAST",
    "Example",
    "DocTest",
    "DocTestParser",
    "DocTestFinder",
    "DocTestRunner",
    "OutputChecker",
    "DocTestFailure",
    "UnexpectedException",
    "DebugRunner",
    "testmod",
    "testfile",
    "run_docstring_examples",
    "DocTestSuite",
    "DocFileSuite",
    "set_unittest_reportflags",
    "script_from_examples",
    "testsource",
    "debug_src",
    "debug",
]
import __future__
import difflib
import inspect
import linecache
import os
import pdb
import re
import sys
import traceback
import unittest
from io import StringIO, IncrementalNewlineDecoder
from collections import namedtuple

TestResults = namedtuple("TestResults", "failed attempted")
OPTIONFLAGS_BY_NAME = {}


def register_optionflag(name):
    return OPTIONFLAGS_BY_NAME.setdefault(name, (1 << len(OPTIONFLAGS_BY_NAME)))


DONT_ACCEPT_TRUE_FOR_1 = register_optionflag("DONT_ACCEPT_TRUE_FOR_1")
DONT_ACCEPT_BLANKLINE = register_optionflag("DONT_ACCEPT_BLANKLINE")
NORMALIZE_WHITESPACE = register_optionflag("NORMALIZE_WHITESPACE")
ELLIPSIS = register_optionflag("ELLIPSIS")
SKIP = register_optionflag("SKIP")
IGNORE_EXCEPTION_DETAIL = register_optionflag("IGNORE_EXCEPTION_DETAIL")
COMPARISON_FLAGS = (
    (
        ((DONT_ACCEPT_TRUE_FOR_1 | DONT_ACCEPT_BLANKLINE) | NORMALIZE_WHITESPACE)
        | ELLIPSIS
    )
    | SKIP
) | IGNORE_EXCEPTION_DETAIL
REPORT_UDIFF = register_optionflag("REPORT_UDIFF")
REPORT_CDIFF = register_optionflag("REPORT_CDIFF")
REPORT_NDIFF = register_optionflag("REPORT_NDIFF")
REPORT_ONLY_FIRST_FAILURE = register_optionflag("REPORT_ONLY_FIRST_FAILURE")
FAIL_FAST = register_optionflag("FAIL_FAST")
REPORTING_FLAGS = (
    ((REPORT_UDIFF | REPORT_CDIFF) | REPORT_NDIFF) | REPORT_ONLY_FIRST_FAILURE
) | FAIL_FAST
BLANKLINE_MARKER = "<BLANKLINE>"
ELLIPSIS_MARKER = "..."


def _extract_future_flags(globs):
    "\n    Return the compiler-flags associated with the future features that\n    have been imported into the given namespace (globs).\n    "
    flags = 0
    for fname in __future__.all_feature_names:
        feature = globs.get(fname, None)
        if feature is getattr(__future__, fname):
            flags |= feature.compiler_flag
    return flags


def _normalize_module(module, depth=2):
    "\n    Return the module specified by `module`.  In particular:\n      - If `module` is a module, then return module.\n      - If `module` is a string, then import and return the\n        module with that name.\n      - If `module` is None, then return the calling module.\n        The calling module is assumed to be the module of\n        the stack frame at the given depth in the call stack.\n    "
    if inspect.ismodule(module):
        return module
    elif isinstance(module, str):
        return __import__(module, globals(), locals(), ["*"])
    elif module is None:
        return sys.modules[sys._getframe(depth).f_globals["__name__"]]
    else:
        raise TypeError("Expected a module, string, or None")


def _newline_convert(data):
    return IncrementalNewlineDecoder(None, True).decode(data, True)


def _load_testfile(filename, package, module_relative, encoding):
    if module_relative:
        package = _normalize_module(package, 3)
        filename = _module_relative_path(package, filename)
        if (loader := getattr(package, "__loader__", None)) is None:
            try:
                loader = package.__spec__.loader
            except AttributeError:
                pass
        if hasattr(loader, "get_data"):
            file_contents = loader.get_data(filename)
            file_contents = file_contents.decode(encoding)
            return (_newline_convert(file_contents), filename)
    with open(filename, encoding=encoding) as f:
        return (f.read(), filename)


def _indent(s, indent=4):
    "\n    Add the given number of space characters to the beginning of\n    every non-blank line in `s`, and return the result.\n    "
    return re.sub("(?m)^(?!$)", (indent * " "), s)


def _exception_traceback(exc_info):
    "\n    Return a string containing a traceback message for the given\n    exc_info tuple (as returned by sys.exc_info()).\n    "
    excout = StringIO()
    (exc_type, exc_val, exc_tb) = exc_info
    traceback.print_exception(exc_type, exc_val, exc_tb, file=excout)
    return excout.getvalue()


class _SpoofOut(StringIO):
    def getvalue(self):
        result = StringIO.getvalue(self)
        if result and (not result.endswith("\n")):
            result += "\n"
        return result

    def truncate(self, size=None):
        self.seek(size)
        StringIO.truncate(self)


def _ellipsis_match(want, got):
    "\n    Essentially the only subtle case:\n    >>> _ellipsis_match('aa...aa', 'aaa')\n    False\n    "
    if ELLIPSIS_MARKER not in want:
        return want == got
    ws = want.split(ELLIPSIS_MARKER)
    assert len(ws) >= 2
    (startpos, endpos) = (0, len(got))
    w = ws[0]
    if w:
        if got.startswith(w):
            startpos = len(w)
            del ws[0]
        else:
            return False
    w = ws[(-1)]
    if w:
        if got.endswith(w):
            endpos -= len(w)
            del ws[(-1)]
        else:
            return False
    if startpos > endpos:
        return False
    for w in ws:
        startpos = got.find(w, startpos, endpos)
        if startpos < 0:
            return False
        startpos += len(w)
    return True


def _comment_line(line):
    "Return a commented form of the given line"
    line = line.rstrip()
    if line:
        return "# " + line
    else:
        return "#"


def _strip_exception_details(msg):
    (start, end) = (0, len(msg))
    i = msg.find("\n")
    if i >= 0:
        end = i
    i = msg.find(":", 0, end)
    if i >= 0:
        end = i
    i = msg.rfind(".", 0, end)
    if i >= 0:
        start = i + 1
    return msg[start:end]


class _OutputRedirectingPdb(pdb.Pdb):
    "\n    A specialized version of the python debugger that redirects stdout\n    to a given stream when interacting with the user.  Stdout is *not*\n    redirected when traced code is executed.\n    "

    def __init__(self, out):
        self.__out = out
        self.__debugger_used = False
        pdb.Pdb.__init__(self, stdout=out, nosigint=True)
        self.use_rawinput = 1

    def set_trace(self, frame=None):
        self.__debugger_used = True
        if frame is None:
            frame = sys._getframe().f_back
        pdb.Pdb.set_trace(self, frame)

    def set_continue(self):
        if self.__debugger_used:
            pdb.Pdb.set_continue(self)

    def trace_dispatch(self, *args):
        save_stdout = sys.stdout
        sys.stdout = self.__out
        try:
            return pdb.Pdb.trace_dispatch(self, *args)
        finally:
            sys.stdout = save_stdout


def _module_relative_path(module, test_path):
    if not inspect.ismodule(module):
        raise TypeError(("Expected a module: %r" % module))
    if test_path.startswith("/"):
        raise ValueError("Module-relative files may not have absolute paths")
    test_path = os.path.join(*test_path.split("/"))
    if hasattr(module, "__file__"):
        basedir = os.path.split(module.__file__)[0]
    elif module.__name__ == "__main__":
        if (len(sys.argv) > 0) and (sys.argv[0] != ""):
            basedir = os.path.split(sys.argv[0])[0]
        else:
            basedir = os.curdir
    else:
        if hasattr(module, "__path__"):
            for directory in module.__path__:
                fullpath = os.path.join(directory, test_path)
                if os.path.exists(fullpath):
                    return fullpath
        raise ValueError(
            (
                "Can't resolve paths relative to the module %r (it has no __file__)"
                % module.__name__
            )
        )
    return os.path.join(basedir, test_path)


class Example:
    "\n    A single doctest example, consisting of source code and expected\n    output.  `Example` defines the following attributes:\n\n      - source: A single Python statement, always ending with a newline.\n        The constructor adds a newline if needed.\n\n      - want: The expected output from running the source code (either\n        from stdout, or a traceback in case of exception).  `want` ends\n        with a newline unless it's empty, in which case it's an empty\n        string.  The constructor adds a newline if needed.\n\n      - exc_msg: The exception message generated by the example, if\n        the example is expected to generate an exception; or `None` if\n        it is not expected to generate an exception.  This exception\n        message is compared against the return value of\n        `traceback.format_exception_only()`.  `exc_msg` ends with a\n        newline unless it's `None`.  The constructor adds a newline\n        if needed.\n\n      - lineno: The line number within the DocTest string containing\n        this Example where the Example begins.  This line number is\n        zero-based, with respect to the beginning of the DocTest.\n\n      - indent: The example's indentation in the DocTest string.\n        I.e., the number of space characters that precede the\n        example's first prompt.\n\n      - options: A dictionary mapping from option flags to True or\n        False, which is used to override default options for this\n        example.  Any option flags not contained in this dictionary\n        are left at their default value (as specified by the\n        DocTestRunner's optionflags).  By default, no options are set.\n    "

    def __init__(self, source, want, exc_msg=None, lineno=0, indent=0, options=None):
        if not source.endswith("\n"):
            source += "\n"
        if want and (not want.endswith("\n")):
            want += "\n"
        if (exc_msg is not None) and (not exc_msg.endswith("\n")):
            exc_msg += "\n"
        self.source = source
        self.want = want
        self.lineno = lineno
        self.indent = indent
        if options is None:
            options = {}
        self.options = options
        self.exc_msg = exc_msg

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (
            (self.source == other.source)
            and (self.want == other.want)
            and (self.lineno == other.lineno)
            and (self.indent == other.indent)
            and (self.options == other.options)
            and (self.exc_msg == other.exc_msg)
        )

    def __hash__(self):
        return hash((self.source, self.want, self.lineno, self.indent, self.exc_msg))


class DocTest:
    "\n    A collection of doctest examples that should be run in a single\n    namespace.  Each `DocTest` defines the following attributes:\n\n      - examples: the list of examples.\n\n      - globs: The namespace (aka globals) that the examples should\n        be run in.\n\n      - name: A name identifying the DocTest (typically, the name of\n        the object whose docstring this DocTest was extracted from).\n\n      - filename: The name of the file that this DocTest was extracted\n        from, or `None` if the filename is unknown.\n\n      - lineno: The line number within filename where this DocTest\n        begins, or `None` if the line number is unavailable.  This\n        line number is zero-based, with respect to the beginning of\n        the file.\n\n      - docstring: The string that the examples were extracted from,\n        or `None` if the string is unavailable.\n    "

    def __init__(self, examples, globs, name, filename, lineno, docstring):
        "\n        Create a new DocTest containing the given examples.  The\n        DocTest's globals are initialized with a copy of `globs`.\n        "
        assert not isinstance(
            examples, str
        ), "DocTest no longer accepts str; use DocTestParser instead"
        self.examples = examples
        self.docstring = docstring
        self.globs = globs.copy()
        self.name = name
        self.filename = filename
        self.lineno = lineno

    def __repr__(self):
        if len(self.examples) == 0:
            examples = "no examples"
        elif len(self.examples) == 1:
            examples = "1 example"
        else:
            examples = "%d examples" % len(self.examples)
        return "<%s %s from %s:%s (%s)>" % (
            self.__class__.__name__,
            self.name,
            self.filename,
            self.lineno,
            examples,
        )

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (
            (self.examples == other.examples)
            and (self.docstring == other.docstring)
            and (self.globs == other.globs)
            and (self.name == other.name)
            and (self.filename == other.filename)
            and (self.lineno == other.lineno)
        )

    def __hash__(self):
        return hash((self.docstring, self.name, self.filename, self.lineno))

    def __lt__(self, other):
        if not isinstance(other, DocTest):
            return NotImplemented
        return (self.name, self.filename, self.lineno, id(self)) < (
            other.name,
            other.filename,
            other.lineno,
            id(other),
        )


class DocTestParser:
    "\n    A class used to parse strings containing doctest examples.\n    "
    _EXAMPLE_RE = re.compile(
        "\n        # Source consists of a PS1 line followed by zero or more PS2 lines.\n        (?P<source>\n            (?:^(?P<indent> [ ]*) >>>    .*)    # PS1 line\n            (?:\\n           [ ]*  \\.\\.\\. .*)*)  # PS2 lines\n        \\n?\n        # Want consists of any non-blank lines that do not start with PS1.\n        (?P<want> (?:(?![ ]*$)    # Not a blank line\n                     (?![ ]*>>>)  # Not a line starting with PS1\n                     .+$\\n?       # But any other line\n                  )*)\n        ",
        (re.MULTILINE | re.VERBOSE),
    )
    _EXCEPTION_RE = re.compile(
        "\n        # Grab the traceback header.  Different versions of Python have\n        # said different things on the first traceback line.\n        ^(?P<hdr> Traceback\\ \\(\n            (?: most\\ recent\\ call\\ last\n            |   innermost\\ last\n            ) \\) :\n        )\n        \\s* $                # toss trailing whitespace on the header.\n        (?P<stack> .*?)      # don't blink: absorb stuff until...\n        ^ (?P<msg> \\w+ .*)   #     a line *starts* with alphanum.\n        ",
        ((re.VERBOSE | re.MULTILINE) | re.DOTALL),
    )
    _IS_BLANK_OR_COMMENT = re.compile("^[ ]*(#.*)?$").match

    def parse(self, string, name="<string>"):
        "\n        Divide the given string into examples and intervening text,\n        and return them as a list of alternating Examples and strings.\n        Line numbers for the Examples are 0-based.  The optional\n        argument `name` is a name identifying this string, and is only\n        used for error messages.\n        "
        string = string.expandtabs()
        min_indent = self._min_indent(string)
        if min_indent > 0:
            string = "\n".join([l[min_indent:] for l in string.split("\n")])
        output = []
        (charno, lineno) = (0, 0)
        for m in self._EXAMPLE_RE.finditer(string):
            output.append(string[charno : m.start()])
            lineno += string.count("\n", charno, m.start())
            (source, options, want, exc_msg) = self._parse_example(m, name, lineno)
            if not self._IS_BLANK_OR_COMMENT(source):
                output.append(
                    Example(
                        source,
                        want,
                        exc_msg,
                        lineno=lineno,
                        indent=(min_indent + len(m.group("indent"))),
                        options=options,
                    )
                )
            lineno += string.count("\n", m.start(), m.end())
            charno = m.end()
        output.append(string[charno:])
        return output

    def get_doctest(self, string, globs, name, filename, lineno):
        "\n        Extract all doctest examples from the given string, and\n        collect them into a `DocTest` object.\n\n        `globs`, `name`, `filename`, and `lineno` are attributes for\n        the new `DocTest` object.  See the documentation for `DocTest`\n        for more information.\n        "
        return DocTest(
            self.get_examples(string, name), globs, name, filename, lineno, string
        )

    def get_examples(self, string, name="<string>"):
        '\n        Extract all doctest examples from the given string, and return\n        them as a list of `Example` objects.  Line numbers are\n        0-based, because it\'s most common in doctests that nothing\n        interesting appears on the same line as opening triple-quote,\n        and so the first interesting line is called "line 1" then.\n\n        The optional argument `name` is a name identifying this\n        string, and is only used for error messages.\n        '
        return [x for x in self.parse(string, name) if isinstance(x, Example)]

    def _parse_example(self, m, name, lineno):
        "\n        Given a regular expression match from `_EXAMPLE_RE` (`m`),\n        return a pair `(source, want)`, where `source` is the matched\n        example's source code (with prompts and indentation stripped);\n        and `want` is the example's expected output (with indentation\n        stripped).\n\n        `name` is the string's name, and `lineno` is the line number\n        where the example starts; both are used for error messages.\n        "
        indent = len(m.group("indent"))
        source_lines = m.group("source").split("\n")
        self._check_prompt_blank(source_lines, indent, name, lineno)
        self._check_prefix(source_lines[1:], ((" " * indent) + "."), name, lineno)
        source = "\n".join([sl[(indent + 4) :] for sl in source_lines])
        want = m.group("want")
        want_lines = want.split("\n")
        if (len(want_lines) > 1) and re.match(" *$", want_lines[(-1)]):
            del want_lines[(-1)]
        self._check_prefix(
            want_lines, (" " * indent), name, (lineno + len(source_lines))
        )
        want = "\n".join([wl[indent:] for wl in want_lines])
        m = self._EXCEPTION_RE.match(want)
        if m:
            exc_msg = m.group("msg")
        else:
            exc_msg = None
        options = self._find_options(source, name, lineno)
        return (source, options, want, exc_msg)

    _OPTION_DIRECTIVE_RE = re.compile("#\\s*doctest:\\s*([^\\n\\'\"]*)$", re.MULTILINE)

    def _find_options(self, source, name, lineno):
        "\n        Return a dictionary containing option overrides extracted from\n        option directives in the given source string.\n\n        `name` is the string's name, and `lineno` is the line number\n        where the example starts; both are used for error messages.\n        "
        options = {}
        for m in self._OPTION_DIRECTIVE_RE.finditer(source):
            option_strings = m.group(1).replace(",", " ").split()
            for option in option_strings:
                if (option[0] not in "+-") or (option[1:] not in OPTIONFLAGS_BY_NAME):
                    raise ValueError(
                        (
                            "line %r of the doctest for %s has an invalid option: %r"
                            % ((lineno + 1), name, option)
                        )
                    )
                flag = OPTIONFLAGS_BY_NAME[option[1:]]
                options[flag] = option[0] == "+"
        if options and self._IS_BLANK_OR_COMMENT(source):
            raise ValueError(
                (
                    "line %r of the doctest for %s has an option directive on a line with no example: %r"
                    % (lineno, name, source)
                )
            )
        return options

    _INDENT_RE = re.compile("^([ ]*)(?=\\S)", re.MULTILINE)

    def _min_indent(self, s):
        "Return the minimum indentation of any non-blank line in `s`"
        indents = [len(indent) for indent in self._INDENT_RE.findall(s)]
        if len(indents) > 0:
            return min(indents)
        else:
            return 0

    def _check_prompt_blank(self, lines, indent, name, lineno):
        "\n        Given the lines of a source string (including prompts and\n        leading indentation), check to make sure that every prompt is\n        followed by a space character.  If any line is not followed by\n        a space character, then raise ValueError.\n        "
        for (i, line) in enumerate(lines):
            if (len(line) >= (indent + 4)) and (line[(indent + 3)] != " "):
                raise ValueError(
                    (
                        "line %r of the docstring for %s lacks blank after %s: %r"
                        % (((lineno + i) + 1), name, line[indent : (indent + 3)], line)
                    )
                )

    def _check_prefix(self, lines, prefix, name, lineno):
        "\n        Check that every line in the given list starts with the given\n        prefix; if any line does not, then raise a ValueError.\n        "
        for (i, line) in enumerate(lines):
            if line and (not line.startswith(prefix)):
                raise ValueError(
                    (
                        "line %r of the docstring for %s has inconsistent leading whitespace: %r"
                        % (((lineno + i) + 1), name, line)
                    )
                )


class DocTestFinder:
    "\n    A class used to extract the DocTests that are relevant to a given\n    object, from its docstring and the docstrings of its contained\n    objects.  Doctests can currently be extracted from the following\n    object types: modules, functions, classes, methods, staticmethods,\n    classmethods, and properties.\n    "

    def __init__(
        self, verbose=False, parser=DocTestParser(), recurse=True, exclude_empty=True
    ):
        "\n        Create a new doctest finder.\n\n        The optional argument `parser` specifies a class or\n        function that should be used to create new DocTest objects (or\n        objects that implement the same interface as DocTest).  The\n        signature for this factory function should match the signature\n        of the DocTest constructor.\n\n        If the optional argument `recurse` is false, then `find` will\n        only examine the given object, and not any contained objects.\n\n        If the optional argument `exclude_empty` is false, then `find`\n        will include tests for objects with empty docstrings.\n        "
        self._parser = parser
        self._verbose = verbose
        self._recurse = recurse
        self._exclude_empty = exclude_empty

    def find(self, obj, name=None, module=None, globs=None, extraglobs=None):
        "\n        Return a list of the DocTests that are defined by the given\n        object's docstring, or by any of its contained objects'\n        docstrings.\n\n        The optional parameter `module` is the module that contains\n        the given object.  If the module is not specified or is None, then\n        the test finder will attempt to automatically determine the\n        correct module.  The object's module is used:\n\n            - As a default namespace, if `globs` is not specified.\n            - To prevent the DocTestFinder from extracting DocTests\n              from objects that are imported from other modules.\n            - To find the name of the file containing the object.\n            - To help find the line number of the object within its\n              file.\n\n        Contained objects whose module does not match `module` are ignored.\n\n        If `module` is False, no attempt to find the module will be made.\n        This is obscure, of use mostly in tests:  if `module` is False, or\n        is None but cannot be found automatically, then all objects are\n        considered to belong to the (non-existent) module, so all contained\n        objects will (recursively) be searched for doctests.\n\n        The globals for each DocTest is formed by combining `globs`\n        and `extraglobs` (bindings in `extraglobs` override bindings\n        in `globs`).  A new copy of the globals dictionary is created\n        for each DocTest.  If `globs` is not specified, then it\n        defaults to the module's `__dict__`, if specified, or {}\n        otherwise.  If `extraglobs` is not specified, then it defaults\n        to {}.\n\n        "
        if name is None:
            name = getattr(obj, "__name__", None)
            if name is None:
                raise ValueError(
                    (
                        "DocTestFinder.find: name must be given when obj.__name__ doesn't exist: %r"
                        % (type(obj),)
                    )
                )
        if module is False:
            module = None
        elif module is None:
            module = inspect.getmodule(obj)
        try:
            file = inspect.getsourcefile(obj)
        except TypeError:
            source_lines = None
        else:
            if not file:
                file = inspect.getfile(obj)
                if not ((file[0] + file[(-2):]) == "<]>"):
                    file = None
            if file is None:
                source_lines = None
            else:
                if module is not None:
                    source_lines = linecache.getlines(file, module.__dict__)
                else:
                    source_lines = linecache.getlines(file)
                if not source_lines:
                    source_lines = None
        if globs is None:
            if module is None:
                globs = {}
            else:
                globs = module.__dict__.copy()
        else:
            globs = globs.copy()
        if extraglobs is not None:
            globs.update(extraglobs)
        if "__name__" not in globs:
            globs["__name__"] = "__main__"
        tests = []
        self._find(tests, obj, name, module, source_lines, globs, {})
        tests.sort()
        return tests

    def _from_module(self, module, object):
        "\n        Return true if the given object is defined in the given\n        module.\n        "
        if module is None:
            return True
        elif inspect.getmodule(object) is not None:
            return module is inspect.getmodule(object)
        elif inspect.isfunction(object):
            return module.__dict__ is object.__globals__
        elif inspect.ismethoddescriptor(object):
            if hasattr(object, "__objclass__"):
                obj_mod = object.__objclass__.__module__
            elif hasattr(object, "__module__"):
                obj_mod = object.__module__
            else:
                return True
            return module.__name__ == obj_mod
        elif inspect.isclass(object):
            return module.__name__ == object.__module__
        elif hasattr(object, "__module__"):
            return module.__name__ == object.__module__
        elif isinstance(object, property):
            return True
        else:
            raise ValueError("object must be a class or function")

    def _find(self, tests, obj, name, module, source_lines, globs, seen):
        "\n        Find tests for the given object and any contained objects, and\n        add them to `tests`.\n        "
        if self._verbose:
            print(("Finding tests in %s" % name))
        if id(obj) in seen:
            return
        seen[id(obj)] = 1
        test = self._get_test(obj, name, module, globs, source_lines)
        if test is not None:
            tests.append(test)
        if inspect.ismodule(obj) and self._recurse:
            for (valname, val) in obj.__dict__.items():
                valname = "%s.%s" % (name, valname)
                if (
                    inspect.isroutine(inspect.unwrap(val)) or inspect.isclass(val)
                ) and self._from_module(module, val):
                    self._find(tests, val, valname, module, source_lines, globs, seen)
        if inspect.ismodule(obj) and self._recurse:
            for (valname, val) in getattr(obj, "__test__", {}).items():
                if not isinstance(valname, str):
                    raise ValueError(
                        (
                            "DocTestFinder.find: __test__ keys must be strings: %r"
                            % (type(valname),)
                        )
                    )
                if not (
                    inspect.isroutine(val)
                    or inspect.isclass(val)
                    or inspect.ismodule(val)
                    or isinstance(val, str)
                ):
                    raise ValueError(
                        (
                            "DocTestFinder.find: __test__ values must be strings, functions, methods, classes, or modules: %r"
                            % (type(val),)
                        )
                    )
                valname = "%s.__test__.%s" % (name, valname)
                self._find(tests, val, valname, module, source_lines, globs, seen)
        if inspect.isclass(obj) and self._recurse:
            for (valname, val) in obj.__dict__.items():
                if isinstance(val, staticmethod):
                    val = getattr(obj, valname)
                if isinstance(val, classmethod):
                    val = getattr(obj, valname).__func__
                if (
                    inspect.isroutine(val)
                    or inspect.isclass(val)
                    or isinstance(val, property)
                ) and self._from_module(module, val):
                    valname = "%s.%s" % (name, valname)
                    self._find(tests, val, valname, module, source_lines, globs, seen)

    def _get_test(self, obj, name, module, globs, source_lines):
        "\n        Return a DocTest for the given object, if it defines a docstring;\n        otherwise, return None.\n        "
        if isinstance(obj, str):
            docstring = obj
        else:
            try:
                if obj.__doc__ is None:
                    docstring = ""
                else:
                    docstring = obj.__doc__
                    if not isinstance(docstring, str):
                        docstring = str(docstring)
            except (TypeError, AttributeError):
                docstring = ""
        lineno = self._find_lineno(obj, source_lines)
        if self._exclude_empty and (not docstring):
            return None
        if module is None:
            filename = None
        else:
            filename = getattr(module, "__file__", None) or module.__name__
            if filename[(-4):] == ".pyc":
                filename = filename[:(-1)]
        return self._parser.get_doctest(docstring, globs, name, filename, lineno)

    def _find_lineno(self, obj, source_lines):
        "\n        Return a line number of the given object's docstring.  Note:\n        this method assumes that the object has a docstring.\n        "
        lineno = None
        if inspect.ismodule(obj):
            lineno = 0
        if inspect.isclass(obj):
            if source_lines is None:
                return None
            pat = re.compile(("^\\s*class\\s*%s\\b" % getattr(obj, "__name__", "-")))
            for (i, line) in enumerate(source_lines):
                if pat.match(line):
                    lineno = i
                    break
        if inspect.ismethod(obj):
            obj = obj.__func__
        if inspect.isfunction(obj):
            obj = obj.__code__
        if inspect.istraceback(obj):
            obj = obj.tb_frame
        if inspect.isframe(obj):
            obj = obj.f_code
        if inspect.iscode(obj):
            lineno = getattr(obj, "co_firstlineno", None) - 1
        if lineno is not None:
            if source_lines is None:
                return lineno + 1
            pat = re.compile("(^|.*:)\\s*\\w*(\"|\\')")
            for lineno in range(lineno, len(source_lines)):
                if pat.match(source_lines[lineno]):
                    return lineno
        return None


class DocTestRunner:
    "\n    A class used to run DocTest test cases, and accumulate statistics.\n    The `run` method is used to process a single DocTest case.  It\n    returns a tuple `(f, t)`, where `t` is the number of test cases\n    tried, and `f` is the number of test cases that failed.\n\n        >>> tests = DocTestFinder().find(_TestClass)\n        >>> runner = DocTestRunner(verbose=False)\n        >>> tests.sort(key = lambda test: test.name)\n        >>> for test in tests:\n        ...     print(test.name, '->', runner.run(test))\n        _TestClass -> TestResults(failed=0, attempted=2)\n        _TestClass.__init__ -> TestResults(failed=0, attempted=2)\n        _TestClass.get -> TestResults(failed=0, attempted=2)\n        _TestClass.square -> TestResults(failed=0, attempted=1)\n\n    The `summarize` method prints a summary of all the test cases that\n    have been run by the runner, and returns an aggregated `(f, t)`\n    tuple:\n\n        >>> runner.summarize(verbose=1)\n        4 items passed all tests:\n           2 tests in _TestClass\n           2 tests in _TestClass.__init__\n           2 tests in _TestClass.get\n           1 tests in _TestClass.square\n        7 tests in 4 items.\n        7 passed and 0 failed.\n        Test passed.\n        TestResults(failed=0, attempted=7)\n\n    The aggregated number of tried examples and failed examples is\n    also available via the `tries` and `failures` attributes:\n\n        >>> runner.tries\n        7\n        >>> runner.failures\n        0\n\n    The comparison between expected outputs and actual outputs is done\n    by an `OutputChecker`.  This comparison may be customized with a\n    number of option flags; see the documentation for `testmod` for\n    more information.  If the option flags are insufficient, then the\n    comparison may also be customized by passing a subclass of\n    `OutputChecker` to the constructor.\n\n    The test runner's display output can be controlled in two ways.\n    First, an output function (`out) can be passed to\n    `TestRunner.run`; this function will be called with strings that\n    should be displayed.  It defaults to `sys.stdout.write`.  If\n    capturing the output is not sufficient, then the display output\n    can be also customized by subclassing DocTestRunner, and\n    overriding the methods `report_start`, `report_success`,\n    `report_unexpected_exception`, and `report_failure`.\n    "
    DIVIDER = "*" * 70

    def __init__(self, checker=None, verbose=None, optionflags=0):
        "\n        Create a new test runner.\n\n        Optional keyword arg `checker` is the `OutputChecker` that\n        should be used to compare the expected outputs and actual\n        outputs of doctest examples.\n\n        Optional keyword arg 'verbose' prints lots of stuff if true,\n        only failures if false; by default, it's true iff '-v' is in\n        sys.argv.\n\n        Optional argument `optionflags` can be used to control how the\n        test runner compares expected output to actual output, and how\n        it displays failures.  See the documentation for `testmod` for\n        more information.\n        "
        self._checker = checker or OutputChecker()
        if verbose is None:
            verbose = "-v" in sys.argv
        self._verbose = verbose
        self.optionflags = optionflags
        self.original_optionflags = optionflags
        self.tries = 0
        self.failures = 0
        self._name2ft = {}
        self._fakeout = _SpoofOut()

    def report_start(self, out, test, example):
        "\n        Report that the test runner is about to process the given\n        example.  (Only displays a message if verbose=True)\n        "
        if self._verbose:
            if example.want:
                out(
                    (
                        (("Trying:\n" + _indent(example.source)) + "Expecting:\n")
                        + _indent(example.want)
                    )
                )
            else:
                out((("Trying:\n" + _indent(example.source)) + "Expecting nothing\n"))

    def report_success(self, out, test, example, got):
        "\n        Report that the given example ran successfully.  (Only\n        displays a message if verbose=True)\n        "
        if self._verbose:
            out("ok\n")

    def report_failure(self, out, test, example, got):
        "\n        Report that the given example failed.\n        "
        out(
            (
                self._failure_header(test, example)
                + self._checker.output_difference(example, got, self.optionflags)
            )
        )

    def report_unexpected_exception(self, out, test, example, exc_info):
        "\n        Report that the given example raised an unexpected exception.\n        "
        out(
            (
                (self._failure_header(test, example) + "Exception raised:\n")
                + _indent(_exception_traceback(exc_info))
            )
        )

    def _failure_header(self, test, example):
        out = [self.DIVIDER]
        if test.filename:
            if (test.lineno is not None) and (example.lineno is not None):
                lineno = (test.lineno + example.lineno) + 1
            else:
                lineno = "?"
            out.append(
                ('File "%s", line %s, in %s' % (test.filename, lineno, test.name))
            )
        else:
            out.append(("Line %s, in %s" % ((example.lineno + 1), test.name)))
        out.append("Failed example:")
        source = example.source
        out.append(_indent(source))
        return "\n".join(out)

    def __run(self, test, compileflags, out):
        "\n        Run the examples in `test`.  Write the outcome of each example\n        with one of the `DocTestRunner.report_*` methods, using the\n        writer function `out`.  `compileflags` is the set of compiler\n        flags that should be used to execute examples.  Return a tuple\n        `(f, t)`, where `t` is the number of examples tried, and `f`\n        is the number of examples that failed.  The examples are run\n        in the namespace `test.globs`.\n        "
        failures = tries = 0
        original_optionflags = self.optionflags
        (SUCCESS, FAILURE, BOOM) = range(3)
        check = self._checker.check_output
        for (examplenum, example) in enumerate(test.examples):
            quiet = (self.optionflags & REPORT_ONLY_FIRST_FAILURE) and (failures > 0)
            self.optionflags = original_optionflags
            if example.options:
                for (optionflag, val) in example.options.items():
                    if val:
                        self.optionflags |= optionflag
                    else:
                        self.optionflags &= ~optionflag
            if self.optionflags & SKIP:
                continue
            tries += 1
            if not quiet:
                self.report_start(out, test, example)
            filename = "<doctest %s[%d]>" % (test.name, examplenum)
            try:
                exec(
                    compile(example.source, filename, "single", compileflags, True),
                    test.globs,
                )
                self.debugger.set_continue()
                exception = None
            except KeyboardInterrupt:
                raise
            except:
                exception = sys.exc_info()
                self.debugger.set_continue()
            got = self._fakeout.getvalue()
            self._fakeout.truncate(0)
            outcome = FAILURE
            if exception is None:
                if check(example.want, got, self.optionflags):
                    outcome = SUCCESS
            else:
                exc_msg = traceback.format_exception_only(*exception[:2])[(-1)]
                if not quiet:
                    got += _exception_traceback(exception)
                if example.exc_msg is None:
                    outcome = BOOM
                elif check(example.exc_msg, exc_msg, self.optionflags):
                    outcome = SUCCESS
                elif self.optionflags & IGNORE_EXCEPTION_DETAIL:
                    if check(
                        _strip_exception_details(example.exc_msg),
                        _strip_exception_details(exc_msg),
                        self.optionflags,
                    ):
                        outcome = SUCCESS
            if outcome is SUCCESS:
                if not quiet:
                    self.report_success(out, test, example, got)
            elif outcome is FAILURE:
                if not quiet:
                    self.report_failure(out, test, example, got)
                failures += 1
            elif outcome is BOOM:
                if not quiet:
                    self.report_unexpected_exception(out, test, example, exception)
                failures += 1
            else:
                assert False, ("unknown outcome", outcome)
            if failures and (self.optionflags & FAIL_FAST):
                break
        self.optionflags = original_optionflags
        self.__record_outcome(test, failures, tries)
        return TestResults(failures, tries)

    def __record_outcome(self, test, f, t):
        "\n        Record the fact that the given DocTest (`test`) generated `f`\n        failures out of `t` tried examples.\n        "
        (f2, t2) = self._name2ft.get(test.name, (0, 0))
        self._name2ft[test.name] = ((f + f2), (t + t2))
        self.failures += f
        self.tries += t

    __LINECACHE_FILENAME_RE = re.compile(
        "<doctest (?P<name>.+)\\[(?P<examplenum>\\d+)\\]>$"
    )

    def __patched_linecache_getlines(self, filename, module_globals=None):
        m = self.__LINECACHE_FILENAME_RE.match(filename)
        if m and (m.group("name") == self.test.name):
            example = self.test.examples[int(m.group("examplenum"))]
            return example.source.splitlines(keepends=True)
        else:
            return self.save_linecache_getlines(filename, module_globals)

    def run(self, test, compileflags=None, out=None, clear_globs=True):
        "\n        Run the examples in `test`, and display the results using the\n        writer function `out`.\n\n        The examples are run in the namespace `test.globs`.  If\n        `clear_globs` is true (the default), then this namespace will\n        be cleared after the test runs, to help with garbage\n        collection.  If you would like to examine the namespace after\n        the test completes, then use `clear_globs=False`.\n\n        `compileflags` gives the set of flags that should be used by\n        the Python compiler when running the examples.  If not\n        specified, then it will default to the set of future-import\n        flags that apply to `globs`.\n\n        The output of each example is checked using\n        `DocTestRunner.check_output`, and the results are formatted by\n        the `DocTestRunner.report_*` methods.\n        "
        self.test = test
        if compileflags is None:
            compileflags = _extract_future_flags(test.globs)
        save_stdout = sys.stdout
        if out is None:
            encoding = save_stdout.encoding
            if (encoding is None) or (encoding.lower() == "utf-8"):
                out = save_stdout.write
            else:

                def out(s):
                    s = str(s.encode(encoding, "backslashreplace"), encoding)
                    save_stdout.write(s)

        sys.stdout = self._fakeout
        save_trace = sys.gettrace()
        save_set_trace = pdb.set_trace
        self.debugger = _OutputRedirectingPdb(save_stdout)
        self.debugger.reset()
        pdb.set_trace = self.debugger.set_trace
        self.save_linecache_getlines = linecache.getlines
        linecache.getlines = self.__patched_linecache_getlines
        save_displayhook = sys.displayhook
        sys.displayhook = sys.__displayhook__
        try:
            return self.__run(test, compileflags, out)
        finally:
            sys.stdout = save_stdout
            pdb.set_trace = save_set_trace
            sys.settrace(save_trace)
            linecache.getlines = self.save_linecache_getlines
            sys.displayhook = save_displayhook
            if clear_globs:
                test.globs.clear()
                import builtins

                builtins._ = None

    def summarize(self, verbose=None):
        "\n        Print a summary of all the test cases that have been run by\n        this DocTestRunner, and return a tuple `(f, t)`, where `f` is\n        the total number of failed examples, and `t` is the total\n        number of tried examples.\n\n        The optional `verbose` argument controls how detailed the\n        summary is.  If the verbosity is not specified, then the\n        DocTestRunner's verbosity is used.\n        "
        if verbose is None:
            verbose = self._verbose
        notests = []
        passed = []
        failed = []
        totalt = totalf = 0
        for x in self._name2ft.items():
            (name, (f, t)) = x
            assert f <= t
            totalt += t
            totalf += f
            if t == 0:
                notests.append(name)
            elif f == 0:
                passed.append((name, t))
            else:
                failed.append(x)
        if verbose:
            if notests:
                print(len(notests), "items had no tests:")
                notests.sort()
                for thing in notests:
                    print("   ", thing)
            if passed:
                print(len(passed), "items passed all tests:")
                passed.sort()
                for (thing, count) in passed:
                    print((" %3d tests in %s" % (count, thing)))
        if failed:
            print(self.DIVIDER)
            print(len(failed), "items had failures:")
            failed.sort()
            for (thing, (f, t)) in failed:
                print((" %3d of %3d in %s" % (f, t, thing)))
        if verbose:
            print(totalt, "tests in", len(self._name2ft), "items.")
            print((totalt - totalf), "passed and", totalf, "failed.")
        if totalf:
            print("***Test Failed***", totalf, "failures.")
        elif verbose:
            print("Test passed.")
        return TestResults(totalf, totalt)

    def merge(self, other):
        d = self._name2ft
        for (name, (f, t)) in other._name2ft.items():
            if name in d:
                (f2, t2) = d[name]
                f = f + f2
                t = t + t2
            d[name] = (f, t)


class OutputChecker:
    "\n    A class used to check the whether the actual output from a doctest\n    example matches the expected output.  `OutputChecker` defines two\n    methods: `check_output`, which compares a given pair of outputs,\n    and returns true if they match; and `output_difference`, which\n    returns a string describing the differences between two outputs.\n    "

    def _toAscii(self, s):
        "\n        Convert string to hex-escaped ASCII string.\n        "
        return str(s.encode("ASCII", "backslashreplace"), "ASCII")

    def check_output(self, want, got, optionflags):
        "\n        Return True iff the actual output from an example (`got`)\n        matches the expected output (`want`).  These strings are\n        always considered to match if they are identical; but\n        depending on what option flags the test runner is using,\n        several non-exact match types are also possible.  See the\n        documentation for `TestRunner` for more information about\n        option flags.\n        "
        got = self._toAscii(got)
        want = self._toAscii(want)
        if got == want:
            return True
        if not (optionflags & DONT_ACCEPT_TRUE_FOR_1):
            if (got, want) == ("True\n", "1\n"):
                return True
            if (got, want) == ("False\n", "0\n"):
                return True
        if not (optionflags & DONT_ACCEPT_BLANKLINE):
            want = re.sub(("(?m)^%s\\s*?$" % re.escape(BLANKLINE_MARKER)), "", want)
            got = re.sub("(?m)^[^\\S\\n]+$", "", got)
            if got == want:
                return True
        if optionflags & NORMALIZE_WHITESPACE:
            got = " ".join(got.split())
            want = " ".join(want.split())
            if got == want:
                return True
        if optionflags & ELLIPSIS:
            if _ellipsis_match(want, got):
                return True
        return False

    def _do_a_fancy_diff(self, want, got, optionflags):
        if not (optionflags & ((REPORT_UDIFF | REPORT_CDIFF) | REPORT_NDIFF)):
            return False
        if optionflags & REPORT_NDIFF:
            return True
        return (want.count("\n") > 2) and (got.count("\n") > 2)

    def output_difference(self, example, got, optionflags):
        "\n        Return a string describing the differences between the\n        expected output for a given example (`example`) and the actual\n        output (`got`).  `optionflags` is the set of option flags used\n        to compare `want` and `got`.\n        "
        want = example.want
        if not (optionflags & DONT_ACCEPT_BLANKLINE):
            got = re.sub("(?m)^[ ]*(?=\n)", BLANKLINE_MARKER, got)
        if self._do_a_fancy_diff(want, got, optionflags):
            want_lines = want.splitlines(keepends=True)
            got_lines = got.splitlines(keepends=True)
            if optionflags & REPORT_UDIFF:
                diff = difflib.unified_diff(want_lines, got_lines, n=2)
                diff = list(diff)[2:]
                kind = "unified diff with -expected +actual"
            elif optionflags & REPORT_CDIFF:
                diff = difflib.context_diff(want_lines, got_lines, n=2)
                diff = list(diff)[2:]
                kind = "context diff with expected followed by actual"
            elif optionflags & REPORT_NDIFF:
                engine = difflib.Differ(charjunk=difflib.IS_CHARACTER_JUNK)
                diff = list(engine.compare(want_lines, got_lines))
                kind = "ndiff with -expected +actual"
            else:
                assert 0, "Bad diff option"
            return ("Differences (%s):\n" % kind) + _indent("".join(diff))
        if want and got:
            return "Expected:\n%sGot:\n%s" % (_indent(want), _indent(got))
        elif want:
            return "Expected:\n%sGot nothing\n" % _indent(want)
        elif got:
            return "Expected nothing\nGot:\n%s" % _indent(got)
        else:
            return "Expected nothing\nGot nothing\n"


class DocTestFailure(Exception):
    "A DocTest example has failed in debugging mode.\n\n    The exception instance has variables:\n\n    - test: the DocTest object being run\n\n    - example: the Example object that failed\n\n    - got: the actual output\n    "

    def __init__(self, test, example, got):
        self.test = test
        self.example = example
        self.got = got

    def __str__(self):
        return str(self.test)


class UnexpectedException(Exception):
    "A DocTest example has encountered an unexpected exception\n\n    The exception instance has variables:\n\n    - test: the DocTest object being run\n\n    - example: the Example object that failed\n\n    - exc_info: the exception info\n    "

    def __init__(self, test, example, exc_info):
        self.test = test
        self.example = example
        self.exc_info = exc_info

    def __str__(self):
        return str(self.test)


class DebugRunner(DocTestRunner):
    "Run doc tests but raise an exception as soon as there is a failure.\n\n       If an unexpected exception occurs, an UnexpectedException is raised.\n       It contains the test, the example, and the original exception:\n\n         >>> runner = DebugRunner(verbose=False)\n         >>> test = DocTestParser().get_doctest('>>> raise KeyError\\n42',\n         ...                                    {}, 'foo', 'foo.py', 0)\n         >>> try:\n         ...     runner.run(test)\n         ... except UnexpectedException as f:\n         ...     failure = f\n\n         >>> failure.test is test\n         True\n\n         >>> failure.example.want\n         '42\\n'\n\n         >>> exc_info = failure.exc_info\n         >>> raise exc_info[1] # Already has the traceback\n         Traceback (most recent call last):\n         ...\n         KeyError\n\n       We wrap the original exception to give the calling application\n       access to the test and example information.\n\n       If the output doesn't match, then a DocTestFailure is raised:\n\n         >>> test = DocTestParser().get_doctest('''\n         ...      >>> x = 1\n         ...      >>> x\n         ...      2\n         ...      ''', {}, 'foo', 'foo.py', 0)\n\n         >>> try:\n         ...    runner.run(test)\n         ... except DocTestFailure as f:\n         ...    failure = f\n\n       DocTestFailure objects provide access to the test:\n\n         >>> failure.test is test\n         True\n\n       As well as to the example:\n\n         >>> failure.example.want\n         '2\\n'\n\n       and the actual output:\n\n         >>> failure.got\n         '1\\n'\n\n       If a failure or error occurs, the globals are left intact:\n\n         >>> del test.globs['__builtins__']\n         >>> test.globs\n         {'x': 1}\n\n         >>> test = DocTestParser().get_doctest('''\n         ...      >>> x = 2\n         ...      >>> raise KeyError\n         ...      ''', {}, 'foo', 'foo.py', 0)\n\n         >>> runner.run(test)\n         Traceback (most recent call last):\n         ...\n         doctest.UnexpectedException: <DocTest foo from foo.py:0 (2 examples)>\n\n         >>> del test.globs['__builtins__']\n         >>> test.globs\n         {'x': 2}\n\n       But the globals are cleared if there is no error:\n\n         >>> test = DocTestParser().get_doctest('''\n         ...      >>> x = 2\n         ...      ''', {}, 'foo', 'foo.py', 0)\n\n         >>> runner.run(test)\n         TestResults(failed=0, attempted=1)\n\n         >>> test.globs\n         {}\n\n       "

    def run(self, test, compileflags=None, out=None, clear_globs=True):
        r = DocTestRunner.run(self, test, compileflags, out, False)
        if clear_globs:
            test.globs.clear()
        return r

    def report_unexpected_exception(self, out, test, example, exc_info):
        raise UnexpectedException(test, example, exc_info)

    def report_failure(self, out, test, example, got):
        raise DocTestFailure(test, example, got)


master = None


def testmod(
    m=None,
    name=None,
    globs=None,
    verbose=None,
    report=True,
    optionflags=0,
    extraglobs=None,
    raise_on_error=False,
    exclude_empty=False,
):
    'm=None, name=None, globs=None, verbose=None, report=True,\n       optionflags=0, extraglobs=None, raise_on_error=False,\n       exclude_empty=False\n\n    Test examples in docstrings in functions and classes reachable\n    from module m (or the current module if m is not supplied), starting\n    with m.__doc__.\n\n    Also test examples reachable from dict m.__test__ if it exists and is\n    not None.  m.__test__ maps names to functions, classes and strings;\n    function and class docstrings are tested even if the name is private;\n    strings are tested directly, as if they were docstrings.\n\n    Return (#failures, #tests).\n\n    See help(doctest) for an overview.\n\n    Optional keyword arg "name" gives the name of the module; by default\n    use m.__name__.\n\n    Optional keyword arg "globs" gives a dict to be used as the globals\n    when executing examples; by default, use m.__dict__.  A copy of this\n    dict is actually used for each docstring, so that each docstring\'s\n    examples start with a clean slate.\n\n    Optional keyword arg "extraglobs" gives a dictionary that should be\n    merged into the globals that are used to execute examples.  By\n    default, no extra globals are used.  This is new in 2.4.\n\n    Optional keyword arg "verbose" prints lots of stuff if true, prints\n    only failures if false; by default, it\'s true iff "-v" is in sys.argv.\n\n    Optional keyword arg "report" prints a summary at the end when true,\n    else prints nothing at the end.  In verbose mode, the summary is\n    detailed, else very brief (in fact, empty if all tests passed).\n\n    Optional keyword arg "optionflags" or\'s together module constants,\n    and defaults to 0.  This is new in 2.3.  Possible values (see the\n    docs for details):\n\n        DONT_ACCEPT_TRUE_FOR_1\n        DONT_ACCEPT_BLANKLINE\n        NORMALIZE_WHITESPACE\n        ELLIPSIS\n        SKIP\n        IGNORE_EXCEPTION_DETAIL\n        REPORT_UDIFF\n        REPORT_CDIFF\n        REPORT_NDIFF\n        REPORT_ONLY_FIRST_FAILURE\n\n    Optional keyword arg "raise_on_error" raises an exception on the\n    first unexpected exception or failure. This allows failures to be\n    post-mortem debugged.\n\n    Advanced tomfoolery:  testmod runs methods of a local instance of\n    class doctest.Tester, then merges the results into (or creates)\n    global Tester instance doctest.master.  Methods of doctest.master\n    can be called directly too, if you want to do something unusual.\n    Passing report=0 to testmod is especially useful then, to delay\n    displaying a summary.  Invoke doctest.master.summarize(verbose)\n    when you\'re done fiddling.\n    '
    global master
    if m is None:
        m = sys.modules.get("__main__")
    if not inspect.ismodule(m):
        raise TypeError(("testmod: module required; %r" % (m,)))
    if name is None:
        name = m.__name__
    finder = DocTestFinder(exclude_empty=exclude_empty)
    if raise_on_error:
        runner = DebugRunner(verbose=verbose, optionflags=optionflags)
    else:
        runner = DocTestRunner(verbose=verbose, optionflags=optionflags)
    for test in finder.find(m, name, globs=globs, extraglobs=extraglobs):
        runner.run(test)
    if report:
        runner.summarize()
    if master is None:
        master = runner
    else:
        master.merge(runner)
    return TestResults(runner.failures, runner.tries)


def testfile(
    filename,
    module_relative=True,
    name=None,
    package=None,
    globs=None,
    verbose=None,
    report=True,
    optionflags=0,
    extraglobs=None,
    raise_on_error=False,
    parser=DocTestParser(),
    encoding=None,
):
    '\n    Test examples in the given file.  Return (#failures, #tests).\n\n    Optional keyword arg "module_relative" specifies how filenames\n    should be interpreted:\n\n      - If "module_relative" is True (the default), then "filename"\n         specifies a module-relative path.  By default, this path is\n         relative to the calling module\'s directory; but if the\n         "package" argument is specified, then it is relative to that\n         package.  To ensure os-independence, "filename" should use\n         "/" characters to separate path segments, and should not\n         be an absolute path (i.e., it may not begin with "/").\n\n      - If "module_relative" is False, then "filename" specifies an\n        os-specific path.  The path may be absolute or relative (to\n        the current working directory).\n\n    Optional keyword arg "name" gives the name of the test; by default\n    use the file\'s basename.\n\n    Optional keyword argument "package" is a Python package or the\n    name of a Python package whose directory should be used as the\n    base directory for a module relative filename.  If no package is\n    specified, then the calling module\'s directory is used as the base\n    directory for module relative filenames.  It is an error to\n    specify "package" if "module_relative" is False.\n\n    Optional keyword arg "globs" gives a dict to be used as the globals\n    when executing examples; by default, use {}.  A copy of this dict\n    is actually used for each docstring, so that each docstring\'s\n    examples start with a clean slate.\n\n    Optional keyword arg "extraglobs" gives a dictionary that should be\n    merged into the globals that are used to execute examples.  By\n    default, no extra globals are used.\n\n    Optional keyword arg "verbose" prints lots of stuff if true, prints\n    only failures if false; by default, it\'s true iff "-v" is in sys.argv.\n\n    Optional keyword arg "report" prints a summary at the end when true,\n    else prints nothing at the end.  In verbose mode, the summary is\n    detailed, else very brief (in fact, empty if all tests passed).\n\n    Optional keyword arg "optionflags" or\'s together module constants,\n    and defaults to 0.  Possible values (see the docs for details):\n\n        DONT_ACCEPT_TRUE_FOR_1\n        DONT_ACCEPT_BLANKLINE\n        NORMALIZE_WHITESPACE\n        ELLIPSIS\n        SKIP\n        IGNORE_EXCEPTION_DETAIL\n        REPORT_UDIFF\n        REPORT_CDIFF\n        REPORT_NDIFF\n        REPORT_ONLY_FIRST_FAILURE\n\n    Optional keyword arg "raise_on_error" raises an exception on the\n    first unexpected exception or failure. This allows failures to be\n    post-mortem debugged.\n\n    Optional keyword arg "parser" specifies a DocTestParser (or\n    subclass) that should be used to extract tests from the files.\n\n    Optional keyword arg "encoding" specifies an encoding that should\n    be used to convert the file to unicode.\n\n    Advanced tomfoolery:  testmod runs methods of a local instance of\n    class doctest.Tester, then merges the results into (or creates)\n    global Tester instance doctest.master.  Methods of doctest.master\n    can be called directly too, if you want to do something unusual.\n    Passing report=0 to testmod is especially useful then, to delay\n    displaying a summary.  Invoke doctest.master.summarize(verbose)\n    when you\'re done fiddling.\n    '
    global master
    if package and (not module_relative):
        raise ValueError("Package may only be specified for module-relative paths.")
    (text, filename) = _load_testfile(
        filename, package, module_relative, (encoding or "utf-8")
    )
    if name is None:
        name = os.path.basename(filename)
    if globs is None:
        globs = {}
    else:
        globs = globs.copy()
    if extraglobs is not None:
        globs.update(extraglobs)
    if "__name__" not in globs:
        globs["__name__"] = "__main__"
    if raise_on_error:
        runner = DebugRunner(verbose=verbose, optionflags=optionflags)
    else:
        runner = DocTestRunner(verbose=verbose, optionflags=optionflags)
    test = parser.get_doctest(text, globs, name, filename, 0)
    runner.run(test)
    if report:
        runner.summarize()
    if master is None:
        master = runner
    else:
        master.merge(runner)
    return TestResults(runner.failures, runner.tries)


def run_docstring_examples(
    f, globs, verbose=False, name="NoName", compileflags=None, optionflags=0
):
    "\n    Test examples in the given object's docstring (`f`), using `globs`\n    as globals.  Optional argument `name` is used in failure messages.\n    If the optional argument `verbose` is true, then generate output\n    even if there are no failures.\n\n    `compileflags` gives the set of flags that should be used by the\n    Python compiler when running the examples.  If not specified, then\n    it will default to the set of future-import flags that apply to\n    `globs`.\n\n    Optional keyword arg `optionflags` specifies options for the\n    testing and output.  See the documentation for `testmod` for more\n    information.\n    "
    finder = DocTestFinder(verbose=verbose, recurse=False)
    runner = DocTestRunner(verbose=verbose, optionflags=optionflags)
    for test in finder.find(f, name, globs=globs):
        runner.run(test, compileflags=compileflags)


_unittest_reportflags = 0


def set_unittest_reportflags(flags):
    "Sets the unittest option flags.\n\n    The old flag is returned so that a runner could restore the old\n    value if it wished to:\n\n      >>> import doctest\n      >>> old = doctest._unittest_reportflags\n      >>> doctest.set_unittest_reportflags(REPORT_NDIFF |\n      ...                          REPORT_ONLY_FIRST_FAILURE) == old\n      True\n\n      >>> doctest._unittest_reportflags == (REPORT_NDIFF |\n      ...                                   REPORT_ONLY_FIRST_FAILURE)\n      True\n\n    Only reporting flags can be set:\n\n      >>> doctest.set_unittest_reportflags(ELLIPSIS)\n      Traceback (most recent call last):\n      ...\n      ValueError: ('Only reporting flags allowed', 8)\n\n      >>> doctest.set_unittest_reportflags(old) == (REPORT_NDIFF |\n      ...                                   REPORT_ONLY_FIRST_FAILURE)\n      True\n    "
    global _unittest_reportflags
    if (flags & REPORTING_FLAGS) != flags:
        raise ValueError("Only reporting flags allowed", flags)
    old = _unittest_reportflags
    _unittest_reportflags = flags
    return old


class DocTestCase(unittest.TestCase):
    def __init__(self, test, optionflags=0, setUp=None, tearDown=None, checker=None):
        unittest.TestCase.__init__(self)
        self._dt_optionflags = optionflags
        self._dt_checker = checker
        self._dt_test = test
        self._dt_setUp = setUp
        self._dt_tearDown = tearDown

    def setUp(self):
        test = self._dt_test
        if self._dt_setUp is not None:
            self._dt_setUp(test)

    def tearDown(self):
        test = self._dt_test
        if self._dt_tearDown is not None:
            self._dt_tearDown(test)
        test.globs.clear()

    def runTest(self):
        test = self._dt_test
        old = sys.stdout
        new = StringIO()
        optionflags = self._dt_optionflags
        if not (optionflags & REPORTING_FLAGS):
            optionflags |= _unittest_reportflags
        runner = DocTestRunner(
            optionflags=optionflags, checker=self._dt_checker, verbose=False
        )
        try:
            runner.DIVIDER = "-" * 70
            (failures, tries) = runner.run(test, out=new.write, clear_globs=False)
        finally:
            sys.stdout = old
        if failures:
            raise self.failureException(self.format_failure(new.getvalue()))

    def format_failure(self, err):
        test = self._dt_test
        if test.lineno is None:
            lineno = "unknown line number"
        else:
            lineno = "%s" % test.lineno
        lname = ".".join(test.name.split(".")[(-1):])
        return 'Failed doctest test for %s\n  File "%s", line %s, in %s\n\n%s' % (
            test.name,
            test.filename,
            lineno,
            lname,
            err,
        )

    def debug(self):
        "Run the test case without results and without catching exceptions\n\n           The unit test framework includes a debug method on test cases\n           and test suites to support post-mortem debugging.  The test code\n           is run in such a way that errors are not caught.  This way a\n           caller can catch the errors and initiate post-mortem debugging.\n\n           The DocTestCase provides a debug method that raises\n           UnexpectedException errors if there is an unexpected\n           exception:\n\n             >>> test = DocTestParser().get_doctest('>>> raise KeyError\\n42',\n             ...                {}, 'foo', 'foo.py', 0)\n             >>> case = DocTestCase(test)\n             >>> try:\n             ...     case.debug()\n             ... except UnexpectedException as f:\n             ...     failure = f\n\n           The UnexpectedException contains the test, the example, and\n           the original exception:\n\n             >>> failure.test is test\n             True\n\n             >>> failure.example.want\n             '42\\n'\n\n             >>> exc_info = failure.exc_info\n             >>> raise exc_info[1] # Already has the traceback\n             Traceback (most recent call last):\n             ...\n             KeyError\n\n           If the output doesn't match, then a DocTestFailure is raised:\n\n             >>> test = DocTestParser().get_doctest('''\n             ...      >>> x = 1\n             ...      >>> x\n             ...      2\n             ...      ''', {}, 'foo', 'foo.py', 0)\n             >>> case = DocTestCase(test)\n\n             >>> try:\n             ...    case.debug()\n             ... except DocTestFailure as f:\n             ...    failure = f\n\n           DocTestFailure objects provide access to the test:\n\n             >>> failure.test is test\n             True\n\n           As well as to the example:\n\n             >>> failure.example.want\n             '2\\n'\n\n           and the actual output:\n\n             >>> failure.got\n             '1\\n'\n\n           "
        self.setUp()
        runner = DebugRunner(
            optionflags=self._dt_optionflags, checker=self._dt_checker, verbose=False
        )
        runner.run(self._dt_test, clear_globs=False)
        self.tearDown()

    def id(self):
        return self._dt_test.name

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (
            (self._dt_test == other._dt_test)
            and (self._dt_optionflags == other._dt_optionflags)
            and (self._dt_setUp == other._dt_setUp)
            and (self._dt_tearDown == other._dt_tearDown)
            and (self._dt_checker == other._dt_checker)
        )

    def __hash__(self):
        return hash(
            (self._dt_optionflags, self._dt_setUp, self._dt_tearDown, self._dt_checker)
        )

    def __repr__(self):
        name = self._dt_test.name.split(".")
        return "%s (%s)" % (name[(-1)], ".".join(name[:(-1)]))

    __str__ = object.__str__

    def shortDescription(self):
        return "Doctest: " + self._dt_test.name


class SkipDocTestCase(DocTestCase):
    def __init__(self, module):
        self.module = module
        DocTestCase.__init__(self, None)

    def setUp(self):
        self.skipTest("DocTestSuite will not work with -O2 and above")

    def test_skip(self):
        pass

    def shortDescription(self):
        return "Skipping tests from %s" % self.module.__name__

    __str__ = shortDescription


class _DocTestSuite(unittest.TestSuite):
    def _removeTestAtIndex(self, index):
        pass


def DocTestSuite(module=None, globs=None, extraglobs=None, test_finder=None, **options):
    "\n    Convert doctest tests for a module to a unittest test suite.\n\n    This converts each documentation string in a module that\n    contains doctest tests to a unittest test case.  If any of the\n    tests in a doc string fail, then the test case fails.  An exception\n    is raised showing the name of the file containing the test and a\n    (sometimes approximate) line number.\n\n    The `module` argument provides the module to be tested.  The argument\n    can be either a module or a module name.\n\n    If no argument is given, the calling module is used.\n\n    A number of options may be provided as keyword arguments:\n\n    setUp\n      A set-up function.  This is called before running the\n      tests in each file. The setUp function will be passed a DocTest\n      object.  The setUp function can access the test globals as the\n      globs attribute of the test passed.\n\n    tearDown\n      A tear-down function.  This is called after running the\n      tests in each file.  The tearDown function will be passed a DocTest\n      object.  The tearDown function can access the test globals as the\n      globs attribute of the test passed.\n\n    globs\n      A dictionary containing initial global variables for the tests.\n\n    optionflags\n       A set of doctest option flags expressed as an integer.\n    "
    if test_finder is None:
        test_finder = DocTestFinder()
    module = _normalize_module(module)
    tests = test_finder.find(module, globs=globs, extraglobs=extraglobs)
    if (not tests) and (sys.flags.optimize >= 2):
        suite = _DocTestSuite()
        suite.addTest(SkipDocTestCase(module))
        return suite
    tests.sort()
    suite = _DocTestSuite()
    for test in tests:
        if len(test.examples) == 0:
            continue
        if not test.filename:
            filename = module.__file__
            if filename[(-4):] == ".pyc":
                filename = filename[:(-1)]
            test.filename = filename
        suite.addTest(DocTestCase(test, **options))
    return suite


class DocFileCase(DocTestCase):
    def id(self):
        return "_".join(self._dt_test.name.split("."))

    def __repr__(self):
        return self._dt_test.filename

    def format_failure(self, err):
        return 'Failed doctest test for %s\n  File "%s", line 0\n\n%s' % (
            self._dt_test.name,
            self._dt_test.filename,
            err,
        )


def DocFileTest(
    path,
    module_relative=True,
    package=None,
    globs=None,
    parser=DocTestParser(),
    encoding=None,
    **options,
):
    if globs is None:
        globs = {}
    else:
        globs = globs.copy()
    if package and (not module_relative):
        raise ValueError("Package may only be specified for module-relative paths.")
    (doc, path) = _load_testfile(path, package, module_relative, (encoding or "utf-8"))
    if "__file__" not in globs:
        globs["__file__"] = path
    name = os.path.basename(path)
    test = parser.get_doctest(doc, globs, name, path, 0)
    return DocFileCase(test, **options)


def DocFileSuite(*paths, **kw):
    'A unittest suite for one or more doctest files.\n\n    The path to each doctest file is given as a string; the\n    interpretation of that string depends on the keyword argument\n    "module_relative".\n\n    A number of options may be provided as keyword arguments:\n\n    module_relative\n      If "module_relative" is True, then the given file paths are\n      interpreted as os-independent module-relative paths.  By\n      default, these paths are relative to the calling module\'s\n      directory; but if the "package" argument is specified, then\n      they are relative to that package.  To ensure os-independence,\n      "filename" should use "/" characters to separate path\n      segments, and may not be an absolute path (i.e., it may not\n      begin with "/").\n\n      If "module_relative" is False, then the given file paths are\n      interpreted as os-specific paths.  These paths may be absolute\n      or relative (to the current working directory).\n\n    package\n      A Python package or the name of a Python package whose directory\n      should be used as the base directory for module relative paths.\n      If "package" is not specified, then the calling module\'s\n      directory is used as the base directory for module relative\n      filenames.  It is an error to specify "package" if\n      "module_relative" is False.\n\n    setUp\n      A set-up function.  This is called before running the\n      tests in each file. The setUp function will be passed a DocTest\n      object.  The setUp function can access the test globals as the\n      globs attribute of the test passed.\n\n    tearDown\n      A tear-down function.  This is called after running the\n      tests in each file.  The tearDown function will be passed a DocTest\n      object.  The tearDown function can access the test globals as the\n      globs attribute of the test passed.\n\n    globs\n      A dictionary containing initial global variables for the tests.\n\n    optionflags\n      A set of doctest option flags expressed as an integer.\n\n    parser\n      A DocTestParser (or subclass) that should be used to extract\n      tests from the files.\n\n    encoding\n      An encoding that will be used to convert the files to unicode.\n    '
    suite = _DocTestSuite()
    if kw.get("module_relative", True):
        kw["package"] = _normalize_module(kw.get("package"))
    for path in paths:
        suite.addTest(DocFileTest(path, **kw))
    return suite


def script_from_examples(s):
    "Extract script from text with examples.\n\n       Converts text with examples to a Python script.  Example input is\n       converted to regular code.  Example output and all other words\n       are converted to comments:\n\n       >>> text = '''\n       ...       Here are examples of simple math.\n       ...\n       ...           Python has super accurate integer addition\n       ...\n       ...           >>> 2 + 2\n       ...           5\n       ...\n       ...           And very friendly error messages:\n       ...\n       ...           >>> 1/0\n       ...           To Infinity\n       ...           And\n       ...           Beyond\n       ...\n       ...           You can use logic if you want:\n       ...\n       ...           >>> if 0:\n       ...           ...    blah\n       ...           ...    blah\n       ...           ...\n       ...\n       ...           Ho hum\n       ...           '''\n\n       >>> print(script_from_examples(text))\n       # Here are examples of simple math.\n       #\n       #     Python has super accurate integer addition\n       #\n       2 + 2\n       # Expected:\n       ## 5\n       #\n       #     And very friendly error messages:\n       #\n       1/0\n       # Expected:\n       ## To Infinity\n       ## And\n       ## Beyond\n       #\n       #     You can use logic if you want:\n       #\n       if 0:\n          blah\n          blah\n       #\n       #     Ho hum\n       <BLANKLINE>\n       "
    output = []
    for piece in DocTestParser().parse(s):
        if isinstance(piece, Example):
            output.append(piece.source[:(-1)])
            want = piece.want
            if want:
                output.append("# Expected:")
                output += [("## " + l) for l in want.split("\n")[:(-1)]]
        else:
            output += [_comment_line(l) for l in piece.split("\n")[:(-1)]]
    while output and (output[(-1)] == "#"):
        output.pop()
    while output and (output[0] == "#"):
        output.pop(0)
    return "\n".join(output) + "\n"


def testsource(module, name):
    "Extract the test sources from a doctest docstring as a script.\n\n    Provide the module (or dotted name of the module) containing the\n    test to be debugged and the name (within the module) of the object\n    with the doc string with tests to be debugged.\n    "
    module = _normalize_module(module)
    tests = DocTestFinder().find(module)
    test = [t for t in tests if (t.name == name)]
    if not test:
        raise ValueError(name, "not found in tests")
    test = test[0]
    testsrc = script_from_examples(test.docstring)
    return testsrc


def debug_src(src, pm=False, globs=None):
    "Debug a single doctest docstring, in argument `src`'"
    testsrc = script_from_examples(src)
    debug_script(testsrc, pm, globs)


def debug_script(src, pm=False, globs=None):
    "Debug a test script.  `src` is the script, as a string."
    import pdb

    if globs:
        globs = globs.copy()
    else:
        globs = {}
    if pm:
        try:
            exec(src, globs, globs)
        except:
            print(sys.exc_info()[1])
            p = pdb.Pdb(nosigint=True)
            p.reset()
            p.interaction(None, sys.exc_info()[2])
    else:
        pdb.Pdb(nosigint=True).run(("exec(%r)" % src), globs, globs)


def debug(module, name, pm=False):
    "Debug a single doctest docstring.\n\n    Provide the module (or dotted name of the module) containing the\n    test to be debugged and the name (within the module) of the object\n    with the docstring with tests to be debugged.\n    "
    module = _normalize_module(module)
    testsrc = testsource(module, name)
    debug_script(testsrc, pm, module.__dict__)


class _TestClass:
    "\n    A pointless class, for sanity-checking of docstring testing.\n\n    Methods:\n        square()\n        get()\n\n    >>> _TestClass(13).get() + _TestClass(-12).get()\n    1\n    >>> hex(_TestClass(13).square().get())\n    '0xa9'\n    "

    def __init__(self, val):
        "val -> _TestClass object with associated value val.\n\n        >>> t = _TestClass(123)\n        >>> print(t.get())\n        123\n        "
        self.val = val

    def square(self):
        "square() -> square TestClass's associated value\n\n        >>> _TestClass(13).square().get()\n        169\n        "
        self.val = self.val ** 2
        return self

    def get(self):
        "get() -> return TestClass's associated value.\n\n        >>> x = _TestClass(-42)\n        >>> print(x.get())\n        -42\n        "
        return self.val


__test__ = {
    "_TestClass": _TestClass,
    "string": "\n                      Example of a string object, searched as-is.\n                      >>> x = 1; y = 2\n                      >>> x + y, x * y\n                      (3, 2)\n                      ",
    "bool-int equivalence": "\n                                    In 2.2, boolean expressions displayed\n                                    0 or 1.  By default, we still accept\n                                    them.  This can be disabled by passing\n                                    DONT_ACCEPT_TRUE_FOR_1 to the new\n                                    optionflags argument.\n                                    >>> 4 == 4\n                                    1\n                                    >>> 4 == 4\n                                    True\n                                    >>> 4 > 4\n                                    0\n                                    >>> 4 > 4\n                                    False\n                                    ",
    "blank lines": "\n                Blank lines can be marked with <BLANKLINE>:\n                    >>> print('foo\\n\\nbar\\n')\n                    foo\n                    <BLANKLINE>\n                    bar\n                    <BLANKLINE>\n            ",
    "ellipsis": "\n                If the ellipsis flag is used, then '...' can be used to\n                elide substrings in the desired output:\n                    >>> print(list(range(1000))) #doctest: +ELLIPSIS\n                    [0, 1, 2, ..., 999]\n            ",
    "whitespace normalization": "\n                If the whitespace normalization flag is used, then\n                differences in whitespace are ignored.\n                    >>> print(list(range(30))) #doctest: +NORMALIZE_WHITESPACE\n                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,\n                     15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,\n                     27, 28, 29]\n            ",
}


def _test():
    import argparse

    parser = argparse.ArgumentParser(description="doctest runner")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="print very verbose output for all tests",
    )
    parser.add_argument(
        "-o",
        "--option",
        action="append",
        choices=OPTIONFLAGS_BY_NAME.keys(),
        default=[],
        help="specify a doctest option flag to apply to the test run; may be specified more than once to apply multiple options",
    )
    parser.add_argument(
        "-f",
        "--fail-fast",
        action="store_true",
        help="stop running tests after first failure (this is a shorthand for -o FAIL_FAST, and is in addition to any other -o options)",
    )
    parser.add_argument("file", nargs="+", help="file containing the tests to run")
    args = parser.parse_args()
    testfiles = args.file
    verbose = args.verbose
    options = 0
    for option in args.option:
        options |= OPTIONFLAGS_BY_NAME[option]
    if args.fail_fast:
        options |= FAIL_FAST
    for filename in testfiles:
        if filename.endswith(".py"):
            (dirname, filename) = os.path.split(filename)
            sys.path.insert(0, dirname)
            m = __import__(filename[:(-3)])
            del sys.path[0]
            (failures, _) = testmod(m, verbose=verbose, optionflags=options)
        else:
            (failures, _) = testfile(
                filename, module_relative=False, verbose=verbose, optionflags=options
            )
        if failures:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(_test())
