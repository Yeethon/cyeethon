"Extract, format and print information about Python stack traces."
import collections
import itertools
import linecache
import sys

__all__ = [
    "extract_stack",
    "extract_tb",
    "format_exception",
    "format_exception_only",
    "format_list",
    "format_stack",
    "format_tb",
    "print_exc",
    "format_exc",
    "print_exception",
    "print_last",
    "print_stack",
    "print_tb",
    "clear_frames",
    "FrameSummary",
    "StackSummary",
    "TracebackException",
    "walk_stack",
    "walk_tb",
]


def print_list(extracted_list, file=None):
    "Print the list of tuples as returned by extract_tb() or\n    extract_stack() as a formatted stack trace to the given file."
    if file is None:
        file = sys.stderr
    for item in StackSummary.from_list(extracted_list).format():
        print(item, file=file, end="")


def format_list(extracted_list):
    "Format a list of tuples or FrameSummary objects for printing.\n\n    Given a list of tuples or FrameSummary objects as returned by\n    extract_tb() or extract_stack(), return a list of strings ready\n    for printing.\n\n    Each string in the resulting list corresponds to the item with the\n    same index in the argument list.  Each string ends in a newline;\n    the strings may contain internal newlines as well, for those items\n    whose source text line is not None.\n    "
    return StackSummary.from_list(extracted_list).format()


def print_tb(tb, limit=None, file=None):
    "Print up to 'limit' stack trace entries from the traceback 'tb'.\n\n    If 'limit' is omitted or None, all entries are printed.  If 'file'\n    is omitted or None, the output goes to sys.stderr; otherwise\n    'file' should be an open file or file-like object with a write()\n    method.\n    "
    print_list(extract_tb(tb, limit=limit), file=file)


def format_tb(tb, limit=None):
    "A shorthand for 'format_list(extract_tb(tb, limit))'."
    return extract_tb(tb, limit=limit).format()


def extract_tb(tb, limit=None):
    "\n    Return a StackSummary object representing a list of\n    pre-processed entries from traceback.\n\n    This is useful for alternate formatting of stack traces.  If\n    'limit' is omitted or None, all entries are extracted.  A\n    pre-processed stack trace entry is a FrameSummary object\n    containing attributes filename, lineno, name, and line\n    representing the information that is usually printed for a stack\n    trace.  The line is a string with leading and trailing\n    whitespace stripped; if the source is not available it is None.\n    "
    return StackSummary.extract(walk_tb(tb), limit=limit)


_cause_message = (
    "\nThe above exception was the direct cause of the following exception:\n\n"
)
_context_message = (
    "\nDuring handling of the above exception, another exception occurred:\n\n"
)
_sentinel = object()


def _parse_value_tb(exc, value, tb):
    if (value is _sentinel) != (tb is _sentinel):
        raise ValueError("Both or neither of value and tb must be given")
    if value is tb is _sentinel:
        if exc is not None:
            return (exc, exc.__traceback__)
        else:
            return (None, None)
    return (value, tb)


def print_exception(
    exc, /, value=_sentinel, tb=_sentinel, limit=None, file=None, chain=True
):
    "Print exception up to 'limit' stack trace entries from 'tb' to 'file'.\n\n    This differs from print_tb() in the following ways: (1) if\n    traceback is not None, it prints a header \"Traceback (most recent\n    call last):\"; (2) it prints the exception type and value after the\n    stack trace; (3) if type is SyntaxError and value has the\n    appropriate format, it prints the line where the syntax error\n    occurred with a caret on the next line indicating the approximate\n    position of the error.\n    "
    (value, tb) = _parse_value_tb(exc, value, tb)
    if file is None:
        file = sys.stderr
    te = TracebackException(type(value), value, tb, limit=limit, compact=True)
    for line in te.format(chain=chain):
        print(line, file=file, end="")


def format_exception(exc, /, value=_sentinel, tb=_sentinel, limit=None, chain=True):
    "Format a stack trace and the exception information.\n\n    The arguments have the same meaning as the corresponding arguments\n    to print_exception().  The return value is a list of strings, each\n    ending in a newline and some containing internal newlines.  When\n    these lines are concatenated and printed, exactly the same text is\n    printed as does print_exception().\n    "
    (value, tb) = _parse_value_tb(exc, value, tb)
    te = TracebackException(type(value), value, tb, limit=limit, compact=True)
    return list(te.format(chain=chain))


