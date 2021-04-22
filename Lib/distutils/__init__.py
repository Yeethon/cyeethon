"distutils\n\nThe main package for the Python Module Distribution Utilities.  Normally\nused from a setup script as\n\n   from distutils.core import setup\n\n   setup (...)\n"
import sys
import warnings

__version__ = sys.version[: sys.version.index(" ")]
_DEPRECATION_MESSAGE = "The distutils package is deprecated and slated for removal in Python 3.12. Use setuptools or check PEP 632 for potential alternatives"
warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, 2)
