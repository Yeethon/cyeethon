"functools.py - Tools for working with functions and callable objects\n"
__all__ = [
    "update_wrapper",
    "wraps",
    "WRAPPER_ASSIGNMENTS",
    "WRAPPER_UPDATES",
    "total_ordering",
    "cache",
    "cmp_to_key",
    "lru_cache",
    "reduce",
    "partial",
    "partialmethod",
    "singledispatch",
    "singledispatchmethod",
    "cached_property",
]
from abc import get_cache_token
from collections import namedtuple
from reprlib import recursive_repr
from _thread import RLock
from types import GenericAlias

WRAPPER_ASSIGNMENTS = (
    "__module__",
    "__name__",
    "__qualname__",
    "__doc__",
    "__annotations__",
)
WRAPPER_UPDATES = ("__dict__",)


def update_wrapper(
    wrapper, wrapped, assigned=WRAPPER_ASSIGNMENTS, updated=WRAPPER_UPDATES
):
    "Update a wrapper function to look like the wrapped function\n\n       wrapper is the function to be updated\n       wrapped is the original function\n       assigned is a tuple naming the attributes assigned directly\n       from the wrapped function to the wrapper function (defaults to\n       functools.WRAPPER_ASSIGNMENTS)\n       updated is a tuple naming the attributes of the wrapper that\n       are updated with the corresponding attribute from the wrapped\n       function (defaults to functools.WRAPPER_UPDATES)\n    "
    for attr in assigned:
        try:
            value = getattr(wrapped, attr)
        except AttributeError:
            pass
        else:
            setattr(wrapper, attr, value)
    for attr in updated:
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    wrapper.__wrapped__ = wrapped
    return wrapper


def wraps(wrapped, assigned=WRAPPER_ASSIGNMENTS, updated=WRAPPER_UPDATES):
    "Decorator factory to apply update_wrapper() to a wrapper function\n\n       Returns a decorator that invokes update_wrapper() with the decorated\n       function as the wrapper argument and the arguments to wraps() as the\n       remaining arguments. Default arguments are as for update_wrapper().\n       This is a convenience function to simplify applying partial() to\n       update_wrapper().\n    "
    return partial(update_wrapper, wrapped=wrapped, assigned=assigned, updated=updated)


def _gt_from_lt(self, other, NotImplemented=NotImplemented):
    "Return a > b.  Computed by @total_ordering from (not a < b) and (a != b)."
    op_result = self.__lt__(other)
    if op_result is NotImplemented:
        return op_result
    return (not op_result) and (self != other)


def _le_from_lt(self, other, NotImplemented=NotImplemented):
    "Return a <= b.  Computed by @total_ordering from (a < b) or (a == b)."
    op_result = self.__lt__(other)
    if op_result is NotImplemented:
        return op_result
    return op_result or (self == other)


def _ge_from_lt(self, other, NotImplemented=NotImplemented):
    "Return a >= b.  Computed by @total_ordering from (not a < b)."
    op_result = self.__lt__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result


def _ge_from_le(self, other, NotImplemented=NotImplemented):
    "Return a >= b.  Computed by @total_ordering from (not a <= b) or (a == b)."
    op_result = self.__le__(other)
    if op_result is NotImplemented:
        return op_result
    return (not op_result) or (self == other)


def _lt_from_le(self, other, NotImplemented=NotImplemented):
    "Return a < b.  Computed by @total_ordering from (a <= b) and (a != b)."
    op_result = self.__le__(other)
    if op_result is NotImplemented:
        return op_result
    return op_result and (self != other)


def _gt_from_le(self, other, NotImplemented=NotImplemented):
    "Return a > b.  Computed by @total_ordering from (not a <= b)."
    op_result = self.__le__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result


def _lt_from_gt(self, other, NotImplemented=NotImplemented):
    "Return a < b.  Computed by @total_ordering from (not a > b) and (a != b)."
    op_result = self.__gt__(other)
    if op_result is NotImplemented:
        return op_result
    return (not op_result) and (self != other)


def _ge_from_gt(self, other, NotImplemented=NotImplemented):
    "Return a >= b.  Computed by @total_ordering from (a > b) or (a == b)."
    op_result = self.__gt__(other)
    if op_result is NotImplemented:
        return op_result
    return op_result or (self == other)


def _le_from_gt(self, other, NotImplemented=NotImplemented):
    "Return a <= b.  Computed by @total_ordering from (not a > b)."
    op_result = self.__gt__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result