def format_exception_only(exc, /, value=_sentinel):
    "Format the exception part of a traceback.\n\n    The return value is a list of strings, each ending in a newline.\n\n    Normally, the list contains a single string; however, for\n    SyntaxError exceptions, it contains several lines that (when\n    printed) display detailed information about where the syntax\n    error occurred.\n\n    The message indicating which exception occurred is always the last\n    string in the list.\n\n    "
    if value is _sentinel:
        value = exc
    te = TracebackException(type(value), value, None, compact=True)
    return list(te.format_exception_only())


def _format_final_exc_line(etype, value):
    valuestr = _some_str(value)
    if (value is None) or (not valuestr):
        line = "%s\n" % etype
    else:
        line = "%s: %s\n" % (etype, valuestr)
    return line


def _some_str(value):
    try:
        return str(value)
    except:
        return "<unprintable %s object>" % type(value).__name__


def print_exc(limit=None, file=None, chain=True):
    "Shorthand for 'print_exception(*sys.exc_info(), limit, file)'."
    print_exception(*sys.exc_info(), limit=limit, file=file, chain=chain)


def format_exc(limit=None, chain=True):
    "Like print_exc() but return a string."
    return "".join(format_exception(*sys.exc_info(), limit=limit, chain=chain))


def print_last(limit=None, file=None, chain=True):
    "This is a shorthand for 'print_exception(sys.last_type,\n    sys.last_value, sys.last_traceback, limit, file)'."
    if not hasattr(sys, "last_type"):
        raise ValueError("no last exception")
    print_exception(
        sys.last_type, sys.last_value, sys.last_traceback, limit, file, chain
    )


def print_stack(f=None, limit=None, file=None):
    "Print a stack trace from its invocation point.\n\n    The optional 'f' argument can be used to specify an alternate\n    stack frame at which to start. The optional 'limit' and 'file'\n    arguments have the same meaning as for print_exception().\n    "
    if f is None:
        f = sys._getframe().f_back
    print_list(extract_stack(f, limit=limit), file=file)


def format_stack(f=None, limit=None):
    "Shorthand for 'format_list(extract_stack(f, limit))'."
    if f is None:
        f = sys._getframe().f_back
    return format_list(extract_stack(f, limit=limit))


def extract_stack(f=None, limit=None):
    "Extract the raw traceback from the current stack frame.\n\n    The return value has the same format as for extract_tb().  The\n    optional 'f' and 'limit' arguments have the same meaning as for\n    print_stack().  Each item in the list is a quadruple (filename,\n    line number, function name, text), and the entries are in order\n    from oldest to newest stack frame.\n    "
    if f is None:
        f = sys._getframe().f_back
    stack = StackSummary.extract(walk_stack(f), limit=limit)
    stack.reverse()
    return stack


def clear_frames(tb):
    "Clear all references to local variables in the frames of a traceback."
    while tb is not None:
        try:
            tb.tb_frame.clear()
        except RuntimeError:
            pass
        tb = tb.tb_next


