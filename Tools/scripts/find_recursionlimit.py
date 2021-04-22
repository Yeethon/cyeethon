'Find the maximum recursion limit that prevents interpreter termination.\n\nThis script finds the maximum safe recursion limit on a particular\nplatform.  If you need to change the recursion limit on your system,\nthis script will tell you a safe upper bound.  To use the new limit,\ncall sys.setrecursionlimit().\n\nThis module implements several ways to create infinite recursion in\nPython.  Different implementations end up pushing different numbers of\nC stack frames, depending on how many calls through Python\'s abstract\nC API occur.\n\nAfter each round of tests, it prints a message:\n"Limit of NNNN is fine".\n\nThe highest printed value of "NNNN" is therefore the highest potentially\nsafe limit for your system (which depends on the OS, architecture, but also\nthe compilation flags). Please note that it is practically impossible to\ntest all possible recursion paths in the interpreter, so the results of\nthis test should not be trusted blindly -- although they give a good hint\nof which values are reasonable.\n\nNOTE: When the C stack space allocated by your system is exceeded due\nto excessive recursion, exact behaviour depends on the platform, although\nthe interpreter will always fail in a likely brutal way: either a\nsegmentation fault, a MemoryError, or just a silent abort.\n\nNB: A program that does not use __methods__ can set a higher limit.\n'
import sys
import itertools


class RecursiveBlowup1:
    def __init__(self):
        self.__init__()


def test_init():
    return RecursiveBlowup1()


class RecursiveBlowup2:
    def __repr__(self):
        return repr(self)


def test_repr():
    return repr(RecursiveBlowup2())


class RecursiveBlowup4:
    def __add__(self, x):
        return x + self


def test_add():
    return RecursiveBlowup4() + RecursiveBlowup4()


class RecursiveBlowup5:
    def __getattr__(self, attr):
        return getattr(self, attr)


def test_getattr():
    return RecursiveBlowup5().attr


class RecursiveBlowup6:
    def __getitem__(self, item):
        return self[(item - 2)] + self[(item - 1)]


def test_getitem():
    return RecursiveBlowup6()[5]


def test_recurse():
    return test_recurse()


def test_cpickle(_cache={}):
    import io

    try:
        import _pickle
    except ImportError:
        print("cannot import _pickle, skipped!")
        return
    (k, l) = (None, None)
    for n in itertools.count():
        try:
            l = _cache[n]
            continue
        except KeyError:
            for i in range(100):
                l = [k, l]
                k = {i: l}
        _pickle.Pickler(io.BytesIO(), protocol=(-1)).dump(l)
        _cache[n] = l


def test_compiler_recursion():
    compile(("()" * (10 * sys.getrecursionlimit())), "<single>", "single")


def check_limit(n, test_func_name):
    sys.setrecursionlimit(n)
    if test_func_name.startswith("test_"):
        print(test_func_name[5:])
    else:
        print(test_func_name)
    test_func = globals()[test_func_name]
    try:
        test_func()
    except (RecursionError, AttributeError):
        pass
    else:
        print("Yikes!")


if __name__ == "__main__":
    limit = 1000
    while 1:
        check_limit(limit, "test_recurse")
        check_limit(limit, "test_add")
        check_limit(limit, "test_repr")
        check_limit(limit, "test_init")
        check_limit(limit, "test_getattr")
        check_limit(limit, "test_getitem")
        check_limit(limit, "test_cpickle")
        check_limit(limit, "test_compiler_recursion")
        print(("Limit of %d is fine" % limit))
        limit = limit + 100
