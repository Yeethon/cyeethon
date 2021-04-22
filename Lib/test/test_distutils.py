"Tests for distutils.\n\nThe tests for distutils are defined in the distutils.tests package;\nthe test_suite() function there returns a test suite that's ready to\nbe run.\n"
import warnings
from test import support
from test.support import warnings_helper

with warnings_helper.check_warnings(
    ("The distutils package is deprecated", DeprecationWarning)
):
    import distutils.tests


def test_main():
    support.run_unittest(distutils.tests.test_suite())
    support.reap_children()


def load_tests(*_):
    return distutils.tests.test_suite()


if __name__ == "__main__":
    test_main()
