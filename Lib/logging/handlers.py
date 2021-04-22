"\nAdditional handlers for the logging package for Python. The core package is\nbased on PEP 282 and comments thereto in comp.lang.python.\n\nCopyright (C) 2001-2016 Vinay Sajip. All Rights Reserved.\n\nTo use, simply 'import logging.handlers' and log away!\n"
import io, logging, socket, os, pickle, struct, time, re
from stat import ST_DEV, ST_INO, ST_MTIME
import queue
import threading
import copy

DEFAULT_TCP_LOGGING_PORT = 9020
DEFAULT_UDP_LOGGING_PORT = 9021
DEFAULT_HTTP_LOGGING_PORT = 9022
DEFAULT_SOAP_LOGGING_PORT = 9023
SYSLOG_UDP_PORT = 514
SYSLOG_TCP_PORT = 514
_MIDNIGHT = (24 * 60) * 60


class BaseRotatingHandler(logging.FileHandler):
    "\n    Base class for handlers that rotate log files at a certain point.\n    Not meant to be instantiated directly.  Instead, use RotatingFileHandler\n    or TimedRotatingFileHandler.\n    "
    namer = None
    rotator = None

    def __init__(self, filename, mode, encoding=None, delay=False, errors=None):
        "\n        Use the specified filename for streamed logging\n        "
        logging.FileHandler.__init__(
            self, filename, mode=mode, encoding=encoding, delay=delay, errors=errors
        )
        self.mode = mode
        self.encoding = encoding
        self.errors = errors

    def emit(self, record):
        "\n        Emit a record.\n\n        Output the record to the file, catering for rollover as described\n        in doRollover().\n        "
        try:
            if self.shouldRollover(record):
                self.doRollover()
            logging.FileHandler.emit(self, record)
        except Exception:
            self.handleError(record)

    def rotation_filename(self, default_name):
        "\n        Modify the filename of a log file when rotating.\n\n        This is provided so that a custom filename can be provided.\n\n        The default implementation calls the 'namer' attribute of the\n        handler, if it's callable, passing the default name to\n        it. If the attribute isn't callable (the default is None), the name\n        is returned unchanged.\n\n        :param default_name: The default name for the log file.\n        "
        if not callable(self.namer):
            result = default_name
        else:
            result = self.namer(default_name)
        return result

    def rotate(self, source, dest):
        "\n        When rotating, rotate the current log.\n\n        The default implementation calls the 'rotator' attribute of the\n        handler, if it's callable, passing the source and dest arguments to\n        it. If the attribute isn't callable (the default is None), the source\n        is simply renamed to the destination.\n\n        :param source: The source filename. This is normally the base\n                       filename, e.g. 'test.log'\n        :param dest:   The destination filename. This is normally\n                       what the source is rotated to, e.g. 'test.log.1'.\n        "
        if not callable(self.rotator):
            if os.path.exists(source):
                os.rename(source, dest)
        else:
            self.rotator(source, dest)


class RotatingFileHandler(BaseRotatingHandler):
    "\n    Handler for logging to a set of files, which switches from one file\n    to the next when the current file reaches a certain size.\n    "

    def __init__(
        self,
        filename,
        mode="a",
        maxBytes=0,
        backupCount=0,
        encoding=None,
        delay=False,
        errors=None,
    ):
        '\n        Open the specified file and use it as the stream for logging.\n\n        By default, the file grows indefinitely. You can specify particular\n        values of maxBytes and backupCount to allow the file to rollover at\n        a predetermined size.\n\n        Rollover occurs whenever the current log file is nearly maxBytes in\n        length. If backupCount is >= 1, the system will successively create\n        new files with the same pathname as the base file, but with extensions\n        ".1", ".2" etc. appended to it. For example, with a backupCount of 5\n        and a base file name of "app.log", you would get "app.log",\n        "app.log.1", "app.log.2", ... through to "app.log.5". The file being\n        written to is always "app.log" - when it gets filled up, it is closed\n        and renamed to "app.log.1", and if files "app.log.1", "app.log.2" etc.\n        exist, then they are renamed to "app.log.2", "app.log.3" etc.\n        respectively.\n\n        If maxBytes is zero, rollover never occurs.\n        '
        if maxBytes > 0:
            mode = "a"
        if "b" not in mode:
            encoding = io.text_encoding(encoding)
        BaseRotatingHandler.__init__(
            self, filename, mode, encoding=encoding, delay=delay, errors=errors
        )
        self.maxBytes = maxBytes
        self.backupCount = backupCount

    def doRollover(self):
        "\n        Do a rollover, as described in __init__().\n        "
        if self.stream:
            self.stream.close()
            self.stream = None
        if self.backupCount > 0:
            for i in range((self.backupCount - 1), 0, (-1)):
                sfn = self.rotation_filename(("%s.%d" % (self.baseFilename, i)))
                dfn = self.rotation_filename(("%s.%d" % (self.baseFilename, (i + 1))))
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.rotation_filename((self.baseFilename + ".1"))
            if os.path.exists(dfn):
                os.remove(dfn)
            self.rotate(self.baseFilename, dfn)
        if not self.delay:
            self.stream = self._open()

    def shouldRollover(self, record):
        "\n        Determine if rollover should occur.\n\n        Basically, see if the supplied record would cause the file to exceed\n        the size limit we have.\n        "
        if self.stream is None:
            self.stream = self._open()
        if self.maxBytes > 0:
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)
            if (self.stream.tell() + len(msg)) >= self.maxBytes:
                return 1
        return 0


