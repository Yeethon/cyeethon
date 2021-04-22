"\nLogging package for Python. Based on PEP 282 and comments thereto in\ncomp.lang.python.\n\nCopyright (C) 2001-2019 Vinay Sajip. All Rights Reserved.\n\nTo use, simply 'import logging' and log away!\n"
import sys, os, time, io, re, traceback, warnings, weakref, collections.abc
from string import Template
from string import Formatter as StrFormatter

__all__ = [
    "BASIC_FORMAT",
    "BufferingFormatter",
    "CRITICAL",
    "DEBUG",
    "ERROR",
    "FATAL",
    "FileHandler",
    "Filter",
    "Formatter",
    "Handler",
    "INFO",
    "LogRecord",
    "Logger",
    "LoggerAdapter",
    "NOTSET",
    "NullHandler",
    "StreamHandler",
    "WARN",
    "WARNING",
    "addLevelName",
    "basicConfig",
    "captureWarnings",
    "critical",
    "debug",
    "disable",
    "error",
    "exception",
    "fatal",
    "getLevelName",
    "getLogger",
    "getLoggerClass",
    "info",
    "log",
    "makeLogRecord",
    "setLoggerClass",
    "shutdown",
    "warn",
    "warning",
    "getLogRecordFactory",
    "setLogRecordFactory",
    "lastResort",
    "raiseExceptions",
]
import threading

__author__ = "Vinay Sajip <vinay_sajip@red-dove.com>"
__status__ = "production"
__version__ = "0.5.1.2"
__date__ = "07 February 2010"
_startTime = time.time()
raiseExceptions = True
logThreads = True
logMultiprocessing = True
logProcesses = True
CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0
_levelToName = {
    CRITICAL: "CRITICAL",
    ERROR: "ERROR",
    WARNING: "WARNING",
    INFO: "INFO",
    DEBUG: "DEBUG",
    NOTSET: "NOTSET",
}
_nameToLevel = {
    "CRITICAL": CRITICAL,
    "FATAL": FATAL,
    "ERROR": ERROR,
    "WARN": WARNING,
    "WARNING": WARNING,
    "INFO": INFO,
    "DEBUG": DEBUG,
    "NOTSET": NOTSET,
}


def getLevelName(level):
    "\n    Return the textual or numeric representation of logging level 'level'.\n\n    If the level is one of the predefined levels (CRITICAL, ERROR, WARNING,\n    INFO, DEBUG) then you get the corresponding string. If you have\n    associated levels with names using addLevelName then the name you have\n    associated with 'level' is returned.\n\n    If a numeric value corresponding to one of the defined levels is passed\n    in, the corresponding string representation is returned.\n\n    If a string representation of the level is passed in, the corresponding\n    numeric value is returned.\n\n    If no matching numeric or string value is passed in, the string\n    'Level %s' % level is returned.\n    "
    result = _levelToName.get(level)
    if result is not None:
        return result
    result = _nameToLevel.get(level)
    if result is not None:
        return result
    return "Level %s" % level


def addLevelName(level, levelName):
    "\n    Associate 'levelName' with 'level'.\n\n    This is used when converting levels to text during message formatting.\n    "
    _acquireLock()
    try:
        _levelToName[level] = levelName
        _nameToLevel[levelName] = level
    finally:
        _releaseLock()


if hasattr(sys, "_getframe"):
    currentframe = lambda: sys._getframe(3)
else:

    def currentframe():
        "Return the frame object for the caller's stack frame."
        try:
            raise Exception
        except Exception:
            return sys.exc_info()[2].tb_frame.f_back


_srcfile = os.path.normcase(addLevelName.__code__.co_filename)


def _checkLevel(level):
    if isinstance(level, int):
        rv = level
    elif str(level) == level:
        if level not in _nameToLevel:
            raise ValueError(("Unknown level: %r" % level))
        rv = _nameToLevel[level]
    else:
        raise TypeError(("Level not an integer or a valid string: %r" % (level,)))
    return rv


_lock = threading.RLock()


def _acquireLock():
    "\n    Acquire the module-level lock for serializing access to shared data.\n\n    This should be released with _releaseLock().\n    "
    if _lock:
        _lock.acquire()


def _releaseLock():
    "\n    Release the module-level lock acquired by calling _acquireLock().\n    "
    if _lock:
        _lock.release()


if not hasattr(os, "register_at_fork"):

    def _register_at_fork_reinit_lock(instance):
        pass


else:
    _at_fork_reinit_lock_weakset = weakref.WeakSet()

    def _register_at_fork_reinit_lock(instance):
        _acquireLock()
        try:
            _at_fork_reinit_lock_weakset.add(instance)
        finally:
            _releaseLock()

    def _after_at_fork_child_reinit_locks():
        for handler in _at_fork_reinit_lock_weakset:
            handler._at_fork_reinit()
        _lock._at_fork_reinit()

    os.register_at_fork(
        before=_acquireLock,
        after_in_child=_after_at_fork_child_reinit_locks,
        after_in_parent=_releaseLock,
    )


class LogRecord(object):
    "\n    A LogRecord instance represents an event being logged.\n\n    LogRecord instances are created every time something is logged. They\n    contain all the information pertinent to the event being logged. The\n    main information passed in is in msg and args, which are combined\n    using str(msg) % args to create the message field of the record. The\n    record also includes information such as when the record was created,\n    the source line where the logging call was made, and any exception\n    information to be logged.\n    "

    def __init__(
        self,
        name,
        level,
        pathname,
        lineno,
        msg,
        args,
        exc_info,
        func=None,
        sinfo=None,
        **kwargs,
    ):
        "\n        Initialize a logging record with interesting information.\n        "
        ct = time.time()
        self.name = name
        self.msg = msg
        if (
            args
            and (len(args) == 1)
            and isinstance(args[0], collections.abc.Mapping)
            and args[0]
        ):
            args = args[0]
        self.args = args
        self.levelname = getLevelName(level)
        self.levelno = level
        self.pathname = pathname
        try:
            self.filename = os.path.basename(pathname)
            self.module = os.path.splitext(self.filename)[0]
        except (TypeError, ValueError, AttributeError):
            self.filename = pathname
            self.module = "Unknown module"
        self.exc_info = exc_info
        self.exc_text = None
        self.stack_info = sinfo
        self.lineno = lineno
        self.funcName = func
        self.created = ct
        self.msecs = (ct - int(ct)) * 1000
        self.relativeCreated = (self.created - _startTime) * 1000
        if logThreads:
            self.thread = threading.get_ident()
            self.threadName = threading.current_thread().name
        else:
            self.thread = None
            self.threadName = None
        if not logMultiprocessing:
            self.processName = None
        else:
            self.processName = "MainProcess"
            mp = sys.modules.get("multiprocessing")
            if mp is not None:
                try:
                    self.processName = mp.current_process().name
                except Exception:
                    pass
        if logProcesses and hasattr(os, "getpid"):
            self.process = os.getpid()
        else:
            self.process = None

    def __repr__(self):
        return '<LogRecord: %s, %s, %s, %s, "%s">' % (
            self.name,
            self.levelno,
            self.pathname,
            self.lineno,
            self.msg,
        )

    def getMessage(self):
        "\n        Return the message for this LogRecord.\n\n        Return the message for this LogRecord after merging any user-supplied\n        arguments with the message.\n        "
        msg = str(self.msg)
        if self.args:
            msg = msg % self.args
        return msg