class FrameSummary:
    "A single frame from a traceback.\n\n    - :attr:`filename` The filename for the frame.\n    - :attr:`lineno` The line within filename for the frame that was\n      active when the frame was captured.\n    - :attr:`name` The name of the function or method that was executing\n      when the frame was captured.\n    - :attr:`line` The text from the linecache module for the\n      of code that was running when the frame was captured.\n    - :attr:`locals` Either None if locals were not supplied, or a dict\n      mapping the name to the repr() of the variable.\n    "
    __slots__ = ("filename", "lineno", "name", "_line", "locals")

    def __init__(
        self, filename, lineno, name, *, lookup_line=True, locals=None, line=None
    ):
        "Construct a FrameSummary.\n\n        :param lookup_line: If True, `linecache` is consulted for the source\n            code line. Otherwise, the line will be looked up when first needed.\n        :param locals: If supplied the frame locals, which will be captured as\n            object representations.\n        :param line: If provided, use this instead of looking up the line in\n            the linecache.\n        "
        self.filename = filename
        self.lineno = lineno
        self.name = name
        self._line = line
        if lookup_line:
            self.line
        self.locals = {k: repr(v) for (k, v) in locals.items()} if locals else None

    def __eq__(self, other):
        if isinstance(other, FrameSummary):
            return (
                (self.filename == other.filename)
                and (self.lineno == other.lineno)
                and (self.name == other.name)
                and (self.locals == other.locals)
            )
        if isinstance(other, tuple):
            return (self.filename, self.lineno, self.name, self.line) == other
        return NotImplemented

    def __getitem__(self, pos):
        return (self.filename, self.lineno, self.name, self.line)[pos]

    def __iter__(self):
        return iter([self.filename, self.lineno, self.name, self.line])

    def __repr__(self):
        return "<FrameSummary file {filename}, line {lineno} in {name}>".format(
            filename=self.filename, lineno=self.lineno, name=self.name
        )

    def __len__(self):
        return 4

    @property
    def line(self):
        if self._line is None:
            self._line = linecache.getline(self.filename, self.lineno).strip()
        return self._line


def walk_stack(f):
    "Walk a stack yielding the frame and line number for each frame.\n\n    This will follow f.f_back from the given frame. If no frame is given, the\n    current stack is used. Usually used with StackSummary.extract.\n    "
    if f is None:
        f = sys._getframe().f_back.f_back
    while f is not None:
        (yield (f, f.f_lineno))
        f = f.f_back


def walk_tb(tb):
    "Walk a traceback yielding the frame and line number for each frame.\n\n    This will follow tb.tb_next (and thus is in the opposite order to\n    walk_stack). Usually used with StackSummary.extract.\n    "
    while tb is not None:
        (yield (tb.tb_frame, tb.tb_lineno))
        tb = tb.tb_next


_RECURSIVE_CUTOFF = 3


class StackSummary(list):
    "A stack of frames."

    @classmethod
    def extract(
        klass, frame_gen, *, limit=None, lookup_lines=True, capture_locals=False
    ):
        "Create a StackSummary from a traceback or stack object.\n\n        :param frame_gen: A generator that yields (frame, lineno) tuples to\n            include in the stack.\n        :param limit: None to include all frames or the number of frames to\n            include.\n        :param lookup_lines: If True, lookup lines for each frame immediately,\n            otherwise lookup is deferred until the frame is rendered.\n        :param capture_locals: If True, the local variables from each frame will\n            be captured as object representations into the FrameSummary.\n        "
        if limit is None:
            limit = getattr(sys, "tracebacklimit", None)
            if (limit is not None) and (limit < 0):
                limit = 0
        if limit is not None:
            if limit >= 0:
                frame_gen = itertools.islice(frame_gen, limit)
            else:
                frame_gen = collections.deque(frame_gen, maxlen=(-limit))
        result = klass()
        fnames = set()
        for (f, lineno) in frame_gen:
            co = f.f_code
            filename = co.co_filename
            name = co.co_name
            fnames.add(filename)
            linecache.lazycache(filename, f.f_globals)
            if capture_locals:
                f_locals = f.f_locals
            else:
                f_locals = None
            result.append(
                FrameSummary(filename, lineno, name, lookup_line=False, locals=f_locals)
            )
        for filename in fnames:
            linecache.checkcache(filename)
        if lookup_lines:
            for f in result:
                f.line
        return result

    @classmethod
    def from_list(klass, a_list):
        "\n        Create a StackSummary object from a supplied list of\n        FrameSummary objects or old-style list of tuples.\n        "
        result = StackSummary()
        for frame in a_list:
            if isinstance(frame, FrameSummary):
                result.append(frame)
            else:
                (filename, lineno, name, line) = frame
                result.append(FrameSummary(filename, lineno, name, line=line))
        return result

    def format(self):
        "Format the stack ready for printing.\n\n        Returns a list of strings ready for printing.  Each string in the\n        resulting list corresponds to a single frame from the stack.\n        Each string ends in a newline; the strings may contain internal\n        newlines as well, for those items with source text lines.\n\n        For long sequences of the same frame and line, the first few\n        repetitions are shown, followed by a summary line stating the exact\n        number of further repetitions.\n        "
        result = []
        last_file = None
        last_line = None
        last_name = None
        count = 0
        for frame in self:
            if (
                (last_file is None)
                or (last_file != frame.filename)
                or (last_line is None)
                or (last_line != frame.lineno)
                or (last_name is None)
                or (last_name != frame.name)
            ):
                if count > _RECURSIVE_CUTOFF:
                    count -= _RECURSIVE_CUTOFF
                    result.append(
                        f"""  [Previous line repeated {count} more time{('s' if (count > 1) else '')}]
"""
                    )
                last_file = frame.filename
                last_line = frame.lineno
                last_name = frame.name
                count = 0
            count += 1
            if count > _RECURSIVE_CUTOFF:
                continue
            row = []
            row.append(
                '  File "{}", line {}, in {}\n'.format(
                    frame.filename, frame.lineno, frame.name
                )
            )
            if frame.line:
                row.append("    {}\n".format(frame.line.strip()))
            if frame.locals:
                for (name, value) in sorted(frame.locals.items()):
                    row.append("    {name} = {value}\n".format(name=name, value=value))
            result.append("".join(row))
        if count > _RECURSIVE_CUTOFF:
            count -= _RECURSIVE_CUTOFF
            result.append(
                f"""  [Previous line repeated {count} more time{('s' if (count > 1) else '')}]
"""
            )
        return result