class TimedRotatingFileHandler(BaseRotatingHandler):
    "\n    Handler for logging to a file, rotating the log file at certain timed\n    intervals.\n\n    If backupCount is > 0, when rollover is done, no more than backupCount\n    files are kept - the oldest ones are deleted.\n    "

    def __init__(
        self,
        filename,
        when="h",
        interval=1,
        backupCount=0,
        encoding=None,
        delay=False,
        utc=False,
        atTime=None,
        errors=None,
    ):
        encoding = io.text_encoding(encoding)
        BaseRotatingHandler.__init__(
            self, filename, "a", encoding=encoding, delay=delay, errors=errors
        )
        self.when = when.upper()
        self.backupCount = backupCount
        self.utc = utc
        self.atTime = atTime
        if self.when == "S":
            self.interval = 1
            self.suffix = "%Y-%m-%d_%H-%M-%S"
            self.extMatch = "^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}(\\.\\w+)?$"
        elif self.when == "M":
            self.interval = 60
            self.suffix = "%Y-%m-%d_%H-%M"
            self.extMatch = "^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}(\\.\\w+)?$"
        elif self.when == "H":
            self.interval = 60 * 60
            self.suffix = "%Y-%m-%d_%H"
            self.extMatch = "^\\d{4}-\\d{2}-\\d{2}_\\d{2}(\\.\\w+)?$"
        elif (self.when == "D") or (self.when == "MIDNIGHT"):
            self.interval = (60 * 60) * 24
            self.suffix = "%Y-%m-%d"
            self.extMatch = "^\\d{4}-\\d{2}-\\d{2}(\\.\\w+)?$"
        elif self.when.startswith("W"):
            self.interval = ((60 * 60) * 24) * 7
            if len(self.when) != 2:
                raise ValueError(
                    (
                        "You must specify a day for weekly rollover from 0 to 6 (0 is Monday): %s"
                        % self.when
                    )
                )
            if (self.when[1] < "0") or (self.when[1] > "6"):
                raise ValueError(
                    ("Invalid day specified for weekly rollover: %s" % self.when)
                )
            self.dayOfWeek = int(self.when[1])
            self.suffix = "%Y-%m-%d"
            self.extMatch = "^\\d{4}-\\d{2}-\\d{2}(\\.\\w+)?$"
        else:
            raise ValueError(("Invalid rollover interval specified: %s" % self.when))
        self.extMatch = re.compile(self.extMatch, re.ASCII)
        self.interval = self.interval * interval
        filename = self.baseFilename
        if os.path.exists(filename):
            t = os.stat(filename)[ST_MTIME]
        else:
            t = int(time.time())
        self.rolloverAt = self.computeRollover(t)

    def computeRollover(self, currentTime):
        "\n        Work out the rollover time based on the specified time.\n        "
        result = currentTime + self.interval
        if (self.when == "MIDNIGHT") or self.when.startswith("W"):
            if self.utc:
                t = time.gmtime(currentTime)
            else:
                t = time.localtime(currentTime)
            currentHour = t[3]
            currentMinute = t[4]
            currentSecond = t[5]
            currentDay = t[6]
            if self.atTime is None:
                rotate_ts = _MIDNIGHT
            else:
                rotate_ts = (
                    ((self.atTime.hour * 60) + self.atTime.minute) * 60
                ) + self.atTime.second
            r = rotate_ts - (
                (((currentHour * 60) + currentMinute) * 60) + currentSecond
            )
            if r < 0:
                r += _MIDNIGHT
                currentDay = (currentDay + 1) % 7
            result = currentTime + r
            if self.when.startswith("W"):
                day = currentDay
                if day != self.dayOfWeek:
                    if day < self.dayOfWeek:
                        daysToWait = self.dayOfWeek - day
                    else:
                        daysToWait = ((6 - day) + self.dayOfWeek) + 1
                    newRolloverAt = result + (daysToWait * ((60 * 60) * 24))
                    if not self.utc:
                        dstNow = t[(-1)]
                        dstAtRollover = time.localtime(newRolloverAt)[(-1)]
                        if dstNow != dstAtRollover:
                            if not dstNow:
                                addend = -3600
                            else:
                                addend = 3600
                            newRolloverAt += addend
                    result = newRolloverAt
        return result

    def shouldRollover(self, record):
        "\n        Determine if rollover should occur.\n\n        record is not used, as we are just comparing times, but it is needed so\n        the method signatures are the same\n        "
        t = int(time.time())
        if t >= self.rolloverAt:
            return 1
        return 0

    def getFilesToDelete(self):
        "\n        Determine the files to delete when rolling over.\n\n        More specific than the earlier method, which just used glob.glob().\n        "
        (dirName, baseName) = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix = baseName + "."
        plen = len(prefix)
        for fileName in fileNames:
            if fileName[:plen] == prefix:
                suffix = fileName[plen:]
                if self.extMatch.match(suffix):
                    result.append(os.path.join(dirName, fileName))
        if len(result) < self.backupCount:
            result = []
        else:
            result.sort()
            result = result[: (len(result) - self.backupCount)]
        return result

    def doRollover(self):
        "\n        do a rollover; in this case, a date/time stamp is appended to the filename\n        when the rollover happens.  However, you want the file to be named for the\n        start of the interval, not the current time.  If there is a backup count,\n        then we have to get a list of matching filenames, sort them and remove\n        the one with the oldest suffix.\n        "
        if self.stream:
            self.stream.close()
            self.stream = None
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[(-1)]
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
            dstThen = timeTuple[(-1)]
            if dstNow != dstThen:
                if dstNow:
                    addend = 3600
                else:
                    addend = -3600
                timeTuple = time.localtime((t + addend))
        dfn = self.rotation_filename(
            ((self.baseFilename + ".") + time.strftime(self.suffix, timeTuple))
        )
        if os.path.exists(dfn):
            os.remove(dfn)
        self.rotate(self.baseFilename, dfn)
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        if ((self.when == "MIDNIGHT") or self.when.startswith("W")) and (not self.utc):
            dstAtRollover = time.localtime(newRolloverAt)[(-1)]
            if dstNow != dstAtRollover:
                if not dstNow:
                    addend = -3600
                else:
                    addend = 3600
                newRolloverAt += addend
        self.rolloverAt = newRolloverAt