def _le_from_ge(self, other, NotImplemented=NotImplemented):
    "Return a <= b.  Computed by @total_ordering from (not a >= b) or (a == b)."
    op_result = self.__ge__(other)
    if op_result is NotImplemented:
        return op_result
    return (not op_result) or (self == other)


def _gt_from_ge(self, other, NotImplemented=NotImplemented):
    "Return a > b.  Computed by @total_ordering from (a >= b) and (a != b)."
    op_result = self.__ge__(other)
    if op_result is NotImplemented:
        return op_result
    return op_result and (self != other)


def _lt_from_ge(self, other, NotImplemented=NotImplemented):
    "Return a < b.  Computed by @total_ordering from (not a >= b)."
    op_result = self.__ge__(other)
    if op_result is NotImplemented:
        return op_result
    return not op_result


_convert = {
    "__lt__": [
        ("__gt__", _gt_from_lt),
        ("__le__", _le_from_lt),
        ("__ge__", _ge_from_lt),
    ],
    "__le__": [
        ("__ge__", _ge_from_le),
        ("__lt__", _lt_from_le),
        ("__gt__", _gt_from_le),
    ],
    "__gt__": [
        ("__lt__", _lt_from_gt),
        ("__ge__", _ge_from_gt),
        ("__le__", _le_from_gt),
    ],
    "__ge__": [
        ("__le__", _le_from_ge),
        ("__gt__", _gt_from_ge),
        ("__lt__", _lt_from_ge),
    ],
}


def total_ordering(cls):
    "Class decorator that fills in missing ordering methods"
    roots = {
        op
        for op in _convert
        if (getattr(cls, op, None) is not getattr(object, op, None))
    }
    if not roots:
        raise ValueError("must define at least one ordering operation: < > <= >=")
    root = max(roots)
    for (opname, opfunc) in _convert[root]:
        if opname not in roots:
            opfunc.__name__ = opname
            setattr(cls, opname, opfunc)
    return cls


def cmp_to_key(mycmp):
    "Convert a cmp= function into a key= function"

    class K(object):
        __slots__ = ["obj"]

        def __init__(self, obj):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        __hash__ = None

    return K


try:
    from _functools import cmp_to_key
except ImportError:
    pass
_initial_missing = object()


def reduce(function, sequence, initial=_initial_missing):
    "\n    reduce(function, iterable[, initial]) -> value\n\n    Apply a function of two arguments cumulatively to the items of a sequence\n    or iterable, from left to right, so as to reduce the iterable to a single\n    value.  For example, reduce(lambda x, y: x+y, [1, 2, 3, 4, 5]) calculates\n    ((((1+2)+3)+4)+5).  If initial is present, it is placed before the items\n    of the iterable in the calculation, and serves as a default when the\n    iterable is empty.\n    "
    it = iter(sequence)
    if initial is _initial_missing:
        try:
            value = next(it)
        except StopIteration:
            raise TypeError(
                "reduce() of empty iterable with no initial value"
            ) from None
    else:
        value = initial
    for element in it:
        value = function(value, element)
    return value


try:
    from _functools import reduce
except ImportError:
    pass


class partial:
    "New function with partial application of the given arguments\n    and keywords.\n    "
    __slots__ = ("func", "args", "keywords", "__dict__", "__weakref__")

    def __new__(cls, func, /, *args, **keywords):
        if not callable(func):
            raise TypeError("the first argument must be callable")
        if hasattr(func, "func"):
            args = func.args + args
            keywords = {**func.keywords, **keywords}
            func = func.func
        self = super(partial, cls).__new__(cls)
        self.func = func
        self.args = args
        self.keywords = keywords
        return self

    def __call__(self, /, *args, **keywords):
        keywords = {**self.keywords, **keywords}
        return self.func(*self.args, *args, **keywords)

    @recursive_repr()
    def __repr__(self):
        qualname = type(self).__qualname__
        args = [repr(self.func)]
        args.extend((repr(x) for x in self.args))
        args.extend((f"{k}={v!r}" for (k, v) in self.keywords.items()))
        if type(self).__module__ == "functools":
            return f"functools.{qualname}({', '.join(args)})"
        return f"{qualname}({', '.join(args)})"

    def __reduce__(self):
        return (
            type(self),
            (self.func,),
            (self.func, self.args, (self.keywords or None), (self.__dict__ or None)),
        )

    def __setstate__(self, state):
        if not isinstance(state, tuple):
            raise TypeError("argument to __setstate__ must be a tuple")
        if len(state) != 4:
            raise TypeError(f"expected 4 items in state, got {len(state)}")
        (func, args, kwds, namespace) = state
        if (
            (not callable(func))
            or (not isinstance(args, tuple))
            or ((kwds is not None) and (not isinstance(kwds, dict)))
            or ((namespace is not None) and (not isinstance(namespace, dict)))
        ):
            raise TypeError("invalid partial state")
        args = tuple(args)
        if kwds is None:
            kwds = {}
        elif type(kwds) is not dict:
            kwds = dict(kwds)
        if namespace is None:
            namespace = {}
        self.__dict__ = namespace
        self.func = func
        self.args = args
        self.keywords = kwds