_logRecordFactory = LogRecord


def setLogRecordFactory(factory):
    "\n    Set the factory to be used when instantiating a log record.\n\n    :param factory: A callable which will be called to instantiate\n    a log record.\n    "
    global _logRecordFactory
    _logRecordFactory = factory


def getLogRecordFactory():
    "\n    Return the factory to be used when instantiating a log record.\n    "
    return _logRecordFactory


def makeLogRecord(dict):
    "\n    Make a LogRecord whose attributes are defined by the specified dictionary,\n    This function is useful for converting a logging event received over\n    a socket connection (which is sent as a dictionary) into a LogRecord\n    instance.\n    "
    rv = _logRecordFactory(None, None, "", 0, "", (), None, None)
    rv.__dict__.update(dict)
    return rv


_str_formatter = StrFormatter()
del StrFormatter


class PercentStyle(object):
    default_format = "%(message)s"
    asctime_format = "%(asctime)s"
    asctime_search = "%(asctime)"
    validation_pattern = re.compile(
        "%\\(\\w+\\)[#0+ -]*(\\*|\\d+)?(\\.(\\*|\\d+))?[diouxefgcrsa%]", re.I
    )

    def __init__(self, fmt, *, defaults=None):
        self._fmt = fmt or self.default_format
        self._defaults = defaults

    def usesTime(self):
        return self._fmt.find(self.asctime_search) >= 0

    def validate(self):
        "Validate the input format, ensure it matches the correct style"
        if not self.validation_pattern.search(self._fmt):
            raise ValueError(
                (
                    "Invalid format '%s' for '%s' style"
                    % (self._fmt, self.default_format[0])
                )
            )

    def _format(self, record):
        if (defaults := self._defaults) :
            values = defaults | record.__dict__
        else:
            values = record.__dict__
        return self._fmt % values

    def format(self, record):
        try:
            return self._format(record)
        except KeyError as e:
            raise ValueError(("Formatting field not found in record: %s" % e))


class StrFormatStyle(PercentStyle):
    default_format = "{message}"
    asctime_format = "{asctime}"
    asctime_search = "{asctime"
    fmt_spec = re.compile(
        "^(.?[<>=^])?[+ -]?#?0?(\\d+|{\\w+})?[,_]?(\\.(\\d+|{\\w+}))?[bcdefgnosx%]?$",
        re.I,
    )
    field_spec = re.compile("^(\\d+|\\w+)(\\.\\w+|\\[[^]]+\\])*$")

    def _format(self, record):
        if (defaults := self._defaults) :
            values = defaults | record.__dict__
        else:
            values = record.__dict__
        return self._fmt.format(**values)

    def validate(self):
        "Validate the input format, ensure it is the correct string formatting style"
        fields = set()
        try:
            for (_, fieldname, spec, conversion) in _str_formatter.parse(self._fmt):
                if fieldname:
                    if not self.field_spec.match(fieldname):
                        raise ValueError(
                            ("invalid field name/expression: %r" % fieldname)
                        )
                    fields.add(fieldname)
                if conversion and (conversion not in "rsa"):
                    raise ValueError(("invalid conversion: %r" % conversion))
                if spec and (not self.fmt_spec.match(spec)):
                    raise ValueError(("bad specifier: %r" % spec))
        except ValueError as e:
            raise ValueError(("invalid format: %s" % e))
        if not fields:
            raise ValueError("invalid format: no fields")


class StringTemplateStyle(PercentStyle):
    default_format = "${message}"
    asctime_format = "${asctime}"
    asctime_search = "${asctime}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tpl = Template(self._fmt)

    def usesTime(self):
        fmt = self._fmt
        return (fmt.find("$asctime") >= 0) or (fmt.find(self.asctime_format) >= 0)

    def validate(self):
        pattern = Template.pattern
        fields = set()
        for m in pattern.finditer(self._fmt):
            d = m.groupdict()
            if d["named"]:
                fields.add(d["named"])
            elif d["braced"]:
                fields.add(d["braced"])
            elif m.group(0) == "$":
                raise ValueError("invalid format: bare '$' not allowed")
        if not fields:
            raise ValueError("invalid format: no fields")

    def _format(self, record):
        if (defaults := self._defaults) :
            values = defaults | record.__dict__
        else:
            values = record.__dict__
        return self._tpl.substitute(**values)


BASIC_FORMAT = "%(levelname)s:%(name)s:%(message)s"
_STYLES = {
    "%": (PercentStyle, BASIC_FORMAT),
    "{": (StrFormatStyle, "{levelname}:{name}:{message}"),
    "$": (StringTemplateStyle, "${levelname}:${name}:${message}"),
}