class WatchedFileHandler(logging.FileHandler):
    "\n    A handler for logging to a file, which watches the file\n    to see if it has changed while in use. This can happen because of\n    usage of programs such as newsyslog and logrotate which perform\n    log file rotation. This handler, intended for use under Unix,\n    watches the file to see if it has changed since the last emit.\n    (A file has changed if its device or inode have changed.)\n    If it has changed, the old file stream is closed, and the file\n    opened to get a new stream.\n\n    This handler is not appropriate for use under Windows, because\n    under Windows open files cannot be moved or renamed - logging\n    opens the files with exclusive locks - and so there is no need\n    for such a handler. Furthermore, ST_INO is not supported under\n    Windows; stat always returns zero for this value.\n\n    This handler is based on a suggestion and patch by Chad J.\n    Schroeder.\n    "

    def __init__(self, filename, mode="a", encoding=None, delay=False, errors=None):
        if "b" not in mode:
            encoding = io.text_encoding(encoding)
        logging.FileHandler.__init__(
            self, filename, mode=mode, encoding=encoding, delay=delay, errors=errors
        )
        (self.dev, self.ino) = ((-1), (-1))
        self._statstream()

    def _statstream(self):
        if self.stream:
            sres = os.fstat(self.stream.fileno())
            (self.dev, self.ino) = (sres[ST_DEV], sres[ST_INO])

    def reopenIfNeeded(self):
        "\n        Reopen log file if needed.\n\n        Checks if the underlying file has changed, and if it\n        has, close the old stream and reopen the file to get the\n        current stream.\n        "
        try:
            sres = os.stat(self.baseFilename)
        except FileNotFoundError:
            sres = None
        if (not sres) or (sres[ST_DEV] != self.dev) or (sres[ST_INO] != self.ino):
            if self.stream is not None:
                self.stream.flush()
                self.stream.close()
                self.stream = None
                self.stream = self._open()
                self._statstream()

    def emit(self, record):
        "\n        Emit a record.\n\n        If underlying file has changed, reopen the file before emitting the\n        record to it.\n        "
        self.reopenIfNeeded()
        logging.FileHandler.emit(self, record)