try:
    from _functools import partial
except ImportError:
    pass


class partialmethod(object):
    "Method descriptor with partial application of the given arguments\n    and keywords.\n\n    Supports wrapping existing descriptors and handles non-descriptor\n    callables as instance methods.\n    "

    def __init__(self, func, /, *args, **keywords):
        if (not callable(func)) and (not hasattr(func, "__get__")):
            raise TypeError("{!r} is not callable or a descriptor".format(func))
        if isinstance(func, partialmethod):
            self.func = func.func
            self.args = func.args + args
            self.keywords = {**func.keywords, **keywords}
        else:
            self.func = func
            self.args = args
            self.keywords = keywords

    def __repr__(self):
        args = ", ".join(map(repr, self.args))
        keywords = ", ".join(
            ("{}={!r}".format(k, v) for (k, v) in self.keywords.items())
        )
        format_string = "{module}.{cls}({func}, {args}, {keywords})"
        return format_string.format(
            module=self.__class__.__module__,
            cls=self.__class__.__qualname__,
            func=self.func,
            args=args,
            keywords=keywords,
        )

    def _make_unbound_method(self):
        def _method(cls_or_self, /, *args, **keywords):
            keywords = {**self.keywords, **keywords}
            return self.func(cls_or_self, *self.args, *args, **keywords)

        _method.__isabstractmethod__ = self.__isabstractmethod__
        _method._partialmethod = self
        return _method

    def __get__(self, obj, cls=None):
        get = getattr(self.func, "__get__", None)
        result = None
        if get is not None:
            new_func = get(obj, cls)
            if new_func is not self.func:
                result = partial(new_func, *self.args, **self.keywords)
                try:
                    result.__self__ = new_func.__self__
                except AttributeError:
                    pass
        if result is None:
            result = self._make_unbound_method().__get__(obj, cls)
        return result

    @property
    def __isabstractmethod__(self):
        return getattr(self.func, "__isabstractmethod__", False)

    __class_getitem__ = classmethod(GenericAlias)


def _unwrap_partial(func):
    while isinstance(func, partial):
        func = func.func
    return func


_CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize", "currsize"])


class _HashedSeq(list):
    " This class guarantees that hash() will be called no more than once\n        per element.  This is important because the lru_cache() will hash\n        the key multiple times on a cache miss.\n\n    "
    __slots__ = "hashvalue"

    def __init__(self, tup, hash=hash):
        self[:] = tup
        self.hashvalue = hash(tup)

    def __hash__(self):
        return self.hashvalue


def _make_key(
    args,
    kwds,
    typed,
    kwd_mark=(object(),),
    fasttypes={int, str},
    tuple=tuple,
    type=type,
    len=len,
):
    "Make a cache key from optionally typed positional and keyword arguments\n\n    The key is constructed in a way that is flat as possible rather than\n    as a nested structure that would take more memory.\n\n    If there is only a single argument and its data type is known to cache\n    its hash value, then that argument is returned without a wrapper.  This\n    saves space and improves lookup speed.\n\n    "
    key = args
    if kwds:
        key += kwd_mark
        for item in kwds.items():
            key += item
    if typed:
        key += tuple((type(v) for v in args))
        if kwds:
            key += tuple((type(v) for v in kwds.values()))
    elif (len(key) == 1) and (type(key[0]) in fasttypes):
        return key[0]
    return _HashedSeq(key)


