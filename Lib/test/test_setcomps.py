doctests = "\n########### Tests mostly copied from test_listcomps.py ############\n\nTest simple loop with conditional\n\n    >>> sum({i*i for i in range(100) if i&1 == 1})\n    166650\n\nTest simple case\n\n    >>> {2*y + x + 1 for x in (0,) for y in (1,)}\n    {3}\n\nTest simple nesting\n\n    >>> list(sorted({(i,j) for i in range(3) for j in range(4)}))\n    [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3), (2, 0), (2, 1), (2, 2), (2, 3)]\n\nTest nesting with the inner expression dependent on the outer\n\n    >>> list(sorted({(i,j) for i in range(4) for j in range(i)}))\n    [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (3, 2)]\n\nTest the idiom for temporary variable assignment in comprehensions.\n\n    >>> sorted({j*j for i in range(4) for j in [i+1]})\n    [1, 4, 9, 16]\n    >>> sorted({j*k for i in range(4) for j in [i+1] for k in [j+1]})\n    [2, 6, 12, 20]\n    >>> sorted({j*k for i in range(4) for j, k in [(i+1, i+2)]})\n    [2, 6, 12, 20]\n\nNot assignment\n\n    >>> sorted({i*i for i in [*range(4)]})\n    [0, 1, 4, 9]\n    >>> sorted({i*i for i in (*range(4),)})\n    [0, 1, 4, 9]\n\nMake sure the induction variable is not exposed\n\n    >>> i = 20\n    >>> sum({i*i for i in range(100)})\n    328350\n\n    >>> i\n    20\n\nVerify that syntax error's are raised for setcomps used as lvalues\n\n    >>> {y for y in (1,2)} = 10          # doctest: +IGNORE_EXCEPTION_DETAIL\n    Traceback (most recent call last):\n       ...\n    SyntaxError: ...\n\n    >>> {y for y in (1,2)} += 10         # doctest: +IGNORE_EXCEPTION_DETAIL\n    Traceback (most recent call last):\n       ...\n    SyntaxError: ...\n\n\nMake a nested set comprehension that acts like set(range())\n\n    >>> def srange(n):\n    ...     return {i for i in range(n)}\n    >>> list(sorted(srange(10)))\n    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]\n\nSame again, only as a lambda expression instead of a function definition\n\n    >>> lrange = lambda n:  {i for i in range(n)}\n    >>> list(sorted(lrange(10)))\n    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]\n\nGenerators can call other generators:\n\n    >>> def grange(n):\n    ...     for x in {i for i in range(n)}:\n    ...         yield x\n    >>> list(sorted(grange(5)))\n    [0, 1, 2, 3, 4]\n\n\nMake sure that None is a valid return value\n\n    >>> {None for i in range(10)}\n    {None}\n\n########### Tests for various scoping corner cases ############\n\nReturn lambdas that use the iteration variable as a default argument\n\n    >>> items = {(lambda i=i: i) for i in range(5)}\n    >>> {x() for x in items} == set(range(5))\n    True\n\nSame again, only this time as a closure variable\n\n    >>> items = {(lambda: i) for i in range(5)}\n    >>> {x() for x in items}\n    {4}\n\nAnother way to test that the iteration variable is local to the list comp\n\n    >>> items = {(lambda: i) for i in range(5)}\n    >>> i = 20\n    >>> {x() for x in items}\n    {4}\n\nAnd confirm that a closure can jump over the list comp scope\n\n    >>> items = {(lambda: y) for i in range(5)}\n    >>> y = 2\n    >>> {x() for x in items}\n    {2}\n\nWe also repeat each of the above scoping tests inside a function\n\n    >>> def test_func():\n    ...     items = {(lambda i=i: i) for i in range(5)}\n    ...     return {x() for x in items}\n    >>> test_func() == set(range(5))\n    True\n\n    >>> def test_func():\n    ...     items = {(lambda: i) for i in range(5)}\n    ...     return {x() for x in items}\n    >>> test_func()\n    {4}\n\n    >>> def test_func():\n    ...     items = {(lambda: i) for i in range(5)}\n    ...     i = 20\n    ...     return {x() for x in items}\n    >>> test_func()\n    {4}\n\n    >>> def test_func():\n    ...     items = {(lambda: y) for i in range(5)}\n    ...     y = 2\n    ...     return {x() for x in items}\n    >>> test_func()\n    {2}\n\n"
__test__ = {"doctests": doctests}


def test_main(verbose=None):
    import sys
    from test import support
    from test import test_setcomps

    support.run_doctest(test_setcomps, verbose)
    if verbose and hasattr(sys, "gettotalrefcount"):
        import gc

        counts = [None] * 5
        for i in range(len(counts)):
            support.run_doctest(test_setcomps, verbose)
            gc.collect()
            counts[i] = sys.gettotalrefcount()
        print(counts)


if __name__ == "__main__":
    test_main(verbose=True)