class SocketHandler(logging.Handler):
    "\n    A handler class which writes logging records, in pickle format, to\n    a streaming socket. The socket is kept open across logging calls.\n    If the peer resets it, an attempt is made to reconnect on the next call.\n    The pickle which is sent is that of the LogRecord's attribute dictionary\n    (__dict__), so that the receiver does not need to have the logging module\n    installed in order to process the logging event.\n\n    To unpickle the record at the receiving end into a LogRecord, use the\n    makeLogRecord function.\n    "

    def __init__(self, host, port):
        "\n        Initializes the handler with a specific host address and port.\n\n        When the attribute *closeOnError* is set to True - if a socket error\n        occurs, the socket is silently closed and then reopened on the next\n        logging call.\n        "
        logging.Handler.__init__(self)
        self.host = host
        self.port = port
        if port is None:
            self.address = host
        else:
            self.address = (host, port)
        self.sock = None
        self.closeOnError = False
        self.retryTime = None
        self.retryStart = 1.0
        self.retryMax = 30.0
        self.retryFactor = 2.0

    def makeSocket(self, timeout=1):
        "\n        A factory method which allows subclasses to define the precise\n        type of socket they want.\n        "
        if self.port is not None:
            result = socket.create_connection(self.address, timeout=timeout)
        else:
            result = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            result.settimeout(timeout)
            try:
                result.connect(self.address)
            except OSError:
                result.close()
                raise
        return result

    def createSocket(self):
        "\n        Try to create a socket, using an exponential backoff with\n        a max retry time. Thanks to Robert Olson for the original patch\n        (SF #815911) which has been slightly refactored.\n        "
        now = time.time()
        if self.retryTime is None:
            attempt = True
        else:
            attempt = now >= self.retryTime
        if attempt:
            try:
                self.sock = self.makeSocket()
                self.retryTime = None
            except OSError:
                if self.retryTime is None:
                    self.retryPeriod = self.retryStart
                else:
                    self.retryPeriod = self.retryPeriod * self.retryFactor
                    if self.retryPeriod > self.retryMax:
                        self.retryPeriod = self.retryMax
                self.retryTime = now + self.retryPeriod

    def send(self, s):
        "\n        Send a pickled string to the socket.\n\n        This function allows for partial sends which can happen when the\n        network is busy.\n        "
        if self.sock is None:
            self.createSocket()
        if self.sock:
            try:
                self.sock.sendall(s)
            except OSError:
                self.sock.close()
                self.sock = None

    def makePickle(self, record):
        "\n        Pickles the record in binary format with a length prefix, and\n        returns it ready for transmission across the socket.\n        "
        ei = record.exc_info
        if ei:
            dummy = self.format(record)
        d = dict(record.__dict__)
        d["msg"] = record.getMessage()
        d["args"] = None
        d["exc_info"] = None
        d.pop("message", None)
        s = pickle.dumps(d, 1)
        slen = struct.pack(">L", len(s))
        return slen + s

    def handleError(self, record):
        "\n        Handle an error during logging.\n\n        An error has occurred during logging. Most likely cause -\n        connection lost. Close the socket so that we can retry on the\n        next event.\n        "
        if self.closeOnError and self.sock:
            self.sock.close()
            self.sock = None
        else:
            logging.Handler.handleError(self, record)

    def emit(self, record):
        "\n        Emit a record.\n\n        Pickles the record and writes it to the socket in binary format.\n        If there is an error with the socket, silently drop the packet.\n        If there was a problem with the socket, re-establishes the\n        socket.\n        "
        try:
            s = self.makePickle(record)
            self.send(s)
        except Exception:
            self.handleError(record)

    def close(self):
        "\n        Closes the socket.\n        "
        self.acquire()
        try:
            sock = self.sock
            if sock:
                self.sock = None
                sock.close()
            logging.Handler.close(self)
        finally:
            self.release()


class DatagramHandler(SocketHandler):
    "\n    A handler class which writes logging records, in pickle format, to\n    a datagram socket.  The pickle which is sent is that of the LogRecord's\n    attribute dictionary (__dict__), so that the receiver does not need to\n    have the logging module installed in order to process the logging event.\n\n    To unpickle the record at the receiving end into a LogRecord, use the\n    makeLogRecord function.\n\n    "

    def __init__(self, host, port):
        "\n        Initializes the handler with a specific host address and port.\n        "
        SocketHandler.__init__(self, host, port)
        self.closeOnError = False

    def makeSocket(self):
        "\n        The factory method of SocketHandler is here overridden to create\n        a UDP socket (SOCK_DGRAM).\n        "
        if self.port is None:
            family = socket.AF_UNIX
        else:
            family = socket.AF_INET
        s = socket.socket(family, socket.SOCK_DGRAM)
        return s

    def send(self, s):
        "\n        Send a pickled string to a socket.\n\n        This function no longer allows for partial sends which can happen\n        when the network is busy - UDP does not guarantee delivery and\n        can deliver packets out of sequence.\n        "
        if self.sock is None:
            self.createSocket()
        self.sock.sendto(s, self.address)


