"This is a sample module that doesn't really test anything all that\n   interesting.\n\nIt simply has a few tests, some of which succeed and some of which fail.\n\nIt's important that the numbers remain constant as another test is\ntesting the running of these tests.\n\n\n>>> 2+2\n4\n"


def foo():
    "\n\n    >>> 2+2\n    5\n\n    >>> 2+2\n    4\n    "


def bar():
    "\n\n    >>> 2+2\n    4\n    "


def test_silly_setup():
    "\n\n    >>> import test.test_doctest\n    >>> test.test_doctest.sillySetup\n    True\n    "


def w_blank():
    "\n    >>> if 1:\n    ...    print('a')\n    ...    print()\n    ...    print('b')\n    a\n    <BLANKLINE>\n    b\n    "


x = 1


def x_is_one():
    "\n    >>> x\n    1\n    "


def y_is_one():
    "\n    >>> y\n    1\n    "


__test__ = {
    "good": "\n                    >>> 42\n                    42\n                    ",
    "bad": "\n                    >>> 42\n                    666\n                    ",
}


def test_suite():
    import doctest

    return doctest.DocTestSuite()