class Formatter(object):
    '\n    Formatter instances are used to convert a LogRecord to text.\n\n    Formatters need to know how a LogRecord is constructed. They are\n    responsible for converting a LogRecord to (usually) a string which can\n    be interpreted by either a human or an external system. The base Formatter\n    allows a formatting string to be specified. If none is supplied, the\n    style-dependent default value, "%(message)s", "{message}", or\n    "${message}", is used.\n\n    The Formatter can be initialized with a format string which makes use of\n    knowledge of the LogRecord attributes - e.g. the default value mentioned\n    above makes use of the fact that the user\'s message and arguments are pre-\n    formatted into a LogRecord\'s message attribute. Currently, the useful\n    attributes in a LogRecord are described by:\n\n    %(name)s            Name of the logger (logging channel)\n    %(levelno)s         Numeric logging level for the message (DEBUG, INFO,\n                        WARNING, ERROR, CRITICAL)\n    %(levelname)s       Text logging level for the message ("DEBUG", "INFO",\n                        "WARNING", "ERROR", "CRITICAL")\n    %(pathname)s        Full pathname of the source file where the logging\n                        call was issued (if available)\n    %(filename)s        Filename portion of pathname\n    %(module)s          Module (name portion of filename)\n    %(lineno)d          Source line number where the logging call was issued\n                        (if available)\n    %(funcName)s        Function name\n    %(created)f         Time when the LogRecord was created (time.time()\n                        return value)\n    %(asctime)s         Textual time when the LogRecord was created\n    %(msecs)d           Millisecond portion of the creation time\n    %(relativeCreated)d Time in milliseconds when the LogRecord was created,\n                        relative to the time the logging module was loaded\n                        (typically at application startup time)\n    %(thread)d          Thread ID (if available)\n    %(threadName)s      Thread name (if available)\n    %(process)d         Process ID (if available)\n    %(message)s         The result of record.getMessage(), computed just as\n                        the record is emitted\n    '
    converter = time.localtime

    def __init__(
        self, fmt=None, datefmt=None, style="%", validate=True, *, defaults=None
    ):
        "\n        Initialize the formatter with specified format strings.\n\n        Initialize the formatter either with the specified format string, or a\n        default as described above. Allow for specialized date formatting with\n        the optional datefmt argument. If datefmt is omitted, you get an\n        ISO8601-like (or RFC 3339-like) format.\n\n        Use a style parameter of '%', '{' or '$' to specify that you want to\n        use one of %-formatting, :meth:`str.format` (``{}``) formatting or\n        :class:`string.Template` formatting in your format string.\n\n        .. versionchanged:: 3.2\n           Added the ``style`` parameter.\n        "
        if style not in _STYLES:
            raise ValueError(("Style must be one of: %s" % ",".join(_STYLES.keys())))
        self._style = _STYLES[style][0](fmt, defaults=defaults)
        if validate:
            self._style.validate()
        self._fmt = self._style._fmt
        self.datefmt = datefmt

    default_time_format = "%Y-%m-%d %H:%M:%S"
    default_msec_format = "%s,%03d"

    def formatTime(self, record, datefmt=None):
        "\n        Return the creation time of the specified LogRecord as formatted text.\n\n        This method should be called from format() by a formatter which\n        wants to make use of a formatted time. This method can be overridden\n        in formatters to provide for any specific requirement, but the\n        basic behaviour is as follows: if datefmt (a string) is specified,\n        it is used with time.strftime() to format the creation time of the\n        record. Otherwise, an ISO8601-like (or RFC 3339-like) format is used.\n        The resulting string is returned. This function uses a user-configurable\n        function to convert the creation time to a tuple. By default,\n        time.localtime() is used; to change this for a particular formatter\n        instance, set the 'converter' attribute to a function with the same\n        signature as time.localtime() or time.gmtime(). To change it for all\n        formatters, for example if you want all logging times to be shown in GMT,\n        set the 'converter' attribute in the Formatter class.\n        "
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime(self.default_time_format, ct)
            if self.default_msec_format:
                s = self.default_msec_format % (s, record.msecs)
        return s

    def formatException(self, ei):
        "\n        Format and return the specified exception information as a string.\n\n        This default implementation just uses\n        traceback.print_exception()\n        "
        sio = io.StringIO()
        tb = ei[2]
        traceback.print_exception(ei[0], ei[1], tb, None, sio)
        s = sio.getvalue()
        sio.close()
        if s[(-1):] == "\n":
            s = s[:(-1)]
        return s

    def usesTime(self):
        "\n        Check if the format uses the creation time of the record.\n        "
        return self._style.usesTime()

    def formatMessage(self, record):
        return self._style.format(record)

    def formatStack(self, stack_info):
        "\n        This method is provided as an extension point for specialized\n        formatting of stack information.\n\n        The input data is a string as returned from a call to\n        :func:`traceback.print_stack`, but with the last trailing newline\n        removed.\n\n        The base implementation just returns the value passed in.\n        "
        return stack_info

    def format(self, record):
        "\n        Format the specified record as text.\n\n        The record's attribute dictionary is used as the operand to a\n        string formatting operation which yields the returned string.\n        Before formatting the dictionary, a couple of preparatory steps\n        are carried out. The message attribute of the record is computed\n        using LogRecord.getMessage(). If the formatting string uses the\n        time (as determined by a call to usesTime(), formatTime() is\n        called to format the event time. If there is exception information,\n        it is formatted using formatException() and appended to the message.\n        "
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[(-1):] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        if record.stack_info:
            if s[(-1):] != "\n":
                s = s + "\n"
            s = s + self.formatStack(record.stack_info)
        return s


_defaultFormatter = Formatter()


class BufferingFormatter(object):
    "\n    A formatter suitable for formatting a number of records.\n    "

    def __init__(self, linefmt=None):
        "\n        Optionally specify a formatter which will be used to format each\n        individual record.\n        "
        if linefmt:
            self.linefmt = linefmt
        else:
            self.linefmt = _defaultFormatter

    def formatHeader(self, records):
        "\n        Return the header string for the specified records.\n        "
        return ""

    def formatFooter(self, records):
        "\n        Return the footer string for the specified records.\n        "
        return ""

    def format(self, records):
        "\n        Format the specified records and return the result as a string.\n        "
        rv = ""
        if len(records) > 0:
            rv = rv + self.formatHeader(records)
            for record in records:
                rv = rv + self.linefmt.format(record)
            rv = rv + self.formatFooter(records)
        return rv


class Filter(object):
    '\n    Filter instances are used to perform arbitrary filtering of LogRecords.\n\n    Loggers and Handlers can optionally use Filter instances to filter\n    records as desired. The base filter class only allows events which are\n    below a certain point in the logger hierarchy. For example, a filter\n    initialized with "A.B" will allow events logged by loggers "A.B",\n    "A.B.C", "A.B.C.D", "A.B.D" etc. but not "A.BB", "B.A.B" etc. If\n    initialized with the empty string, all events are passed.\n    '

    def __init__(self, name=""):
        "\n        Initialize a filter.\n\n        Initialize with the name of the logger which, together with its\n        children, will have its events allowed through the filter. If no\n        name is specified, allow every event.\n        "
        self.name = name
        self.nlen = len(name)

    def filter(self, record):
        "\n        Determine if the specified record is to be logged.\n\n        Returns True if the record should be logged, or False otherwise.\n        If deemed appropriate, the record may be modified in-place.\n        "
        if self.nlen == 0:
            return True
        elif self.name == record.name:
            return True
        elif record.name.find(self.name, 0, self.nlen) != 0:
            return False
        return record.name[self.nlen] == "."


class Filterer(object):
    "\n    A base class for loggers and handlers which allows them to share\n    common code.\n    "

    def __init__(self):
        "\n        Initialize the list of filters to be an empty list.\n        "
        self.filters = []

    def addFilter(self, filter):
        "\n        Add the specified filter to this handler.\n        "
        if not (filter in self.filters):
            self.filters.append(filter)

    def removeFilter(self, filter):
        "\n        Remove the specified filter from this handler.\n        "
        if filter in self.filters:
            self.filters.remove(filter)

    def filter(self, record):
        "\n        Determine if a record is loggable by consulting all the filters.\n\n        The default is to allow the record to be logged; any filter can veto\n        this and the record is then dropped. Returns a zero value if a record\n        is to be dropped, else non-zero.\n\n        .. versionchanged:: 3.2\n\n           Allow filters to be just callables.\n        "
        rv = True
        for f in self.filters:
            if hasattr(f, "filter"):
                result = f.filter(record)
            else:
                result = f(record)
            if not result:
                rv = False
                break
        return rv


_handlers = weakref.WeakValueDictionary()
_handlerList = []


def _removeHandlerRef(wr):
    "\n    Remove a handler reference from the internal cleanup list.\n    "
    (acquire, release, handlers) = (_acquireLock, _releaseLock, _handlerList)
    if acquire and release and handlers:
        acquire()
        try:
            if wr in handlers:
                handlers.remove(wr)
        finally:
            release()


def _addHandlerRef(handler):
    "\n    Add a handler to the internal cleanup list using a weak reference.\n    "
    _acquireLock()
    try:
        _handlerList.append(weakref.ref(handler, _removeHandlerRef))
    finally:
        _releaseLock()