class SysLogHandler(logging.Handler):
    "\n    A handler class which sends formatted logging records to a syslog\n    server. Based on Sam Rushing's syslog module:\n    http://www.nightmare.com/squirl/python-ext/misc/syslog.py\n    Contributed by Nicolas Untz (after which minor refactoring changes\n    have been made).\n    "
    LOG_EMERG = 0
    LOG_ALERT = 1
    LOG_CRIT = 2
    LOG_ERR = 3
    LOG_WARNING = 4
    LOG_NOTICE = 5
    LOG_INFO = 6
    LOG_DEBUG = 7
    LOG_KERN = 0
    LOG_USER = 1
    LOG_MAIL = 2
    LOG_DAEMON = 3
    LOG_AUTH = 4
    LOG_SYSLOG = 5
    LOG_LPR = 6
    LOG_NEWS = 7
    LOG_UUCP = 8
    LOG_CRON = 9
    LOG_AUTHPRIV = 10
    LOG_FTP = 11
    LOG_NTP = 12
    LOG_SECURITY = 13
    LOG_CONSOLE = 14
    LOG_SOLCRON = 15
    LOG_LOCAL0 = 16
    LOG_LOCAL1 = 17
    LOG_LOCAL2 = 18
    LOG_LOCAL3 = 19
    LOG_LOCAL4 = 20
    LOG_LOCAL5 = 21
    LOG_LOCAL6 = 22
    LOG_LOCAL7 = 23
    priority_names = {
        "alert": LOG_ALERT,
        "crit": LOG_CRIT,
        "critical": LOG_CRIT,
        "debug": LOG_DEBUG,
        "emerg": LOG_EMERG,
        "err": LOG_ERR,
        "error": LOG_ERR,
        "info": LOG_INFO,
        "notice": LOG_NOTICE,
        "panic": LOG_EMERG,
        "warn": LOG_WARNING,
        "warning": LOG_WARNING,
    }
    facility_names = {
        "auth": LOG_AUTH,
        "authpriv": LOG_AUTHPRIV,
        "console": LOG_CONSOLE,
        "cron": LOG_CRON,
        "daemon": LOG_DAEMON,
        "ftp": LOG_FTP,
        "kern": LOG_KERN,
        "lpr": LOG_LPR,
        "mail": LOG_MAIL,
        "news": LOG_NEWS,
        "ntp": LOG_NTP,
        "security": LOG_SECURITY,
        "solaris-cron": LOG_SOLCRON,
        "syslog": LOG_SYSLOG,
        "user": LOG_USER,
        "uucp": LOG_UUCP,
        "local0": LOG_LOCAL0,
        "local1": LOG_LOCAL1,
        "local2": LOG_LOCAL2,
        "local3": LOG_LOCAL3,
        "local4": LOG_LOCAL4,
        "local5": LOG_LOCAL5,
        "local6": LOG_LOCAL6,
        "local7": LOG_LOCAL7,
    }
    priority_map = {
        "DEBUG": "debug",
        "INFO": "info",
        "WARNING": "warning",
        "ERROR": "error",
        "CRITICAL": "critical",
    }

    def __init__(
        self, address=("localhost", SYSLOG_UDP_PORT), facility=LOG_USER, socktype=None
    ):
        '\n        Initialize a handler.\n\n        If address is specified as a string, a UNIX socket is used. To log to a\n        local syslogd, "SysLogHandler(address="/dev/log")" can be used.\n        If facility is not specified, LOG_USER is used. If socktype is\n        specified as socket.SOCK_DGRAM or socket.SOCK_STREAM, that specific\n        socket type will be used. For Unix sockets, you can also specify a\n        socktype of None, in which case socket.SOCK_DGRAM will be used, falling\n        back to socket.SOCK_STREAM.\n        '
        logging.Handler.__init__(self)
        self.address = address
        self.facility = facility
        self.socktype = socktype
        if isinstance(address, str):
            self.unixsocket = True
            try:
                self._connect_unixsocket(address)
            except OSError:
                pass
        else:
            self.unixsocket = False
            if socktype is None:
                socktype = socket.SOCK_DGRAM
            (host, port) = address
            ress = socket.getaddrinfo(host, port, 0, socktype)
            if not ress:
                raise OSError("getaddrinfo returns an empty list")
            for res in ress:
                (af, socktype, proto, _, sa) = res
                err = sock = None
                try:
                    sock = socket.socket(af, socktype, proto)
                    if socktype == socket.SOCK_STREAM:
                        sock.connect(sa)
                    break
                except OSError as exc:
                    err = exc
                    if sock is not None:
                        sock.close()
            if err is not None:
                raise err
            self.socket = sock
            self.socktype = socktype

    def _connect_unixsocket(self, address):
        use_socktype = self.socktype
        if use_socktype is None:
            use_socktype = socket.SOCK_DGRAM
        self.socket = socket.socket(socket.AF_UNIX, use_socktype)
        try:
            self.socket.connect(address)
            self.socktype = use_socktype
        except OSError:
            self.socket.close()
            if self.socktype is not None:
                raise
            use_socktype = socket.SOCK_STREAM
            self.socket = socket.socket(socket.AF_UNIX, use_socktype)
            try:
                self.socket.connect(address)
                self.socktype = use_socktype
            except OSError:
                self.socket.close()
                raise

    def encodePriority(self, facility, priority):
        "\n        Encode the facility and priority. You can pass in strings or\n        integers - if strings are passed, the facility_names and\n        priority_names mapping dictionaries are used to convert them to\n        integers.\n        "
        if isinstance(facility, str):
            facility = self.facility_names[facility]
        if isinstance(priority, str):
            priority = self.priority_names[priority]
        return (facility << 3) | priority

    def close(self):
        "\n        Closes the socket.\n        "
        self.acquire()
        try:
            self.socket.close()
            logging.Handler.close(self)
        finally:
            self.release()

    def mapPriority(self, levelName):
        "\n        Map a logging level name to a key in the priority_names map.\n        This is useful in two scenarios: when custom levels are being\n        used, and in the case where you can't do a straightforward\n        mapping by lowercasing the logging level name because of locale-\n        specific issues (see SF #1524081).\n        "
        return self.priority_map.get(levelName, "warning")

    ident = ""
    append_nul = True

    def emit(self, record):
        "\n        Emit a record.\n\n        The record is formatted, and then sent to the syslog server. If\n        exception information is present, it is NOT sent to the server.\n        "
        try:
            msg = self.format(record)
            if self.ident:
                msg = self.ident + msg
            if self.append_nul:
                msg += "\x00"
            prio = "<%d>" % self.encodePriority(
                self.facility, self.mapPriority(record.levelname)
            )
            prio = prio.encode("utf-8")
            msg = msg.encode("utf-8")
            msg = prio + msg
            if self.unixsocket:
                try:
                    self.socket.send(msg)
                except OSError:
                    self.socket.close()
                    self._connect_unixsocket(self.address)
                    self.socket.send(msg)
            elif self.socktype == socket.SOCK_DGRAM:
                self.socket.sendto(msg, self.address)
            else:
                self.socket.sendall(msg)
        except Exception:
            self.handleError(record)


