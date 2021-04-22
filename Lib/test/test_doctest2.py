"A module to test whether doctest recognizes some 2.2 features,\nlike static and class methods.\n\n>>> print('yup')  # 1\nyup\n\nWe include some (random) encoded (utf-8) text in the text surrounding\nthe example.  It should be ignored:\n\nЉЊЈЁЂ\n\n"
import sys
import unittest
from test import support

if sys.flags.optimize >= 2:
    raise unittest.SkipTest("Cannot test docstrings with -O2")


class C(object):
    "Class C.\n\n    >>> print(C())  # 2\n    42\n\n\n    We include some (random) encoded (utf-8) text in the text surrounding\n    the example.  It should be ignored:\n\n        ЉЊЈЁЂ\n\n    "

    def __init__(self):
        "C.__init__.\n\n        >>> print(C()) # 3\n        42\n        "

    def __str__(self):
        "\n        >>> print(C()) # 4\n        42\n        "
        return "42"

    class D(object):
        'A nested D class.\n\n        >>> print("In D!")   # 5\n        In D!\n        '

        def nested(self):
            "\n            >>> print(3) # 6\n            3\n            "

    def getx(self):
        "\n        >>> c = C()    # 7\n        >>> c.x = 12   # 8\n        >>> print(c.x)  # 9\n        -12\n        "
        return -self._x

    def setx(self, value):
        "\n        >>> c = C()     # 10\n        >>> c.x = 12    # 11\n        >>> print(c.x)   # 12\n        -12\n        "
        self._x = value

    x = property(
        getx,
        setx,
        doc="        >>> c = C()    # 13\n        >>> c.x = 12   # 14\n        >>> print(c.x)  # 15\n        -12\n        ",
    )

    @staticmethod
    def statm():
        "\n        A static method.\n\n        >>> print(C.statm())    # 16\n        666\n        >>> print(C().statm())  # 17\n        666\n        "
        return 666

    @classmethod
    def clsm(cls, val):
        "\n        A class method.\n\n        >>> print(C.clsm(22))    # 18\n        22\n        >>> print(C().clsm(23))  # 19\n        23\n        "
        return val


def test_main():
    from test import test_doctest2

    EXPECTED = 19
    (f, t) = support.run_doctest(test_doctest2)
    if t != EXPECTED:
        raise support.TestFailed(("expected %d tests to run, not %d" % (EXPECTED, t)))


from doctest import *

if __name__ == "__main__":
    test_main()
