def wrap(foo=None):
    def wrapper(func):
        return func

    return wrapper


def replace(func):
    def insteadfunc():
        print("hello")

    return insteadfunc


@wrap()
@wrap(wrap)
def wrapped():
    pass


@replace
def gone():
    pass


oll = lambda m: m
tll = lambda g: (g and g and g)
tlli = lambda d: (d and d)


def onelinefunc():
    pass


def manyargs(arg1, arg2, arg3, arg4):
    pass


def twolinefunc(m):
    return m and m


a = [None, (lambda x: x), None]


def setfunc(func):
    globals()["anonymous"] = func


setfunc((lambda x, y: (x * y)))


def with_comment():
    world


multiline_sig = [(lambda x, y: (x + y)), None]


def func69():
    class cls70:
        def func71():
            pass

    return cls70


extra74 = 74


def func77():
    pass


(extra78, stuff78) = "xy"
extra79 = "stop"


class cls82:
    def func83():
        pass


(extra84, stuff84) = "xy"
extra85 = "stop"


def func88():
    return 90


def f():
    class X:
        def g():
            "doc"
            return 42

    return X


method_in_dynamic_class = f().g


def keyworded(*arg1, arg2=1):
    pass


def annotated(arg1: list):
    pass


def keyword_only_arg(*, arg):
    pass


@wrap((lambda: None))
def func114():
    return 115


class ClassWithMethod:
    def method(self):
        pass


from functools import wraps


def decorator(func):
    @wraps(func)
    def fake():
        return 42

    return fake


@decorator
def real():
    return 20


class cls135:
    def func136():
        def func137():
            never_reached1
            never_reached2


class cls142:
    a = "\nclass cls149:\n    ...\n"


class cls149:
    def func151(self):
        pass


"\nclass cls160:\n    pass\n"


class cls160:
    def func162(self):
        pass


class cls166:
    a = "\n    class cls175:\n        ...\n    "


class cls173:
    class cls175:
        pass


class cls179:
    pass


class cls183:
    class cls185:
        def func186(self):
            pass


def class_decorator(cls):
    return cls


@class_decorator
@class_decorator
class cls196:
    @class_decorator
    @class_decorator
    class cls200:
        pass


class cls203:
    class cls204:
        class cls205:
            pass

    class cls207:
        class cls205:
            pass


def func212():
    class cls213:
        pass

    return cls213


class cls213:
    def func219(self):
        class cls220:
            pass

        return cls220


async def func225():
    class cls226:
        pass

    return cls226


class cls226:
    async def func232(self):
        class cls233:
            pass

        return cls233


if True:

    class cls238:
        class cls239:
            "if clause cls239"


else:

    class cls238:
        class cls239:
            "else clause 239"
            pass


def positional_only_arg(a, /):
    pass


def all_markers(a, b, /, c, d, *, e, f):
    pass


def all_markers_with_args_and_kwargs(a, b, /, c, d, *args, e, f, **kwargs):
    pass


def all_markers_with_defaults(a, b=1, /, c=2, d=3, *, e=4, f=5):
    pass