class SMTPHandler(logging.Handler):
    "\n    A handler class which sends an SMTP email for each logging event.\n    "

    def __init__(
        self,
        mailhost,
        fromaddr,
        toaddrs,
        subject,
        credentials=None,
        secure=None,
        timeout=5.0,
    ):
        "\n        Initialize the handler.\n\n        Initialize the instance with the from and to addresses and subject\n        line of the email. To specify a non-standard SMTP port, use the\n        (host, port) tuple format for the mailhost argument. To specify\n        authentication credentials, supply a (username, password) tuple\n        for the credentials argument. To specify the use of a secure\n        protocol (TLS), pass in a tuple for the secure argument. This will\n        only be used when authentication credentials are supplied. The tuple\n        will be either an empty tuple, or a single-value tuple with the name\n        of a keyfile, or a 2-value tuple with the names of the keyfile and\n        certificate file. (This tuple is passed to the `starttls` method).\n        A timeout in seconds can be specified for the SMTP connection (the\n        default is one second).\n        "
        logging.Handler.__init__(self)
        if isinstance(mailhost, (list, tuple)):
            (self.mailhost, self.mailport) = mailhost
        else:
            (self.mailhost, self.mailport) = (mailhost, None)
        if isinstance(credentials, (list, tuple)):
            (self.username, self.password) = credentials
        else:
            self.username = None
        self.fromaddr = fromaddr
        if isinstance(toaddrs, str):
            toaddrs = [toaddrs]
        self.toaddrs = toaddrs
        self.subject = subject
        self.secure = secure
        self.timeout = timeout

    def getSubject(self, record):
        "\n        Determine the subject for the email.\n\n        If you want to specify a subject line which is record-dependent,\n        override this method.\n        "
        return self.subject

    def emit(self, record):
        "\n        Emit a record.\n\n        Format the record and send it to the specified addressees.\n        "
        try:
            import smtplib
            from email.message import EmailMessage
            import email.utils

            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port, timeout=self.timeout)
            msg = EmailMessage()
            msg["From"] = self.fromaddr
            msg["To"] = ",".join(self.toaddrs)
            msg["Subject"] = self.getSubject(record)
            msg["Date"] = email.utils.localtime()
            msg.set_content(self.format(record))
            if self.username:
                if self.secure is not None:
                    smtp.ehlo()
                    smtp.starttls(*self.secure)
                    smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.send_message(msg)
            smtp.quit()
        except Exception:
            self.handleError(record)


class NTEventLogHandler(logging.Handler):
    "\n    A handler class which sends events to the NT Event Log. Adds a\n    registry entry for the specified application name. If no dllname is\n    provided, win32service.pyd (which contains some basic message\n    placeholders) is used. Note that use of these placeholders will make\n    your event logs big, as the entire message source is held in the log.\n    If you want slimmer logs, you have to pass in the name of your own DLL\n    which contains the message definitions you want to use in the event log.\n    "

    def __init__(self, appname, dllname=None, logtype="Application"):
        logging.Handler.__init__(self)
        try:
            import win32evtlogutil, win32evtlog

            self.appname = appname
            self._welu = win32evtlogutil
            if not dllname:
                dllname = os.path.split(self._welu.__file__)
                dllname = os.path.split(dllname[0])
                dllname = os.path.join(dllname[0], "win32service.pyd")
            self.dllname = dllname
            self.logtype = logtype
            self._welu.AddSourceToRegistry(appname, dllname, logtype)
            self.deftype = win32evtlog.EVENTLOG_ERROR_TYPE
            self.typemap = {
                logging.DEBUG: win32evtlog.EVENTLOG_INFORMATION_TYPE,
                logging.INFO: win32evtlog.EVENTLOG_INFORMATION_TYPE,
                logging.WARNING: win32evtlog.EVENTLOG_WARNING_TYPE,
                logging.ERROR: win32evtlog.EVENTLOG_ERROR_TYPE,
                logging.CRITICAL: win32evtlog.EVENTLOG_ERROR_TYPE,
            }
        except ImportError:
            print(
                "The Python Win32 extensions for NT (service, event logging) appear not to be available."
            )
            self._welu = None

    def getMessageID(self, record):
        "\n        Return the message ID for the event record. If you are using your\n        own messages, you could do this by having the msg passed to the\n        logger being an ID rather than a formatting string. Then, in here,\n        you could use a dictionary lookup to get the message ID. This\n        version returns 1, which is the base message ID in win32service.pyd.\n        "
        return 1

    def getEventCategory(self, record):
        "\n        Return the event category for the record.\n\n        Override this if you want to specify your own categories. This version\n        returns 0.\n        "
        return 0

    def getEventType(self, record):
        "\n        Return the event type for the record.\n\n        Override this if you want to specify your own types. This version does\n        a mapping using the handler's typemap attribute, which is set up in\n        __init__() to a dictionary which contains mappings for DEBUG, INFO,\n        WARNING, ERROR and CRITICAL. If you are using your own levels you will\n        either need to override this method or place a suitable dictionary in\n        the handler's typemap attribute.\n        "
        return self.typemap.get(record.levelno, self.deftype)

    def emit(self, record):
        "\n        Emit a record.\n\n        Determine the message ID, event category and event type. Then\n        log the message in the NT event log.\n        "
        if self._welu:
            try:
                id = self.getMessageID(record)
                cat = self.getEventCategory(record)
                type = self.getEventType(record)
                msg = self.format(record)
                self._welu.ReportEvent(self.appname, id, cat, type, [msg])
            except Exception:
                self.handleError(record)

    def close(self):
        "\n        Clean up this handler.\n\n        You can remove the application name from the registry as a\n        source of event log entries. However, if you do this, you will\n        not be able to see the events as you intended in the Event Log\n        Viewer - it needs to be able to access the registry to get the\n        DLL name.\n        "
        logging.Handler.close(self)