def lru_cache(maxsize=128, typed=False):
    "Least-recently-used cache decorator.\n\n    If *maxsize* is set to None, the LRU features are disabled and the cache\n    can grow without bound.\n\n    If *typed* is True, arguments of different types will be cached separately.\n    For example, f(3.0) and f(3) will be treated as distinct calls with\n    distinct results.\n\n    Arguments to the cached function must be hashable.\n\n    View the cache statistics named tuple (hits, misses, maxsize, currsize)\n    with f.cache_info().  Clear the cache and statistics with f.cache_clear().\n    Access the underlying function with f.__wrapped__.\n\n    See:  http://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)\n\n    "
    if isinstance(maxsize, int):
        if maxsize < 0:
            maxsize = 0
    elif callable(maxsize) and isinstance(typed, bool):
        (user_function, maxsize) = (maxsize, 128)
        wrapper = _lru_cache_wrapper(user_function, maxsize, typed, _CacheInfo)
        wrapper.cache_parameters = lambda: {"maxsize": maxsize, "typed": typed}
        return update_wrapper(wrapper, user_function)
    elif maxsize is not None:
        raise TypeError("Expected first argument to be an integer, a callable, or None")

    def decorating_function(user_function):
        wrapper = _lru_cache_wrapper(user_function, maxsize, typed, _CacheInfo)
        wrapper.cache_parameters = lambda: {"maxsize": maxsize, "typed": typed}
        return update_wrapper(wrapper, user_function)

    return decorating_function


def _lru_cache_wrapper(user_function, maxsize, typed, _CacheInfo):
    sentinel = object()
    make_key = _make_key
    (PREV, NEXT, KEY, RESULT) = (0, 1, 2, 3)
    cache = {}
    hits = misses = 0
    full = False
    cache_get = cache.get
    cache_len = cache.__len__
    lock = RLock()
    root = []
    root[:] = [root, root, None, None]
    if maxsize == 0:

        def wrapper(*args, **kwds):
            nonlocal misses
            misses += 1
            result = user_function(*args, **kwds)
            return result

    elif maxsize is None:

        def wrapper(*args, **kwds):
            nonlocal hits, misses
            key = make_key(args, kwds, typed)
            result = cache_get(key, sentinel)
            if result is not sentinel:
                hits += 1
                return result
            misses += 1
            result = user_function(*args, **kwds)
            cache[key] = result
            return result

    else:

        def wrapper(*args, **kwds):
            nonlocal root, hits, misses, full
            key = make_key(args, kwds, typed)
            with lock:
                link = cache_get(key)
                if link is not None:
                    (link_prev, link_next, _key, result) = link
                    link_prev[NEXT] = link_next
                    link_next[PREV] = link_prev
                    last = root[PREV]
                    last[NEXT] = root[PREV] = link
                    link[PREV] = last
                    link[NEXT] = root
                    hits += 1
                    return result
                misses += 1
            result = user_function(*args, **kwds)
            with lock:
                if key in cache:
                    pass
                elif full:
                    oldroot = root
                    oldroot[KEY] = key
                    oldroot[RESULT] = result
                    root = oldroot[NEXT]
                    oldkey = root[KEY]
                    oldresult = root[RESULT]
                    root[KEY] = root[RESULT] = None
                    del cache[oldkey]
                    cache[key] = oldroot
                else:
                    last = root[PREV]
                    link = [last, root, key, result]
                    last[NEXT] = root[PREV] = cache[key] = link
                    full = cache_len() >= maxsize
            return result

    def cache_info():
        "Report cache statistics"
        with lock:
            return _CacheInfo(hits, misses, maxsize, cache_len())

    def cache_clear():
        "Clear the cache and cache statistics"
        nonlocal hits, misses, full
        with lock:
            cache.clear()
            root[:] = [root, root, None, None]
            hits = misses = 0
            full = False

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear
    return wrapper


try:
    from _functools import _lru_cache_wrapper
except ImportError:
    pass


def cache(user_function, /):
    'Simple lightweight unbounded cache.  Sometimes called "memoize".'
    return lru_cache(maxsize=None)(user_function)


def _c3_merge(sequences):
    "Merges MROs in *sequences* to a single MRO using the C3 algorithm.\n\n    Adapted from http://www.python.org/download/releases/2.3/mro/.\n\n    "
    result = []
    while True:
        sequences = [s for s in sequences if s]
        if not sequences:
            return result
        for s1 in sequences:
            candidate = s1[0]
            for s2 in sequences:
                if candidate in s2[1:]:
                    candidate = None
                    break
            else:
                break
        if candidate is None:
            raise RuntimeError("Inconsistent hierarchy")
        result.append(candidate)
        for seq in sequences:
            if seq[0] == candidate:
                del seq[0]


