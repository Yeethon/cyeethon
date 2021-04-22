import sys, os

if sys.version_info > (3,):
    from distutils.util import copydir_run_2to3

    testroot = os.path.dirname(__file__)
    newroot = os.path.join(testroot, "..", "build/lib/test")
    copydir_run_2to3(testroot, newroot)
    sys.path[0] = newroot
from test_foo import FooTest
import unittest

unittest.main()