class HTTPHandler(logging.Handler):
    "\n    A class which sends records to a Web server, using either GET or\n    POST semantics.\n    "

    def __init__(
        self, host, url, method="GET", secure=False, credentials=None, context=None
    ):
        '\n        Initialize the instance with the host, the request URL, and the method\n        ("GET" or "POST")\n        '
        logging.Handler.__init__(self)
        method = method.upper()
        if method not in ["GET", "POST"]:
            raise ValueError("method must be GET or POST")
        if (not secure) and (context is not None):
            raise ValueError("context parameter only makes sense with secure=True")
        self.host = host
        self.url = url
        self.method = method
        self.secure = secure
        self.credentials = credentials
        self.context = context

    def mapLogRecord(self, record):
        "\n        Default implementation of mapping the log record into a dict\n        that is sent as the CGI data. Overwrite in your class.\n        Contributed by Franz Glasner.\n        "
        return record.__dict__

    def getConnection(self, host, secure):
        "\n        get a HTTP[S]Connection.\n\n        Override when a custom connection is required, for example if\n        there is a proxy.\n        "
        import http.client

        if secure:
            connection = http.client.HTTPSConnection(host, context=self.context)
        else:
            connection = http.client.HTTPConnection(host)
        return connection

    def emit(self, record):
        "\n        Emit a record.\n\n        Send the record to the Web server as a percent-encoded dictionary\n        "
        try:
            import urllib.parse

            host = self.host
            h = self.getConnection(host, self.secure)
            url = self.url
            data = urllib.parse.urlencode(self.mapLogRecord(record))
            if self.method == "GET":
                if url.find("?") >= 0:
                    sep = "&"
                else:
                    sep = "?"
                url = url + ("%c%s" % (sep, data))
            h.putrequest(self.method, url)
            i = host.find(":")
            if i >= 0:
                host = host[:i]
            if self.method == "POST":
                h.putheader("Content-type", "application/x-www-form-urlencoded")
                h.putheader("Content-length", str(len(data)))
            if self.credentials:
                import base64

                s = ("%s:%s" % self.credentials).encode("utf-8")
                s = "Basic " + base64.b64encode(s).strip().decode("ascii")
                h.putheader("Authorization", s)
            h.endheaders()
            if self.method == "POST":
                h.send(data.encode("utf-8"))
            h.getresponse()
        except Exception:
            self.handleError(record)


class BufferingHandler(logging.Handler):
    "\n  A handler class which buffers logging records in memory. Whenever each\n  record is added to the buffer, a check is made to see if the buffer should\n  be flushed. If it should, then flush() is expected to do what's needed.\n    "

    def __init__(self, capacity):
        "\n        Initialize the handler with the buffer size.\n        "
        logging.Handler.__init__(self)
        self.capacity = capacity
        self.buffer = []

    def shouldFlush(self, record):
        "\n        Should the handler flush its buffer?\n\n        Returns true if the buffer is up to capacity. This method can be\n        overridden to implement custom flushing strategies.\n        "
        return len(self.buffer) >= self.capacity

    def emit(self, record):
        "\n        Emit a record.\n\n        Append the record. If shouldFlush() tells us to, call flush() to process\n        the buffer.\n        "
        self.buffer.append(record)
        if self.shouldFlush(record):
            self.flush()

    def flush(self):
        "\n        Override to implement custom flushing behaviour.\n\n        This version just zaps the buffer to empty.\n        "
        self.acquire()
        try:
            self.buffer.clear()
        finally:
            self.release()

    def close(self):
        "\n        Close the handler.\n\n        This version just flushes and chains to the parent class' close().\n        "
        try:
            self.flush()
        finally:
            logging.Handler.close(self)