class TracebackException:
    "An exception ready for rendering.\n\n    The traceback module captures enough attributes from the original exception\n    to this intermediary form to ensure that no references are held, while\n    still being able to fully print or format it.\n\n    Use `from_exception` to create TracebackException instances from exception\n    objects, or the constructor to create TracebackException instances from\n    individual components.\n\n    - :attr:`__cause__` A TracebackException of the original *__cause__*.\n    - :attr:`__context__` A TracebackException of the original *__context__*.\n    - :attr:`__suppress_context__` The *__suppress_context__* value from the\n      original exception.\n    - :attr:`stack` A `StackSummary` representing the traceback.\n    - :attr:`exc_type` The class of the original traceback.\n    - :attr:`filename` For syntax errors - the filename where the error\n      occurred.\n    - :attr:`lineno` For syntax errors - the linenumber where the error\n      occurred.\n    - :attr:`text` For syntax errors - the text where the error\n      occurred.\n    - :attr:`offset` For syntax errors - the offset into the text where the\n      error occurred.\n    - :attr:`msg` For syntax errors - the compiler error message.\n    "

    def __init__(
        self,
        exc_type,
        exc_value,
        exc_traceback,
        *,
        limit=None,
        lookup_lines=True,
        capture_locals=False,
        compact=False,
        _seen=None,
    ):
        is_recursive_call = _seen is not None
        if _seen is None:
            _seen = set()
        _seen.add(id(exc_value))
        self.stack = StackSummary.extract(
            walk_tb(exc_traceback),
            limit=limit,
            lookup_lines=lookup_lines,
            capture_locals=capture_locals,
        )
        self.exc_type = exc_type
        self._str = _some_str(exc_value)
        if exc_type and issubclass(exc_type, SyntaxError):
            self.filename = exc_value.filename
            lno = exc_value.lineno
            self.lineno = str(lno) if (lno is not None) else None
            self.text = exc_value.text
            self.offset = exc_value.offset
            self.msg = exc_value.msg
        if lookup_lines:
            self._load_lines()
        self.__suppress_context__ = (
            exc_value.__suppress_context__ if (exc_value is not None) else False
        )
        if not is_recursive_call:
            queue = [(self, exc_value)]
            while queue:
                (te, e) = queue.pop()
                if e and (e.__cause__ is not None) and (id(e.__cause__) not in _seen):
                    cause = TracebackException(
                        type(e.__cause__),
                        e.__cause__,
                        e.__cause__.__traceback__,
                        limit=limit,
                        lookup_lines=lookup_lines,
                        capture_locals=capture_locals,
                        _seen=_seen,
                    )
                else:
                    cause = None
                if compact:
                    need_context = (
                        (cause is None)
                        and (e is not None)
                        and (not e.__suppress_context__)
                    )
                else:
                    need_context = True
                if (
                    e
                    and (e.__context__ is not None)
                    and need_context
                    and (id(e.__context__) not in _seen)
                ):
                    context = TracebackException(
                        type(e.__context__),
                        e.__context__,
                        e.__context__.__traceback__,
                        limit=limit,
                        lookup_lines=lookup_lines,
                        capture_locals=capture_locals,
                        _seen=_seen,
                    )
                else:
                    context = None
                te.__cause__ = cause
                te.__context__ = context
                if cause:
                    queue.append((te.__cause__, e.__cause__))
                if context:
                    queue.append((te.__context__, e.__context__))

    @classmethod
    def from_exception(cls, exc, *args, **kwargs):
        "Create a TracebackException from an exception."
        return cls(type(exc), exc, exc.__traceback__, *args, **kwargs)

    def _load_lines(self):
        "Private API. force all lines in the stack to be loaded."
        for frame in self.stack:
            frame.line

    def __eq__(self, other):
        if isinstance(other, TracebackException):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __str__(self):
        return self._str

    def format_exception_only(self):
        "Format the exception part of the traceback.\n\n        The return value is a generator of strings, each ending in a newline.\n\n        Normally, the generator emits a single string; however, for\n        SyntaxError exceptions, it emits several lines that (when\n        printed) display detailed information about where the syntax\n        error occurred.\n\n        The message indicating which exception occurred is always the last\n        string in the output.\n        "
        if self.exc_type is None:
            (yield _format_final_exc_line(None, self._str))
            return
        stype = self.exc_type.__qualname__
        smod = self.exc_type.__module__
        if smod not in ("__main__", "builtins"):
            stype = (smod + ".") + stype
        if not issubclass(self.exc_type, SyntaxError):
            (yield _format_final_exc_line(stype, self._str))
        else:
            (yield from self._format_syntax_error(stype))

    def _format_syntax_error(self, stype):
        "Format SyntaxError exceptions (internal helper)."
        filename_suffix = ""
        if self.lineno is not None:
            (
                yield '  File "{}", line {}\n'.format(
                    (self.filename or "<string>"), self.lineno
                )
            )
        elif self.filename is not None:
            filename_suffix = " ({})".format(self.filename)
        text = self.text
        if text is not None:
            rtext = text.rstrip("\n")
            ltext = rtext.lstrip(" \n\x0c")
            spaces = len(rtext) - len(ltext)
            (yield "    {}\n".format(ltext))
            caret = ((self.offset or 0) - 1) - spaces
            if caret >= 0:
                caretspace = ((c if c.isspace() else " ") for c in ltext[:caret])
                (yield "    {}^\n".format("".join(caretspace)))
        msg = self.msg or "<no detail available>"
        (yield "{}: {}{}\n".format(stype, msg, filename_suffix))

    def format(self, *, chain=True):
        "Format the exception.\n\n        If chain is not *True*, *__cause__* and *__context__* will not be formatted.\n\n        The return value is a generator of strings, each ending in a newline and\n        some containing internal newlines. `print_exception` is a wrapper around\n        this method which just prints the lines to a file.\n\n        The message indicating which exception occurred is always the last\n        string in the output.\n        "
        output = []
        exc = self
        while exc:
            if chain:
                if exc.__cause__ is not None:
                    chained_msg = _cause_message
                    chained_exc = exc.__cause__
                elif (exc.__context__ is not None) and (not exc.__suppress_context__):
                    chained_msg = _context_message
                    chained_exc = exc.__context__
                else:
                    chained_msg = None
                    chained_exc = None
                output.append((chained_msg, exc))
                exc = chained_exc
            else:
                output.append((None, exc))
                exc = None
        for (msg, exc) in reversed(output):
            if msg is not None:
                (yield msg)
            if exc.stack:
                (yield "Traceback (most recent call last):\n")
                (yield from exc.stack.format())
            (yield from exc.format_exception_only())
