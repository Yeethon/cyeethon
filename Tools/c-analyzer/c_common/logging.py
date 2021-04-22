import logging
import sys

VERBOSITY = 3
_logger = logging.getLogger(__name__.rpartition(".")[0])


def configure_logger(
    logger, verbosity=VERBOSITY, *, logfile=None, maxlevel=logging.CRITICAL
):
    level = max(1, min(maxlevel, (maxlevel - (verbosity * 10))))
    logger.setLevel(level)
    if not logger.handlers:
        if logfile:
            handler = logging.FileHandler(logfile)
        else:
            handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        logger.addHandler(handler)
    if logger is not _logger:
        configure_logger(_logger, verbosity, logfile=logfile, maxlevel=maxlevel)


def hide_emit_errors():
    "Ignore errors while emitting log entries.\n\n    Rather than printing a message desribing the error, we show nothing.\n    "
    orig = logging.raiseExceptions
    logging.raiseExceptions = False

    def restore():
        logging.raiseExceptions = orig

    return restore


class Printer:
    def __init__(self, verbosity=VERBOSITY):
        self.verbosity = verbosity

    def info(self, *args, **kwargs):
        if self.verbosity < 3:
            return
        print(*args, **kwargs)