class MemoryHandler(BufferingHandler):
    "\n    A handler class which buffers logging records in memory, periodically\n    flushing them to a target handler. Flushing occurs whenever the buffer\n    is full, or when an event of a certain severity or greater is seen.\n    "

    def __init__(
        self, capacity, flushLevel=logging.ERROR, target=None, flushOnClose=True
    ):
        "\n        Initialize the handler with the buffer size, the level at which\n        flushing should occur and an optional target.\n\n        Note that without a target being set either here or via setTarget(),\n        a MemoryHandler is no use to anyone!\n\n        The ``flushOnClose`` argument is ``True`` for backward compatibility\n        reasons - the old behaviour is that when the handler is closed, the\n        buffer is flushed, even if the flush level hasn't been exceeded nor the\n        capacity exceeded. To prevent this, set ``flushOnClose`` to ``False``.\n        "
        BufferingHandler.__init__(self, capacity)
        self.flushLevel = flushLevel
        self.target = target
        self.flushOnClose = flushOnClose

    def shouldFlush(self, record):
        "\n        Check for buffer full or a record at the flushLevel or higher.\n        "
        return (len(self.buffer) >= self.capacity) or (
            record.levelno >= self.flushLevel
        )

    def setTarget(self, target):
        "\n        Set the target handler for this handler.\n        "
        self.acquire()
        try:
            self.target = target
        finally:
            self.release()

    def flush(self):
        "\n        For a MemoryHandler, flushing means just sending the buffered\n        records to the target, if there is one. Override if you want\n        different behaviour.\n\n        The record buffer is also cleared by this operation.\n        "
        self.acquire()
        try:
            if self.target:
                for record in self.buffer:
                    self.target.handle(record)
                self.buffer.clear()
        finally:
            self.release()

    def close(self):
        "\n        Flush, if appropriately configured, set the target to None and lose the\n        buffer.\n        "
        try:
            if self.flushOnClose:
                self.flush()
        finally:
            self.acquire()
            try:
                self.target = None
                BufferingHandler.close(self)
            finally:
                self.release()


class QueueHandler(logging.Handler):
    "\n    This handler sends events to a queue. Typically, it would be used together\n    with a multiprocessing Queue to centralise logging to file in one process\n    (in a multi-process application), so as to avoid file write contention\n    between processes.\n\n    This code is new in Python 3.2, but this class can be copy pasted into\n    user code for use with earlier Python versions.\n    "

    def __init__(self, queue):
        "\n        Initialise an instance, using the passed queue.\n        "
        logging.Handler.__init__(self)
        self.queue = queue

    def enqueue(self, record):
        "\n        Enqueue a record.\n\n        The base implementation uses put_nowait. You may want to override\n        this method if you want to use blocking, timeouts or custom queue\n        implementations.\n        "
        self.queue.put_nowait(record)

    def prepare(self, record):
        "\n        Prepares a record for queuing. The object returned by this method is\n        enqueued.\n\n        The base implementation formats the record to merge the message\n        and arguments, and removes unpickleable items from the record\n        in-place.\n\n        You might want to override this method if you want to convert\n        the record to a dict or JSON string, or send a modified copy\n        of the record while leaving the original intact.\n        "
        msg = self.format(record)
        record = copy.copy(record)
        record.message = msg
        record.msg = msg
        record.args = None
        record.exc_info = None
        record.exc_text = None
        return record

    def emit(self, record):
        "\n        Emit a record.\n\n        Writes the LogRecord to the queue, preparing it for pickling first.\n        "
        try:
            self.enqueue(self.prepare(record))
        except Exception:
            self.handleError(record)


class QueueListener(object):
    "\n    This class implements an internal threaded listener which watches for\n    LogRecords being added to a queue, removes them and passes them to a\n    list of handlers for processing.\n    "
    _sentinel = None

    def __init__(self, queue, *handlers, respect_handler_level=False):
        "\n        Initialise an instance with the specified queue and\n        handlers.\n        "
        self.queue = queue
        self.handlers = handlers
        self._thread = None
        self.respect_handler_level = respect_handler_level

    def dequeue(self, block):
        "\n        Dequeue a record and return it, optionally blocking.\n\n        The base implementation uses get. You may want to override this method\n        if you want to use timeouts or work with custom queue implementations.\n        "
        return self.queue.get(block)

    def start(self):
        "\n        Start the listener.\n\n        This starts up a background thread to monitor the queue for\n        LogRecords to process.\n        "
        self._thread = t = threading.Thread(target=self._monitor)
        t.daemon = True
        t.start()

    def prepare(self, record):
        "\n        Prepare a record for handling.\n\n        This method just returns the passed-in record. You may want to\n        override this method if you need to do any custom marshalling or\n        manipulation of the record before passing it to the handlers.\n        "
        return record

    def handle(self, record):
        "\n        Handle a record.\n\n        This just loops through the handlers offering them the record\n        to handle.\n        "
        record = self.prepare(record)
        for handler in self.handlers:
            if not self.respect_handler_level:
                process = True
            else:
                process = record.levelno >= handler.level
            if process:
                handler.handle(record)

    def _monitor(self):
        "\n        Monitor the queue for records, and ask the handler\n        to deal with them.\n\n        This method runs on a separate, internal thread.\n        The thread will terminate if it sees a sentinel object in the queue.\n        "
        q = self.queue
        has_task_done = hasattr(q, "task_done")
        while True:
            try:
                record = self.dequeue(True)
                if record is self._sentinel:
                    if has_task_done:
                        q.task_done()
                    break
                self.handle(record)
                if has_task_done:
                    q.task_done()
            except queue.Empty:
                break

    def enqueue_sentinel(self):
        "\n        This is used to enqueue the sentinel record.\n\n        The base implementation uses put_nowait. You may want to override this\n        method if you want to use timeouts or work with custom queue\n        implementations.\n        "
        self.queue.put_nowait(self._sentinel)

    def stop(self):
        "\n        Stop the listener.\n\n        This asks the thread to terminate, and then waits for it to do so.\n        Note that if you don't call this before your application exits, there\n        may be some records still left on the queue, which won't be processed.\n        "
        self.enqueue_sentinel()
        self._thread.join()
        self._thread = None