class Handler(Filterer):
    "\n    Handler instances dispatch logging events to specific destinations.\n\n    The base handler class. Acts as a placeholder which defines the Handler\n    interface. Handlers can optionally use Formatter instances to format\n    records as desired. By default, no formatter is specified; in this case,\n    the 'raw' message as determined by record.message is logged.\n    "

    def __init__(self, level=NOTSET):
        "\n        Initializes the instance - basically setting the formatter to None\n        and the filter list to empty.\n        "
        Filterer.__init__(self)
        self._name = None
        self.level = _checkLevel(level)
        self.formatter = None
        _addHandlerRef(self)
        self.createLock()

    def get_name(self):
        return self._name

    def set_name(self, name):
        _acquireLock()
        try:
            if self._name in _handlers:
                del _handlers[self._name]
            self._name = name
            if name:
                _handlers[name] = self
        finally:
            _releaseLock()

    name = property(get_name, set_name)

    def createLock(self):
        "\n        Acquire a thread lock for serializing access to the underlying I/O.\n        "
        self.lock = threading.RLock()
        _register_at_fork_reinit_lock(self)

    def _at_fork_reinit(self):
        self.lock._at_fork_reinit()

    def acquire(self):
        "\n        Acquire the I/O thread lock.\n        "
        if self.lock:
            self.lock.acquire()

    def release(self):
        "\n        Release the I/O thread lock.\n        "
        if self.lock:
            self.lock.release()

    def setLevel(self, level):
        "\n        Set the logging level of this handler.  level must be an int or a str.\n        "
        self.level = _checkLevel(level)

    def format(self, record):
        "\n        Format the specified record.\n\n        If a formatter is set, use it. Otherwise, use the default formatter\n        for the module.\n        "
        if self.formatter:
            fmt = self.formatter
        else:
            fmt = _defaultFormatter
        return fmt.format(record)

    def emit(self, record):
        "\n        Do whatever it takes to actually log the specified logging record.\n\n        This version is intended to be implemented by subclasses and so\n        raises a NotImplementedError.\n        "
        raise NotImplementedError("emit must be implemented by Handler subclasses")

    def handle(self, record):
        "\n        Conditionally emit the specified logging record.\n\n        Emission depends on filters which may have been added to the handler.\n        Wrap the actual emission of the record with acquisition/release of\n        the I/O thread lock. Returns whether the filter passed the record for\n        emission.\n        "
        rv = self.filter(record)
        if rv:
            self.acquire()
            try:
                self.emit(record)
            finally:
                self.release()
        return rv

    def setFormatter(self, fmt):
        "\n        Set the formatter for this handler.\n        "
        self.formatter = fmt

    def flush(self):
        "\n        Ensure all logging output has been flushed.\n\n        This version does nothing and is intended to be implemented by\n        subclasses.\n        "
        pass

    def close(self):
        "\n        Tidy up any resources used by the handler.\n\n        This version removes the handler from an internal map of handlers,\n        _handlers, which is used for handler lookup by name. Subclasses\n        should ensure that this gets called from overridden close()\n        methods.\n        "
        _acquireLock()
        try:
            if self._name and (self._name in _handlers):
                del _handlers[self._name]
        finally:
            _releaseLock()

    def handleError(self, record):
        "\n        Handle errors which occur during an emit() call.\n\n        This method should be called from handlers when an exception is\n        encountered during an emit() call. If raiseExceptions is false,\n        exceptions get silently ignored. This is what is mostly wanted\n        for a logging system - most users will not care about errors in\n        the logging system, they are more interested in application errors.\n        You could, however, replace this with a custom handler if you wish.\n        The record which was being processed is passed in to this method.\n        "
        if raiseExceptions and sys.stderr:
            (t, v, tb) = sys.exc_info()
            try:
                sys.stderr.write("--- Logging error ---\n")
                traceback.print_exception(t, v, tb, None, sys.stderr)
                sys.stderr.write("Call stack:\n")
                frame = tb.tb_frame
                while frame and (
                    os.path.dirname(frame.f_code.co_filename) == __path__[0]
                ):
                    frame = frame.f_back
                if frame:
                    traceback.print_stack(frame, file=sys.stderr)
                else:
                    sys.stderr.write(
                        (
                            "Logged from file %s, line %s\n"
                            % (record.filename, record.lineno)
                        )
                    )
                try:
                    sys.stderr.write(
                        ("Message: %r\nArguments: %s\n" % (record.msg, record.args))
                    )
                except RecursionError:
                    raise
                except Exception:
                    sys.stderr.write(
                        "Unable to print the message and arguments - possible formatting error.\nUse the traceback above to help find the error.\n"
                    )
            except OSError:
                pass
            finally:
                del t, v, tb

    def __repr__(self):
        level = getLevelName(self.level)
        return "<%s (%s)>" % (self.__class__.__name__, level)


class StreamHandler(Handler):
    "\n    A handler class which writes logging records, appropriately formatted,\n    to a stream. Note that this class does not close the stream, as\n    sys.stdout or sys.stderr may be used.\n    "
    terminator = "\n"

    def __init__(self, stream=None):
        "\n        Initialize the handler.\n\n        If stream is not specified, sys.stderr is used.\n        "
        Handler.__init__(self)
        if stream is None:
            stream = sys.stderr
        self.stream = stream

    def flush(self):
        "\n        Flushes the stream.\n        "
        self.acquire()
        try:
            if self.stream and hasattr(self.stream, "flush"):
                self.stream.flush()
        finally:
            self.release()

    def emit(self, record):
        "\n        Emit a record.\n\n        If a formatter is specified, it is used to format the record.\n        The record is then written to the stream with a trailing newline.  If\n        exception information is present, it is formatted using\n        traceback.print_exception and appended to the stream.  If the stream\n        has an 'encoding' attribute, it is used to determine how to do the\n        output to the stream.\n        "
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write((msg + self.terminator))
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)

    def setStream(self, stream):
        "\n        Sets the StreamHandler's stream to the specified value,\n        if it is different.\n\n        Returns the old stream, if the stream was changed, or None\n        if it wasn't.\n        "
        if stream is self.stream:
            result = None
        else:
            result = self.stream
            self.acquire()
            try:
                self.flush()
                self.stream = stream
            finally:
                self.release()
        return result

    def __repr__(self):
        level = getLevelName(self.level)
        name = getattr(self.stream, "name", "")
        name = str(name)
        if name:
            name += " "
        return "<%s %s(%s)>" % (self.__class__.__name__, name, level)


class FileHandler(StreamHandler):
    "\n    A handler class which writes formatted logging records to disk files.\n    "

    def __init__(self, filename, mode="a", encoding=None, delay=False, errors=None):
        "\n        Open the specified file and use it as the stream for logging.\n        "
        filename = os.fspath(filename)
        self.baseFilename = os.path.abspath(filename)
        self.mode = mode
        self.encoding = encoding
        if "b" not in mode:
            self.encoding = io.text_encoding(encoding)
        self.errors = errors
        self.delay = delay
        self._builtin_open = open
        if delay:
            Handler.__init__(self)
            self.stream = None
        else:
            StreamHandler.__init__(self, self._open())

    def close(self):
        "\n        Closes the stream.\n        "
        self.acquire()
        try:
            try:
                if self.stream:
                    try:
                        self.flush()
                    finally:
                        stream = self.stream
                        self.stream = None
                        if hasattr(stream, "close"):
                            stream.close()
            finally:
                StreamHandler.close(self)
        finally:
            self.release()

    def _open(self):
        "\n        Open the current base file with the (original) mode and encoding.\n        Return the resulting stream.\n        "
        open_func = self._builtin_open
        return open_func(
            self.baseFilename, self.mode, encoding=self.encoding, errors=self.errors
        )

    def emit(self, record):
        "\n        Emit a record.\n\n        If the stream was not opened because 'delay' was specified in the\n        constructor, open it before calling the superclass's emit.\n        "
        if self.stream is None:
            self.stream = self._open()
        StreamHandler.emit(self, record)

    def __repr__(self):
        level = getLevelName(self.level)
        return "<%s %s (%s)>" % (self.__class__.__name__, self.baseFilename, level)


