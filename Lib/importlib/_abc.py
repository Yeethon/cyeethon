"Subset of importlib.abc used to reduce importlib.util imports."
from . import _bootstrap
import abc
import warnings


class Loader(metaclass=abc.ABCMeta):
    "Abstract base class for import loaders."

    def create_module(self, spec):
        "Return a module to initialize and into which to load.\n\n        This method should raise ImportError if anything prevents it\n        from creating a new module.  It may return None to indicate\n        that the spec should create the new module.\n        "
        return None

    def load_module(self, fullname):
        "Return the loaded module.\n\n        The module must be added to sys.modules and have import-related\n        attributes set properly.  The fullname is a str.\n\n        ImportError is raised on failure.\n\n        This method is deprecated in favor of loader.exec_module(). If\n        exec_module() exists then it is used to provide a backwards-compatible\n        functionality for this method.\n\n        "
        if not hasattr(self, "exec_module"):
            raise ImportError
        return _bootstrap._load_module_shim(self, fullname)

    def module_repr(self, module):
        "Return a module's repr.\n\n        Used by the module type when the method does not raise\n        NotImplementedError.\n\n        This method is deprecated.\n\n        "
        warnings.warn(
            "importlib.abc.Loader.module_repr() is deprecated and slated for removal in Python 3.12",
            DeprecationWarning,
        )
        raise NotImplementedError
