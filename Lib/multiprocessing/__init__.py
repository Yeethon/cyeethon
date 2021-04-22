import sys
from . import context

__all__ = [x for x in dir(context._default_context) if (not x.startswith("_"))]
globals().update(((name, getattr(context._default_context, name)) for name in __all__))
SUBDEBUG = 5
SUBWARNING = 25
if "__main__" in sys.modules:
    sys.modules["__mp_main__"] = sys.modules["__main__"]