class _StderrHandler(StreamHandler):
    "\n    This class is like a StreamHandler using sys.stderr, but always uses\n    whatever sys.stderr is currently set to rather than the value of\n    sys.stderr at handler construction time.\n    "

    def __init__(self, level=NOTSET):
        "\n        Initialize the handler.\n        "
        Handler.__init__(self, level)

    @property
    def stream(self):
        return sys.stderr


_defaultLastResort = _StderrHandler(WARNING)
lastResort = _defaultLastResort


class PlaceHolder(object):
    "\n    PlaceHolder instances are used in the Manager logger hierarchy to take\n    the place of nodes for which no loggers have been defined. This class is\n    intended for internal use only and not as part of the public API.\n    "

    def __init__(self, alogger):
        "\n        Initialize with the specified logger being a child of this placeholder.\n        "
        self.loggerMap = {alogger: None}

    def append(self, alogger):
        "\n        Add the specified logger as a child of this placeholder.\n        "
        if alogger not in self.loggerMap:
            self.loggerMap[alogger] = None


def setLoggerClass(klass):
    "\n    Set the class to be used when instantiating a logger. The class should\n    define __init__() such that only a name argument is required, and the\n    __init__() should call Logger.__init__()\n    "
    if klass != Logger:
        if not issubclass(klass, Logger):
            raise TypeError(
                ("logger not derived from logging.Logger: " + klass.__name__)
            )
    global _loggerClass
    _loggerClass = klass


def getLoggerClass():
    "\n    Return the class to be used when instantiating a logger.\n    "
    return _loggerClass


class Manager(object):
    "\n    There is [under normal circumstances] just one Manager instance, which\n    holds the hierarchy of loggers.\n    "

    def __init__(self, rootnode):
        "\n        Initialize the manager with the root node of the logger hierarchy.\n        "
        self.root = rootnode
        self.disable = 0
        self.emittedNoHandlerWarning = False
        self.loggerDict = {}
        self.loggerClass = None
        self.logRecordFactory = None

    @property
    def disable(self):
        return self._disable

    @disable.setter
    def disable(self, value):
        self._disable = _checkLevel(value)

    def getLogger(self, name):
        '\n        Get a logger with the specified name (channel name), creating it\n        if it doesn\'t yet exist. This name is a dot-separated hierarchical\n        name, such as "a", "a.b", "a.b.c" or similar.\n\n        If a PlaceHolder existed for the specified name [i.e. the logger\n        didn\'t exist but a child of it did], replace it with the created\n        logger and fix up the parent/child references which pointed to the\n        placeholder to now point to the logger.\n        '
        rv = None
        if not isinstance(name, str):
            raise TypeError("A logger name must be a string")
        _acquireLock()
        try:
            if name in self.loggerDict:
                rv = self.loggerDict[name]
                if isinstance(rv, PlaceHolder):
                    ph = rv
                    rv = (self.loggerClass or _loggerClass)(name)
                    rv.manager = self
                    self.loggerDict[name] = rv
                    self._fixupChildren(ph, rv)
                    self._fixupParents(rv)
            else:
                rv = (self.loggerClass or _loggerClass)(name)
                rv.manager = self
                self.loggerDict[name] = rv
                self._fixupParents(rv)
        finally:
            _releaseLock()
        return rv

    def setLoggerClass(self, klass):
        "\n        Set the class to be used when instantiating a logger with this Manager.\n        "
        if klass != Logger:
            if not issubclass(klass, Logger):
                raise TypeError(
                    ("logger not derived from logging.Logger: " + klass.__name__)
                )
        self.loggerClass = klass

    def setLogRecordFactory(self, factory):
        "\n        Set the factory to be used when instantiating a log record with this\n        Manager.\n        "
        self.logRecordFactory = factory

    def _fixupParents(self, alogger):
        "\n        Ensure that there are either loggers or placeholders all the way\n        from the specified logger to the root of the logger hierarchy.\n        "
        name = alogger.name
        i = name.rfind(".")
        rv = None
        while (i > 0) and (not rv):
            substr = name[:i]
            if substr not in self.loggerDict:
                self.loggerDict[substr] = PlaceHolder(alogger)
            else:
                obj = self.loggerDict[substr]
                if isinstance(obj, Logger):
                    rv = obj
                else:
                    assert isinstance(obj, PlaceHolder)
                    obj.append(alogger)
            i = name.rfind(".", 0, (i - 1))
        if not rv:
            rv = self.root
        alogger.parent = rv

    def _fixupChildren(self, ph, alogger):
        "\n        Ensure that children of the placeholder ph are connected to the\n        specified logger.\n        "
        name = alogger.name
        namelen = len(name)
        for c in ph.loggerMap.keys():
            if c.parent.name[:namelen] != name:
                alogger.parent = c.parent
                c.parent = alogger

    def _clear_cache(self):
        "\n        Clear the cache for all loggers in loggerDict\n        Called when level changes are made\n        "
        _acquireLock()
        for logger in self.loggerDict.values():
            if isinstance(logger, Logger):
                logger._cache.clear()
        self.root._cache.clear()
        _releaseLock()


