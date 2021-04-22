from sqlite3.dbapi2 import *


def __getattr__(name):
    if name == "OptimizedUnicode":
        import warnings

        msg = "\n            OptimizedUnicode is deprecated and will be removed in Python 3.12.\n            Since Python 3.3 it has simply been an alias for 'str'.\n        "
        warnings.warn(msg, DeprecationWarning, stacklevel=2)
        return str
    raise AttributeError(f"module 'sqlite3' has no attribute '{name}'")