def _c3_mro(cls, abcs=None):
    "Computes the method resolution order using extended C3 linearization.\n\n    If no *abcs* are given, the algorithm works exactly like the built-in C3\n    linearization used for method resolution.\n\n    If given, *abcs* is a list of abstract base classes that should be inserted\n    into the resulting MRO. Unrelated ABCs are ignored and don't end up in the\n    result. The algorithm inserts ABCs where their functionality is introduced,\n    i.e. issubclass(cls, abc) returns True for the class itself but returns\n    False for all its direct base classes. Implicit ABCs for a given class\n    (either registered or inferred from the presence of a special method like\n    __len__) are inserted directly after the last ABC explicitly listed in the\n    MRO of said class. If two implicit ABCs end up next to each other in the\n    resulting MRO, their ordering depends on the order of types in *abcs*.\n\n    "
    for (i, base) in enumerate(reversed(cls.__bases__)):
        if hasattr(base, "__abstractmethods__"):
            boundary = len(cls.__bases__) - i
            break
    else:
        boundary = 0
    abcs = list(abcs) if abcs else []
    explicit_bases = list(cls.__bases__[:boundary])
    abstract_bases = []
    other_bases = list(cls.__bases__[boundary:])
    for base in abcs:
        if issubclass(cls, base) and (
            not any((issubclass(b, base) for b in cls.__bases__))
        ):
            abstract_bases.append(base)
    for base in abstract_bases:
        abcs.remove(base)
    explicit_c3_mros = [_c3_mro(base, abcs=abcs) for base in explicit_bases]
    abstract_c3_mros = [_c3_mro(base, abcs=abcs) for base in abstract_bases]
    other_c3_mros = [_c3_mro(base, abcs=abcs) for base in other_bases]
    return _c3_merge(
        (
            (
                (
                    ((([[cls]] + explicit_c3_mros) + abstract_c3_mros) + other_c3_mros)
                    + [explicit_bases]
                )
                + [abstract_bases]
            )
            + [other_bases]
        )
    )


def _compose_mro(cls, types):
    "Calculates the method resolution order for a given class *cls*.\n\n    Includes relevant abstract base classes (with their respective bases) from\n    the *types* iterable. Uses a modified C3 linearization algorithm.\n\n    "
    bases = set(cls.__mro__)

    def is_related(typ):
        return (typ not in bases) and hasattr(typ, "__mro__") and issubclass(cls, typ)

    types = [n for n in types if is_related(n)]

    def is_strict_base(typ):
        for other in types:
            if (typ != other) and (typ in other.__mro__):
                return True
        return False

    types = [n for n in types if (not is_strict_base(n))]
    type_set = set(types)
    mro = []
    for typ in types:
        found = []
        for sub in typ.__subclasses__():
            if (sub not in bases) and issubclass(cls, sub):
                found.append([s for s in sub.__mro__ if (s in type_set)])
        if not found:
            mro.append(typ)
            continue
        found.sort(key=len, reverse=True)
        for sub in found:
            for subcls in sub:
                if subcls not in mro:
                    mro.append(subcls)
    return _c3_mro(cls, abcs=mro)


def _find_impl(cls, registry):
    "Returns the best matching implementation from *registry* for type *cls*.\n\n    Where there is no registered implementation for a specific type, its method\n    resolution order is used to find a more generic implementation.\n\n    Note: if *registry* does not contain an implementation for the base\n    *object* type, this function may return None.\n\n    "
    mro = _compose_mro(cls, registry.keys())
    match = None
    for t in mro:
        if match is not None:
            if (
                (t in registry)
                and (t not in cls.__mro__)
                and (match not in cls.__mro__)
                and (not issubclass(match, t))
            ):
                raise RuntimeError("Ambiguous dispatch: {} or {}".format(match, t))
            break
        if t in registry:
            match = t
    return registry.get(match)