class Logger(Filterer):
    '\n    Instances of the Logger class represent a single logging channel. A\n    "logging channel" indicates an area of an application. Exactly how an\n    "area" is defined is up to the application developer. Since an\n    application can have any number of areas, logging channels are identified\n    by a unique string. Application areas can be nested (e.g. an area\n    of "input processing" might include sub-areas "read CSV files", "read\n    XLS files" and "read Gnumeric files"). To cater for this natural nesting,\n    channel names are organized into a namespace hierarchy where levels are\n    separated by periods, much like the Java or Python package namespace. So\n    in the instance given above, channel names might be "input" for the upper\n    level, and "input.csv", "input.xls" and "input.gnu" for the sub-levels.\n    There is no arbitrary limit to the depth of nesting.\n    '

    def __init__(self, name, level=NOTSET):
        "\n        Initialize the logger with a name and an optional level.\n        "
        Filterer.__init__(self)
        self.name = name
        self.level = _checkLevel(level)
        self.parent = None
        self.propagate = True
        self.handlers = []
        self.disabled = False
        self._cache = {}

    def setLevel(self, level):
        "\n        Set the logging level of this logger.  level must be an int or a str.\n        "
        self.level = _checkLevel(level)
        self.manager._clear_cache()

    def debug(self, msg, *args, **kwargs):
        "\n        Log 'msg % args' with severity 'DEBUG'.\n\n        To pass exception information, use the keyword argument exc_info with\n        a true value, e.g.\n\n        logger.debug(\"Houston, we have a %s\", \"thorny problem\", exc_info=1)\n        "
        if self.isEnabledFor(DEBUG):
            self._log(DEBUG, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        "\n        Log 'msg % args' with severity 'INFO'.\n\n        To pass exception information, use the keyword argument exc_info with\n        a true value, e.g.\n\n        logger.info(\"Houston, we have a %s\", \"interesting problem\", exc_info=1)\n        "
        if self.isEnabledFor(INFO):
            self._log(INFO, msg, args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        "\n        Log 'msg % args' with severity 'WARNING'.\n\n        To pass exception information, use the keyword argument exc_info with\n        a true value, e.g.\n\n        logger.warning(\"Houston, we have a %s\", \"bit of a problem\", exc_info=1)\n        "
        if self.isEnabledFor(WARNING):
            self._log(WARNING, msg, args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        warnings.warn(
            "The 'warn' method is deprecated, use 'warning' instead",
            DeprecationWarning,
            2,
        )
        self.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        "\n        Log 'msg % args' with severity 'ERROR'.\n\n        To pass exception information, use the keyword argument exc_info with\n        a true value, e.g.\n\n        logger.error(\"Houston, we have a %s\", \"major problem\", exc_info=1)\n        "
        if self.isEnabledFor(ERROR):
            self._log(ERROR, msg, args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        "\n        Convenience method for logging an ERROR with exception information.\n        "
        self.error(msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg, *args, **kwargs):
        "\n        Log 'msg % args' with severity 'CRITICAL'.\n\n        To pass exception information, use the keyword argument exc_info with\n        a true value, e.g.\n\n        logger.critical(\"Houston, we have a %s\", \"major disaster\", exc_info=1)\n        "
        if self.isEnabledFor(CRITICAL):
            self._log(CRITICAL, msg, args, **kwargs)

    def fatal(self, msg, *args, **kwargs):
        "\n        Don't use this method, use critical() instead.\n        "
        self.critical(msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        "\n        Log 'msg % args' with the integer severity 'level'.\n\n        To pass exception information, use the keyword argument exc_info with\n        a true value, e.g.\n\n        logger.log(level, \"We have a %s\", \"mysterious problem\", exc_info=1)\n        "
        if not isinstance(level, int):
            if raiseExceptions:
                raise TypeError("level must be an integer")
            else:
                return
        if self.isEnabledFor(level):
            self._log(level, msg, args, **kwargs)

    def findCaller(self, stack_info=False, stacklevel=1):
        "\n        Find the stack frame of the caller so that we can note the source\n        file name, line number and function name.\n        "
        f = currentframe()
        if f is not None:
            f = f.f_back
        orig_f = f
        while f and (stacklevel > 1):
            f = f.f_back
            stacklevel -= 1
        if not f:
            f = orig_f
        rv = ("(unknown file)", 0, "(unknown function)", None)
        while hasattr(f, "f_code"):
            co = f.f_code
            filename = os.path.normcase(co.co_filename)
            if filename == _srcfile:
                f = f.f_back
                continue
            sinfo = None
            if stack_info:
                sio = io.StringIO()
                sio.write("Stack (most recent call last):\n")
                traceback.print_stack(f, file=sio)
                sinfo = sio.getvalue()
                if sinfo[(-1)] == "\n":
                    sinfo = sinfo[:(-1)]
                sio.close()
            rv = (co.co_filename, f.f_lineno, co.co_name, sinfo)
            break
        return rv

    def makeRecord(
        self,
        name,
        level,
        fn,
        lno,
        msg,
        args,
        exc_info,
        func=None,
        extra=None,
        sinfo=None,
    ):
        "\n        A factory method which can be overridden in subclasses to create\n        specialized LogRecords.\n        "
        rv = _logRecordFactory(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in rv.__dict__):
                    raise KeyError(("Attempt to overwrite %r in LogRecord" % key))
                rv.__dict__[key] = extra[key]
        return rv

    def _log(
        self,
        level,
        msg,
        args,
        exc_info=None,
        extra=None,
        stack_info=False,
        stacklevel=1,
    ):
        "\n        Low-level logging routine which creates a LogRecord and then calls\n        all the handlers of this logger to handle the record.\n        "
        sinfo = None
        if _srcfile:
            try:
                (fn, lno, func, sinfo) = self.findCaller(stack_info, stacklevel)
            except ValueError:
                (fn, lno, func) = ("(unknown file)", 0, "(unknown function)")
        else:
            (fn, lno, func) = ("(unknown file)", 0, "(unknown function)")
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
        record = self.makeRecord(
            self.name, level, fn, lno, msg, args, exc_info, func, extra, sinfo
        )
        self.handle(record)

    def handle(self, record):
        "\n        Call the handlers for the specified record.\n\n        This method is used for unpickled records received from a socket, as\n        well as those created locally. Logger-level filtering is applied.\n        "
        if (not self.disabled) and self.filter(record):
            self.callHandlers(record)

    def addHandler(self, hdlr):
        "\n        Add the specified handler to this logger.\n        "
        _acquireLock()
        try:
            if not (hdlr in self.handlers):
                self.handlers.append(hdlr)
        finally:
            _releaseLock()

    def removeHandler(self, hdlr):
        "\n        Remove the specified handler from this logger.\n        "
        _acquireLock()
        try:
            if hdlr in self.handlers:
                self.handlers.remove(hdlr)
        finally:
            _releaseLock()

    def hasHandlers(self):
        '\n        See if this logger has any handlers configured.\n\n        Loop through all handlers for this logger and its parents in the\n        logger hierarchy. Return True if a handler was found, else False.\n        Stop searching up the hierarchy whenever a logger with the "propagate"\n        attribute set to zero is found - that will be the last logger which\n        is checked for the existence of handlers.\n        '
        c = self
        rv = False
        while c:
            if c.handlers:
                rv = True
                break
            if not c.propagate:
                break
            else:
                c = c.parent
        return rv

    def callHandlers(self, record):
        '\n        Pass a record to all relevant handlers.\n\n        Loop through all handlers for this logger and its parents in the\n        logger hierarchy. If no handler was found, output a one-off error\n        message to sys.stderr. Stop searching up the hierarchy whenever a\n        logger with the "propagate" attribute set to zero is found - that\n        will be the last logger whose handlers are called.\n        '
        c = self
        found = 0
        while c:
            for hdlr in c.handlers:
                found = found + 1
                if record.levelno >= hdlr.level:
                    hdlr.handle(record)
            if not c.propagate:
                c = None
            else:
                c = c.parent
        if found == 0:
            if lastResort:
                if record.levelno >= lastResort.level:
                    lastResort.handle(record)
            elif raiseExceptions and (not self.manager.emittedNoHandlerWarning):
                sys.stderr.write(
                    ('No handlers could be found for logger "%s"\n' % self.name)
                )
                self.manager.emittedNoHandlerWarning = True

    def getEffectiveLevel(self):
        "\n        Get the effective level for this logger.\n\n        Loop through this logger and its parents in the logger hierarchy,\n        looking for a non-zero logging level. Return the first one found.\n        "
        logger = self
        while logger:
            if logger.level:
                return logger.level
            logger = logger.parent
        return NOTSET

    def isEnabledFor(self, level):
        "\n        Is this logger enabled for level 'level'?\n        "
        if self.disabled:
            return False
        try:
            return self._cache[level]
        except KeyError:
            _acquireLock()
            try:
                if self.manager.disable >= level:
                    is_enabled = self._cache[level] = False
                else:
                    is_enabled = self._cache[level] = level >= self.getEffectiveLevel()
            finally:
                _releaseLock()
            return is_enabled

    def getChild(self, suffix):
        "\n        Get a logger which is a descendant to this one.\n\n        This is a convenience method, such that\n\n        logging.getLogger('abc').getChild('def.ghi')\n\n        is the same as\n\n        logging.getLogger('abc.def.ghi')\n\n        It's useful, for example, when the parent logger is named using\n        __name__ rather than a literal string.\n        "
        if self.root is not self:
            suffix = ".".join((self.name, suffix))
        return self.manager.getLogger(suffix)

    def __repr__(self):
        level = getLevelName(self.getEffectiveLevel())
        return "<%s %s (%s)>" % (self.__class__.__name__, self.name, level)

    def __reduce__(self):
        if getLogger(self.name) is not self:
            import pickle

            raise pickle.PicklingError("logger cannot be pickled")
        return (getLogger, (self.name,))


class RootLogger(Logger):
    "\n    A root logger is not that different to any other logger, except that\n    it must have a logging level and there is only one instance of it in\n    the hierarchy.\n    "

    def __init__(self, level):
        '\n        Initialize the logger with the name "root".\n        '
        Logger.__init__(self, "root", level)

    def __reduce__(self):
        return (getLogger, ())


_loggerClass = Logger


class LoggerAdapter(object):
    "\n    An adapter for loggers which makes it easier to specify contextual\n    information in logging output.\n    "

    def __init__(self, logger, extra=None):
        '\n        Initialize the adapter with a logger and a dict-like object which\n        provides contextual information. This constructor signature allows\n        easy stacking of LoggerAdapters, if so desired.\n\n        You can effectively pass keyword arguments as shown in the\n        following example:\n\n        adapter = LoggerAdapter(someLogger, dict(p1=v1, p2="v2"))\n        '
        self.logger = logger
        self.extra = extra

    def process(self, msg, kwargs):
        "\n        Process the logging message and keyword arguments passed in to\n        a logging call to insert contextual information. You can either\n        manipulate the message itself, the keyword args or both. Return\n        the message and kwargs modified (or not) to suit your needs.\n\n        Normally, you'll only need to override this one method in a\n        LoggerAdapter subclass for your specific needs.\n        "
        kwargs["extra"] = self.extra
        return (msg, kwargs)

    def debug(self, msg, *args, **kwargs):
        "\n        Delegate a debug call to the underlying logger.\n        "
        self.log(DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        "\n        Delegate an info call to the underlying logger.\n        "
        self.log(INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        "\n        Delegate a warning call to the underlying logger.\n        "
        self.log(WARNING, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        warnings.warn(
            "The 'warn' method is deprecated, use 'warning' instead",
            DeprecationWarning,
            2,
        )
        self.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        "\n        Delegate an error call to the underlying logger.\n        "
        self.log(ERROR, msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        "\n        Delegate an exception call to the underlying logger.\n        "
        self.log(ERROR, msg, *args, exc_info=exc_info, **kwargs)

    def critical(self, msg, *args, **kwargs):
        "\n        Delegate a critical call to the underlying logger.\n        "
        self.log(CRITICAL, msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        "\n        Delegate a log call to the underlying logger, after adding\n        contextual information from this adapter instance.\n        "
        if self.isEnabledFor(level):
            (msg, kwargs) = self.process(msg, kwargs)
            self.logger.log(level, msg, *args, **kwargs)

    def isEnabledFor(self, level):
        "\n        Is this logger enabled for level 'level'?\n        "
        return self.logger.isEnabledFor(level)

    def setLevel(self, level):
        "\n        Set the specified level on the underlying logger.\n        "
        self.logger.setLevel(level)

    def getEffectiveLevel(self):
        "\n        Get the effective level for the underlying logger.\n        "
        return self.logger.getEffectiveLevel()

    def hasHandlers(self):
        "\n        See if the underlying logger has any handlers.\n        "
        return self.logger.hasHandlers()

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        "\n        Low-level log implementation, proxied to allow nested logger adapters.\n        "
        return self.logger._log(
            level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info
        )

    @property
    def manager(self):
        return self.logger.manager

    @manager.setter
    def manager(self, value):
        self.logger.manager = value

    @property
    def name(self):
        return self.logger.name

    def __repr__(self):
        logger = self.logger
        level = getLevelName(logger.getEffectiveLevel())
        return "<%s %s (%s)>" % (self.__class__.__name__, logger.name, level)


root = RootLogger(WARNING)
Logger.root = root
Logger.manager = Manager(Logger.root)


def basicConfig(**kwargs):
    "\n    Do basic configuration for the logging system.\n\n    This function does nothing if the root logger already has handlers\n    configured, unless the keyword argument *force* is set to ``True``.\n    It is a convenience method intended for use by simple scripts\n    to do one-shot configuration of the logging package.\n\n    The default behaviour is to create a StreamHandler which writes to\n    sys.stderr, set a formatter using the BASIC_FORMAT format string, and\n    add the handler to the root logger.\n\n    A number of optional keyword arguments may be specified, which can alter\n    the default behaviour.\n\n    filename  Specifies that a FileHandler be created, using the specified\n              filename, rather than a StreamHandler.\n    filemode  Specifies the mode to open the file, if filename is specified\n              (if filemode is unspecified, it defaults to 'a').\n    format    Use the specified format string for the handler.\n    datefmt   Use the specified date/time format.\n    style     If a format string is specified, use this to specify the\n              type of format string (possible values '%', '{', '$', for\n              %-formatting, :meth:`str.format` and :class:`string.Template`\n              - defaults to '%').\n    level     Set the root logger level to the specified level.\n    stream    Use the specified stream to initialize the StreamHandler. Note\n              that this argument is incompatible with 'filename' - if both\n              are present, 'stream' is ignored.\n    handlers  If specified, this should be an iterable of already created\n              handlers, which will be added to the root handler. Any handler\n              in the list which does not have a formatter assigned will be\n              assigned the formatter created in this function.\n    force     If this keyword  is specified as true, any existing handlers\n              attached to the root logger are removed and closed, before\n              carrying out the configuration as specified by the other\n              arguments.\n    encoding  If specified together with a filename, this encoding is passed to\n              the created FileHandler, causing it to be used when the file is\n              opened.\n    errors    If specified together with a filename, this value is passed to the\n              created FileHandler, causing it to be used when the file is\n              opened in text mode. If not specified, the default value is\n              `backslashreplace`.\n\n    Note that you could specify a stream created using open(filename, mode)\n    rather than passing the filename and mode in. However, it should be\n    remembered that StreamHandler does not close its stream (since it may be\n    using sys.stdout or sys.stderr), whereas FileHandler closes its stream\n    when the handler is closed.\n\n    .. versionchanged:: 3.2\n       Added the ``style`` parameter.\n\n    .. versionchanged:: 3.3\n       Added the ``handlers`` parameter. A ``ValueError`` is now thrown for\n       incompatible arguments (e.g. ``handlers`` specified together with\n       ``filename``/``filemode``, or ``filename``/``filemode`` specified\n       together with ``stream``, or ``handlers`` specified together with\n       ``stream``.\n\n    .. versionchanged:: 3.8\n       Added the ``force`` parameter.\n\n    .. versionchanged:: 3.9\n       Added the ``encoding`` and ``errors`` parameters.\n    "
    _acquireLock()
    try:
        force = kwargs.pop("force", False)
        encoding = kwargs.pop("encoding", None)
        errors = kwargs.pop("errors", "backslashreplace")
        if force:
            for h in root.handlers[:]:
                root.removeHandler(h)
                h.close()
        if len(root.handlers) == 0:
            handlers = kwargs.pop("handlers", None)
            if handlers is None:
                if ("stream" in kwargs) and ("filename" in kwargs):
                    raise ValueError(
                        "'stream' and 'filename' should not be specified together"
                    )
            elif ("stream" in kwargs) or ("filename" in kwargs):
                raise ValueError(
                    "'stream' or 'filename' should not be specified together with 'handlers'"
                )
            if handlers is None:
                filename = kwargs.pop("filename", None)
                mode = kwargs.pop("filemode", "a")
                if filename:
                    if "b" in mode:
                        errors = None
                    else:
                        encoding = io.text_encoding(encoding)
                    h = FileHandler(filename, mode, encoding=encoding, errors=errors)
                else:
                    stream = kwargs.pop("stream", None)
                    h = StreamHandler(stream)
                handlers = [h]
            dfs = kwargs.pop("datefmt", None)
            style = kwargs.pop("style", "%")
            if style not in _STYLES:
                raise ValueError(
                    ("Style must be one of: %s" % ",".join(_STYLES.keys()))
                )
            fs = kwargs.pop("format", _STYLES[style][1])
            fmt = Formatter(fs, dfs, style)
            for h in handlers:
                if h.formatter is None:
                    h.setFormatter(fmt)
                root.addHandler(h)
            level = kwargs.pop("level", None)
            if level is not None:
                root.setLevel(level)
            if kwargs:
                keys = ", ".join(kwargs.keys())
                raise ValueError(("Unrecognised argument(s): %s" % keys))
    finally:
        _releaseLock()


def getLogger(name=None):
    "\n    Return a logger with the specified name, creating it if necessary.\n\n    If no name is specified, return the root logger.\n    "
    if (not name) or (isinstance(name, str) and (name == root.name)):
        return root
    return Logger.manager.getLogger(name)


def critical(msg, *args, **kwargs):
    "\n    Log a message with severity 'CRITICAL' on the root logger. If the logger\n    has no handlers, call basicConfig() to add a console handler with a\n    pre-defined format.\n    "
    if len(root.handlers) == 0:
        basicConfig()
    root.critical(msg, *args, **kwargs)


def fatal(msg, *args, **kwargs):
    "\n    Don't use this function, use critical() instead.\n    "
    critical(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    "\n    Log a message with severity 'ERROR' on the root logger. If the logger has\n    no handlers, call basicConfig() to add a console handler with a pre-defined\n    format.\n    "
    if len(root.handlers) == 0:
        basicConfig()
    root.error(msg, *args, **kwargs)


def exception(msg, *args, exc_info=True, **kwargs):
    "\n    Log a message with severity 'ERROR' on the root logger, with exception\n    information. If the logger has no handlers, basicConfig() is called to add\n    a console handler with a pre-defined format.\n    "
    error(msg, *args, exc_info=exc_info, **kwargs)


def warning(msg, *args, **kwargs):
    "\n    Log a message with severity 'WARNING' on the root logger. If the logger has\n    no handlers, call basicConfig() to add a console handler with a pre-defined\n    format.\n    "
    if len(root.handlers) == 0:
        basicConfig()
    root.warning(msg, *args, **kwargs)


def warn(msg, *args, **kwargs):
    warnings.warn(
        "The 'warn' function is deprecated, use 'warning' instead",
        DeprecationWarning,
        2,
    )
    warning(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    "\n    Log a message with severity 'INFO' on the root logger. If the logger has\n    no handlers, call basicConfig() to add a console handler with a pre-defined\n    format.\n    "
    if len(root.handlers) == 0:
        basicConfig()
    root.info(msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    "\n    Log a message with severity 'DEBUG' on the root logger. If the logger has\n    no handlers, call basicConfig() to add a console handler with a pre-defined\n    format.\n    "
    if len(root.handlers) == 0:
        basicConfig()
    root.debug(msg, *args, **kwargs)


def log(level, msg, *args, **kwargs):
    "\n    Log 'msg % args' with the integer severity 'level' on the root logger. If\n    the logger has no handlers, call basicConfig() to add a console handler\n    with a pre-defined format.\n    "
    if len(root.handlers) == 0:
        basicConfig()
    root.log(level, msg, *args, **kwargs)


def disable(level=CRITICAL):
    "\n    Disable all logging calls of severity 'level' and below.\n    "
    root.manager.disable = level
    root.manager._clear_cache()


def shutdown(handlerList=_handlerList):
    "\n    Perform any cleanup actions in the logging system (e.g. flushing\n    buffers).\n\n    Should be called at application exit.\n    "
    for wr in reversed(handlerList[:]):
        try:
            h = wr()
            if h:
                try:
                    h.acquire()
                    h.flush()
                    h.close()
                except (OSError, ValueError):
                    pass
                finally:
                    h.release()
        except:
            if raiseExceptions:
                raise


import atexit

atexit.register(shutdown)


class NullHandler(Handler):
    '\n    This handler does nothing. It\'s intended to be used to avoid the\n    "No handlers could be found for logger XXX" one-off warning. This is\n    important for library code, which may contain code to log events. If a user\n    of the library does not configure logging, the one-off warning might be\n    produced; to avoid this, the library developer simply needs to instantiate\n    a NullHandler and add it to the top-level logger of the library module or\n    package.\n    '

    def handle(self, record):
        "Stub."

    def emit(self, record):
        "Stub."

    def createLock(self):
        self.lock = None

    def _at_fork_reinit(self):
        pass


_warnings_showwarning = None


def _showwarning(message, category, filename, lineno, file=None, line=None):
    '\n    Implementation of showwarnings which redirects to logging, which will first\n    check to see if the file parameter is None. If a file is specified, it will\n    delegate to the original warnings implementation of showwarning. Otherwise,\n    it will call warnings.formatwarning and will log the resulting string to a\n    warnings logger named "py.warnings" with level logging.WARNING.\n    '
    if file is not None:
        if _warnings_showwarning is not None:
            _warnings_showwarning(message, category, filename, lineno, file, line)
    else:
        s = warnings.formatwarning(message, category, filename, lineno, line)
        logger = getLogger("py.warnings")
        if not logger.handlers:
            logger.addHandler(NullHandler())
        logger.warning("%s", s)


def captureWarnings(capture):
    "\n    If capture is true, redirect all warnings to the logging package.\n    If capture is False, ensure that warnings are not redirected to logging\n    but to their original destinations.\n    "
    global _warnings_showwarning
    if capture:
        if _warnings_showwarning is None:
            _warnings_showwarning = warnings.showwarning
            warnings.showwarning = _showwarning
    elif _warnings_showwarning is not None:
        warnings.showwarning = _warnings_showwarning
        _warnings_showwarning = None