def singledispatch(func):
    "Single-dispatch generic function decorator.\n\n    Transforms a function into a generic function, which can have different\n    behaviours depending upon the type of its first argument. The decorated\n    function acts as the default implementation, and additional\n    implementations can be registered using the register() attribute of the\n    generic function.\n    "
    import types, weakref

    registry = {}
    dispatch_cache = weakref.WeakKeyDictionary()
    cache_token = None

    def dispatch(cls):
        "generic_func.dispatch(cls) -> <function implementation>\n\n        Runs the dispatch algorithm to return the best available implementation\n        for the given *cls* registered on *generic_func*.\n\n        "
        nonlocal cache_token
        if cache_token is not None:
            current_token = get_cache_token()
            if cache_token != current_token:
                dispatch_cache.clear()
                cache_token = current_token
        try:
            impl = dispatch_cache[cls]
        except KeyError:
            try:
                impl = registry[cls]
            except KeyError:
                impl = _find_impl(cls, registry)
            dispatch_cache[cls] = impl
        return impl

    def register(cls, func=None):
        "generic_func.register(cls, func) -> func\n\n        Registers a new implementation for the given *cls* on a *generic_func*.\n\n        "
        nonlocal cache_token
        if func is None:
            if isinstance(cls, type):
                return lambda f: register(cls, f)
            ann = getattr(cls, "__annotations__", {})
            if not ann:
                raise TypeError(
                    f"Invalid first argument to `register()`: {cls!r}. Use either `@register(some_class)` or plain `@register` on an annotated function."
                )
            func = cls
            from typing import get_type_hints

            (argname, cls) = next(iter(get_type_hints(func).items()))
            if not isinstance(cls, type):
                raise TypeError(
                    f"Invalid annotation for {argname!r}. {cls!r} is not a class."
                )
        registry[cls] = func
        if (cache_token is None) and hasattr(cls, "__abstractmethods__"):
            cache_token = get_cache_token()
        dispatch_cache.clear()
        return func

    def wrapper(*args, **kw):
        if not args:
            raise TypeError(f"{funcname} requires at least 1 positional argument")
        return dispatch(args[0].__class__)(*args, **kw)

    funcname = getattr(func, "__name__", "singledispatch function")
    registry[object] = func
    wrapper.register = register
    wrapper.dispatch = dispatch
    wrapper.registry = types.MappingProxyType(registry)
    wrapper._clear_cache = dispatch_cache.clear
    update_wrapper(wrapper, func)
    return wrapper


class singledispatchmethod:
    "Single-dispatch generic method descriptor.\n\n    Supports wrapping existing descriptors and handles non-descriptor\n    callables as instance methods.\n    "

    def __init__(self, func):
        if (not callable(func)) and (not hasattr(func, "__get__")):
            raise TypeError(f"{func!r} is not callable or a descriptor")
        self.dispatcher = singledispatch(func)
        self.func = func

    def register(self, cls, method=None):
        "generic_method.register(cls, func) -> func\n\n        Registers a new implementation for the given *cls* on a *generic_method*.\n        "
        return self.dispatcher.register(cls, func=method)

    def __get__(self, obj, cls=None):
        def _method(*args, **kwargs):
            method = self.dispatcher.dispatch(args[0].__class__)
            return method.__get__(obj, cls)(*args, **kwargs)

        _method.__isabstractmethod__ = self.__isabstractmethod__
        _method.register = self.register
        update_wrapper(_method, self.func)
        return _method

    @property
    def __isabstractmethod__(self):
        return getattr(self.func, "__isabstractmethod__", False)


_NOT_FOUND = object()


class cached_property:
    def __init__(self, func):
        self.func = func
        self.attrname = None
        self.__doc__ = func.__doc__
        self.lock = RLock()

    def __set_name__(self, owner, name):
        if self.attrname is None:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                f"Cannot assign the same cached_property to two different names ({self.attrname!r} and {name!r})."
            )

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if self.attrname is None:
            raise TypeError(
                "Cannot use cached_property instance without calling __set_name__ on it."
            )
        try:
            cache = instance.__dict__
        except AttributeError:
            msg = f"No '__dict__' attribute on {type(instance).__name__!r} instance to cache {self.attrname!r} property."
            raise TypeError(msg) from None
        val = cache.get(self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            with self.lock:
                val = cache.get(self.attrname, _NOT_FOUND)
                if val is _NOT_FOUND:
                    val = self.func(instance)
                    try:
                        cache[self.attrname] = val
                    except TypeError:
                        msg = f"The '__dict__' attribute on {type(instance).__name__!r} instance does not support item assignment for caching {self.attrname!r} property."
                        raise TypeError(msg) from None
        return val

    __class_getitem__ = classmethod(GenericAlias)
