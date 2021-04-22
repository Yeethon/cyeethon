"This module implements specialized container datatypes providing\nalternatives to Python's general purpose built-in containers, dict,\nlist, set, and tuple.\n\n* namedtuple   factory function for creating tuple subclasses with named fields\n* deque        list-like container with fast appends and pops on either end\n* ChainMap     dict-like class for creating a single view of multiple mappings\n* Counter      dict subclass for counting hashable objects\n* OrderedDict  dict subclass that remembers the order entries were added\n* defaultdict  dict subclass that calls a factory function to supply missing values\n* UserDict     wrapper around dictionary objects for easier dict subclassing\n* UserList     wrapper around list objects for easier list subclassing\n* UserString   wrapper around string objects for easier string subclassing\n\n"
__all__ = [
    "ChainMap",
    "Counter",
    "OrderedDict",
    "UserDict",
    "UserList",
    "UserString",
    "defaultdict",
    "deque",
    "namedtuple",
]
import _collections_abc
import sys as _sys
from itertools import chain as _chain
from itertools import repeat as _repeat
from itertools import starmap as _starmap
from keyword import iskeyword as _iskeyword
from operator import eq as _eq
from operator import itemgetter as _itemgetter
from reprlib import recursive_repr as _recursive_repr
from _weakref import proxy as _proxy

try:
    from _collections import deque
except ImportError:
    pass
else:
    _collections_abc.MutableSequence.register(deque)
try:
    from _collections import defaultdict
except ImportError:
    pass


class _OrderedDictKeysView(_collections_abc.KeysView):
    def __reversed__(self):
        (yield from reversed(self._mapping))


class _OrderedDictItemsView(_collections_abc.ItemsView):
    def __reversed__(self):
        for key in reversed(self._mapping):
            (yield (key, self._mapping[key]))


class _OrderedDictValuesView(_collections_abc.ValuesView):
    def __reversed__(self):
        for key in reversed(self._mapping):
            (yield self._mapping[key])


class _Link(object):
    __slots__ = ("prev", "next", "key", "__weakref__")


class OrderedDict(dict):
    "Dictionary that remembers insertion order"

    def __init__(self, other=(), /, **kwds):
        "Initialize an ordered dictionary.  The signature is the same as\n        regular dictionaries.  Keyword argument order is preserved.\n        "
        try:
            self.__root
        except AttributeError:
            self.__hardroot = _Link()
            self.__root = root = _proxy(self.__hardroot)
            root.prev = root.next = root
            self.__map = {}
        self.__update(other, **kwds)

    def __setitem__(
        self, key, value, dict_setitem=dict.__setitem__, proxy=_proxy, Link=_Link
    ):
        "od.__setitem__(i, y) <==> od[i]=y"
        if key not in self:
            self.__map[key] = link = Link()
            root = self.__root
            last = root.prev
            (link.prev, link.next, link.key) = (last, root, key)
            last.next = link
            root.prev = proxy(link)
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        "od.__delitem__(y) <==> del od[y]"
        dict_delitem(self, key)
        link = self.__map.pop(key)
        link_prev = link.prev
        link_next = link.next
        link_prev.next = link_next
        link_next.prev = link_prev
        link.prev = None
        link.next = None

    def __iter__(self):
        "od.__iter__() <==> iter(od)"
        root = self.__root
        curr = root.next
        while curr is not root:
            (yield curr.key)
            curr = curr.next

    def __reversed__(self):
        "od.__reversed__() <==> reversed(od)"
        root = self.__root
        curr = root.prev
        while curr is not root:
            (yield curr.key)
            curr = curr.prev

    def clear(self):
        "od.clear() -> None.  Remove all items from od."
        root = self.__root
        root.prev = root.next = root
        self.__map.clear()
        dict.clear(self)

    def popitem(self, last=True):
        "Remove and return a (key, value) pair from the dictionary.\n\n        Pairs are returned in LIFO order if last is true or FIFO order if false.\n        "
        if not self:
            raise KeyError("dictionary is empty")
        root = self.__root
        if last:
            link = root.prev
            link_prev = link.prev
            link_prev.next = root
            root.prev = link_prev
        else:
            link = root.next
            link_next = link.next
            root.next = link_next
            link_next.prev = root
        key = link.key
        del self.__map[key]
        value = dict.pop(self, key)
        return (key, value)

    def move_to_end(self, key, last=True):
        "Move an existing element to the end (or beginning if last is false).\n\n        Raise KeyError if the element does not exist.\n        "
        link = self.__map[key]
        link_prev = link.prev
        link_next = link.next
        soft_link = link_next.prev
        link_prev.next = link_next
        link_next.prev = link_prev
        root = self.__root
        if last:
            last = root.prev
            link.prev = last
            link.next = root
            root.prev = soft_link
            last.next = link
        else:
            first = root.next
            link.prev = root
            link.next = first
            first.prev = soft_link
            root.next = link

    def __sizeof__(self):
        sizeof = _sys.getsizeof
        n = len(self) + 1
        size = sizeof(self.__dict__)
        size += sizeof(self.__map) * 2
        size += sizeof(self.__hardroot) * n
        size += sizeof(self.__root) * n
        return size

    update = __update = _collections_abc.MutableMapping.update

    def keys(self):
        "D.keys() -> a set-like object providing a view on D's keys"
        return _OrderedDictKeysView(self)

    def items(self):
        "D.items() -> a set-like object providing a view on D's items"
        return _OrderedDictItemsView(self)

    def values(self):
        "D.values() -> an object providing a view on D's values"
        return _OrderedDictValuesView(self)

    __ne__ = _collections_abc.MutableMapping.__ne__
    __marker = object()

    def pop(self, key, default=__marker):
        "od.pop(k[,d]) -> v, remove specified key and return the corresponding\n        value.  If key is not found, d is returned if given, otherwise KeyError\n        is raised.\n\n        "
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        "Insert key with a value of default if key is not in the dictionary.\n\n        Return the value for key if key is in the dictionary, else default.\n        "
        if key in self:
            return self[key]
        self[key] = default
        return default

    @_recursive_repr()
    def __repr__(self):
        "od.__repr__() <==> repr(od)"
        if not self:
            return "%s()" % (self.__class__.__name__,)
        return "%s(%r)" % (self.__class__.__name__, list(self.items()))

    def __reduce__(self):
        "Return state information for pickling"
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        return (self.__class__, (), (inst_dict or None), None, iter(self.items()))

    def copy(self):
        "od.copy() -> a shallow copy of od"
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        "Create a new ordered dictionary with keys from iterable and values set to value.\n        "
        self = cls()
        for key in iterable:
            self[key] = value
        return self

    def __eq__(self, other):
        "od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive\n        while comparison to a regular mapping is order-insensitive.\n\n        "
        if isinstance(other, OrderedDict):
            return dict.__eq__(self, other) and all(map(_eq, self, other))
        return dict.__eq__(self, other)

    def __ior__(self, other):
        self.update(other)
        return self

    def __or__(self, other):
        if not isinstance(other, dict):
            return NotImplemented
        new = self.__class__(self)
        new.update(other)
        return new

    def __ror__(self, other):
        if not isinstance(other, dict):
            return NotImplemented
        new = self.__class__(other)
        new.update(self)
        return new


try:
    from _collections import OrderedDict
except ImportError:
    pass
try:
    from _collections import _tuplegetter
except ImportError:
    _tuplegetter = lambda index, doc: property(_itemgetter(index), doc=doc)


def namedtuple(typename, field_names, *, rename=False, defaults=None, module=None):
    "Returns a new subclass of tuple with named fields.\n\n    >>> Point = namedtuple('Point', ['x', 'y'])\n    >>> Point.__doc__                   # docstring for the new class\n    'Point(x, y)'\n    >>> p = Point(11, y=22)             # instantiate with positional args or keywords\n    >>> p[0] + p[1]                     # indexable like a plain tuple\n    33\n    >>> x, y = p                        # unpack like a regular tuple\n    >>> x, y\n    (11, 22)\n    >>> p.x + p.y                       # fields also accessible by name\n    33\n    >>> d = p._asdict()                 # convert to a dictionary\n    >>> d['x']\n    11\n    >>> Point(**d)                      # convert from a dictionary\n    Point(x=11, y=22)\n    >>> p._replace(x=100)               # _replace() is like str.replace() but targets named fields\n    Point(x=100, y=22)\n\n    "
    if isinstance(field_names, str):
        field_names = field_names.replace(",", " ").split()
    field_names = list(map(str, field_names))
    typename = _sys.intern(str(typename))
    if rename:
        seen = set()
        for (index, name) in enumerate(field_names):
            if (
                (not name.isidentifier())
                or _iskeyword(name)
                or name.startswith("_")
                or (name in seen)
            ):
                field_names[index] = f"_{index}"
            seen.add(name)
    for name in [typename] + field_names:
        if type(name) is not str:
            raise TypeError("Type names and field names must be strings")
        if not name.isidentifier():
            raise ValueError(
                f"Type names and field names must be valid identifiers: {name!r}"
            )
        if _iskeyword(name):
            raise ValueError(
                f"Type names and field names cannot be a keyword: {name!r}"
            )
    seen = set()
    for name in field_names:
        if name.startswith("_") and (not rename):
            raise ValueError(f"Field names cannot start with an underscore: {name!r}")
        if name in seen:
            raise ValueError(f"Encountered duplicate field name: {name!r}")
        seen.add(name)
    field_defaults = {}
    if defaults is not None:
        defaults = tuple(defaults)
        if len(defaults) > len(field_names):
            raise TypeError("Got more default values than field names")
        field_defaults = dict(
            reversed(list(zip(reversed(field_names), reversed(defaults))))
        )
    field_names = tuple(map(_sys.intern, field_names))
    num_fields = len(field_names)
    arg_list = ", ".join(field_names)
    if num_fields == 1:
        arg_list += ","
    repr_fmt = ("(" + ", ".join((f"{name}=%r" for name in field_names))) + ")"
    tuple_new = tuple.__new__
    (_dict, _tuple, _len, _map, _zip) = (dict, tuple, len, map, zip)
    namespace = {
        "_tuple_new": tuple_new,
        "__builtins__": {},
        "__name__": f"namedtuple_{typename}",
    }
    code = f"lambda _cls, {arg_list}: _tuple_new(_cls, ({arg_list}))"
    __new__ = eval(code, namespace)
    __new__.__name__ = "__new__"
    __new__.__doc__ = f"Create new instance of {typename}({arg_list})"
    if defaults is not None:
        __new__.__defaults__ = defaults

    @classmethod
    def _make(cls, iterable):
        result = tuple_new(cls, iterable)
        if _len(result) != num_fields:
            raise TypeError(f"Expected {num_fields} arguments, got {len(result)}")
        return result

    _make.__func__.__doc__ = f"Make a new {typename} object from a sequence or iterable"

    def _replace(self, /, **kwds):
        result = self._make(_map(kwds.pop, field_names, self))
        if kwds:
            raise ValueError(f"Got unexpected field names: {list(kwds)!r}")
        return result

    _replace.__doc__ = (
        f"Return a new {typename} object replacing specified fields with new values"
    )

    def __repr__(self):
        "Return a nicely formatted representation string"
        return self.__class__.__name__ + (repr_fmt % self)

    def _asdict(self):
        "Return a new dict which maps field names to their values."
        return _dict(_zip(self._fields, self))

    def __getnewargs__(self):
        "Return self as a plain tuple.  Used by copy and pickle."
        return _tuple(self)

    for method in (
        __new__,
        _make.__func__,
        _replace,
        __repr__,
        _asdict,
        __getnewargs__,
    ):
        method.__qualname__ = f"{typename}.{method.__name__}"
    class_namespace = {
        "__doc__": f"{typename}({arg_list})",
        "__slots__": (),
        "_fields": field_names,
        "_field_defaults": field_defaults,
        "__new__": __new__,
        "_make": _make,
        "_replace": _replace,
        "__repr__": __repr__,
        "_asdict": _asdict,
        "__getnewargs__": __getnewargs__,
        "__match_args__": field_names,
    }
    for (index, name) in enumerate(field_names):
        doc = _sys.intern(f"Alias for field number {index}")
        class_namespace[name] = _tuplegetter(index, doc)
    result = type(typename, (tuple,), class_namespace)
    if module is None:
        try:
            module = _sys._getframe(1).f_globals.get("__name__", "__main__")
        except (AttributeError, ValueError):
            pass
    if module is not None:
        result.__module__ = module
    return result


def _count_elements(mapping, iterable):
    "Tally elements from the iterable."
    mapping_get = mapping.get
    for elem in iterable:
        mapping[elem] = mapping_get(elem, 0) + 1


try:
    from _collections import _count_elements
except ImportError:
    pass


class Counter(dict):
    "Dict subclass for counting hashable items.  Sometimes called a bag\n    or multiset.  Elements are stored as dictionary keys and their counts\n    are stored as dictionary values.\n\n    >>> c = Counter('abcdeabcdabcaba')  # count elements from a string\n\n    >>> c.most_common(3)                # three most common elements\n    [('a', 5), ('b', 4), ('c', 3)]\n    >>> sorted(c)                       # list all unique elements\n    ['a', 'b', 'c', 'd', 'e']\n    >>> ''.join(sorted(c.elements()))   # list elements with repetitions\n    'aaaaabbbbcccdde'\n    >>> sum(c.values())                 # total of all counts\n    15\n\n    >>> c['a']                          # count of letter 'a'\n    5\n    >>> for elem in 'shazam':           # update counts from an iterable\n    ...     c[elem] += 1                # by adding 1 to each element's count\n    >>> c['a']                          # now there are seven 'a'\n    7\n    >>> del c['b']                      # remove all 'b'\n    >>> c['b']                          # now there are zero 'b'\n    0\n\n    >>> d = Counter('simsalabim')       # make another counter\n    >>> c.update(d)                     # add in the second counter\n    >>> c['a']                          # now there are nine 'a'\n    9\n\n    >>> c.clear()                       # empty the counter\n    >>> c\n    Counter()\n\n    Note:  If a count is set to zero or reduced to zero, it will remain\n    in the counter until the entry is deleted or the counter is cleared:\n\n    >>> c = Counter('aaabbc')\n    >>> c['b'] -= 2                     # reduce the count of 'b' by two\n    >>> c.most_common()                 # 'b' is still in, but its count is zero\n    [('a', 3), ('c', 1), ('b', 0)]\n\n    "

    def __init__(self, iterable=None, /, **kwds):
        "Create a new, empty Counter object.  And if given, count elements\n        from an input iterable.  Or, initialize the count from another mapping\n        of elements to their counts.\n\n        >>> c = Counter()                           # a new, empty counter\n        >>> c = Counter('gallahad')                 # a new counter from an iterable\n        >>> c = Counter({'a': 4, 'b': 2})           # a new counter from a mapping\n        >>> c = Counter(a=4, b=2)                   # a new counter from keyword args\n\n        "
        super().__init__()
        self.update(iterable, **kwds)

    def __missing__(self, key):
        "The count of elements not in the Counter is zero."
        return 0

    def most_common(self, n=None):
        "List the n most common elements and their counts from the most\n        common to the least.  If n is None, then list all element counts.\n\n        >>> Counter('abracadabra').most_common(3)\n        [('a', 5), ('b', 2), ('r', 2)]\n\n        "
        if n is None:
            return sorted(self.items(), key=_itemgetter(1), reverse=True)
        import heapq

        return heapq.nlargest(n, self.items(), key=_itemgetter(1))

    def elements(self):
        "Iterator over elements repeating each as many times as its count.\n\n        >>> c = Counter('ABCABC')\n        >>> sorted(c.elements())\n        ['A', 'A', 'B', 'B', 'C', 'C']\n\n        # Knuth's example for prime factors of 1836:  2**2 * 3**3 * 17**1\n        >>> prime_factors = Counter({2: 2, 3: 3, 17: 1})\n        >>> product = 1\n        >>> for factor in prime_factors.elements():     # loop over factors\n        ...     product *= factor                       # and multiply them\n        >>> product\n        1836\n\n        Note, if an element's count has been set to zero or is a negative\n        number, elements() will ignore it.\n\n        "
        return _chain.from_iterable(_starmap(_repeat, self.items()))

    @classmethod
    def fromkeys(cls, iterable, v=None):
        raise NotImplementedError(
            "Counter.fromkeys() is undefined.  Use Counter(iterable) instead."
        )

    def update(self, iterable=None, /, **kwds):
        "Like dict.update() but add counts instead of replacing them.\n\n        Source can be an iterable, a dictionary, or another Counter instance.\n\n        >>> c = Counter('which')\n        >>> c.update('witch')           # add elements from another iterable\n        >>> d = Counter('watch')\n        >>> c.update(d)                 # add elements from another counter\n        >>> c['h']                      # four 'h' in which, witch, and watch\n        4\n\n        "
        if iterable is not None:
            if isinstance(iterable, _collections_abc.Mapping):
                if self:
                    self_get = self.get
                    for (elem, count) in iterable.items():
                        self[elem] = count + self_get(elem, 0)
                else:
                    super().update(iterable)
            else:
                _count_elements(self, iterable)
        if kwds:
            self.update(kwds)

    def subtract(self, iterable=None, /, **kwds):
        "Like dict.update() but subtracts counts instead of replacing them.\n        Counts can be reduced below zero.  Both the inputs and outputs are\n        allowed to contain zero and negative counts.\n\n        Source can be an iterable, a dictionary, or another Counter instance.\n\n        >>> c = Counter('which')\n        >>> c.subtract('witch')             # subtract elements from another iterable\n        >>> c.subtract(Counter('watch'))    # subtract elements from another counter\n        >>> c['h']                          # 2 in which, minus 1 in witch, minus 1 in watch\n        0\n        >>> c['w']                          # 1 in which, minus 1 in witch, minus 1 in watch\n        -1\n\n        "
        if iterable is not None:
            self_get = self.get
            if isinstance(iterable, _collections_abc.Mapping):
                for (elem, count) in iterable.items():
                    self[elem] = self_get(elem, 0) - count
            else:
                for elem in iterable:
                    self[elem] = self_get(elem, 0) - 1
        if kwds:
            self.subtract(kwds)

    def copy(self):
        "Return a shallow copy."
        return self.__class__(self)

    def __reduce__(self):
        return (self.__class__, (dict(self),))

    def __delitem__(self, elem):
        "Like dict.__delitem__() but does not raise KeyError for missing values."
        if elem in self:
            super().__delitem__(elem)

    def __eq__(self, other):
        "True if all counts agree. Missing counts are treated as zero."
        if not isinstance(other, Counter):
            return NotImplemented
        return all(((self[e] == other[e]) for c in (self, other) for e in c))

    def __ne__(self, other):
        "True if any counts disagree. Missing counts are treated as zero."
        if not isinstance(other, Counter):
            return NotImplemented
        return not (self == other)

    def __le__(self, other):
        "True if all counts in self are a subset of those in other."
        if not isinstance(other, Counter):
            return NotImplemented
        return all(((self[e] <= other[e]) for c in (self, other) for e in c))

    def __lt__(self, other):
        "True if all counts in self are a proper subset of those in other."
        if not isinstance(other, Counter):
            return NotImplemented
        return (self <= other) and (self != other)

    def __ge__(self, other):
        "True if all counts in self are a superset of those in other."
        if not isinstance(other, Counter):
            return NotImplemented
        return all(((self[e] >= other[e]) for c in (self, other) for e in c))

    def __gt__(self, other):
        "True if all counts in self are a proper superset of those in other."
        if not isinstance(other, Counter):
            return NotImplemented
        return (self >= other) and (self != other)

    def __repr__(self):
        if not self:
            return f"{self.__class__.__name__}()"
        try:
            d = dict(self.most_common())
        except TypeError:
            d = dict(self)
        return f"{self.__class__.__name__}({d!r})"

    def __add__(self, other):
        "Add counts from two counters.\n\n        >>> Counter('abbb') + Counter('bcc')\n        Counter({'b': 4, 'c': 2, 'a': 1})\n\n        "
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for (elem, count) in self.items():
            newcount = count + other[elem]
            if newcount > 0:
                result[elem] = newcount
        for (elem, count) in other.items():
            if (elem not in self) and (count > 0):
                result[elem] = count
        return result

    def __sub__(self, other):
        " Subtract count, but keep only results with positive counts.\n\n        >>> Counter('abbbc') - Counter('bccd')\n        Counter({'b': 2, 'a': 1})\n\n        "
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for (elem, count) in self.items():
            newcount = count - other[elem]
            if newcount > 0:
                result[elem] = newcount
        for (elem, count) in other.items():
            if (elem not in self) and (count < 0):
                result[elem] = 0 - count
        return result

    def __or__(self, other):
        "Union is the maximum of value in either of the input counters.\n\n        >>> Counter('abbb') | Counter('bcc')\n        Counter({'b': 3, 'c': 2, 'a': 1})\n\n        "
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for (elem, count) in self.items():
            other_count = other[elem]
            newcount = other_count if (count < other_count) else count
            if newcount > 0:
                result[elem] = newcount
        for (elem, count) in other.items():
            if (elem not in self) and (count > 0):
                result[elem] = count
        return result

    def __and__(self, other):
        " Intersection is the minimum of corresponding counts.\n\n        >>> Counter('abbb') & Counter('bcc')\n        Counter({'b': 1})\n\n        "
        if not isinstance(other, Counter):
            return NotImplemented
        result = Counter()
        for (elem, count) in self.items():
            other_count = other[elem]
            newcount = count if (count < other_count) else other_count
            if newcount > 0:
                result[elem] = newcount
        return result

    def __pos__(self):
        "Adds an empty counter, effectively stripping negative and zero counts"
        result = Counter()
        for (elem, count) in self.items():
            if count > 0:
                result[elem] = count
        return result

    def __neg__(self):
        "Subtracts from an empty counter.  Strips positive and zero counts,\n        and flips the sign on negative counts.\n\n        "
        result = Counter()
        for (elem, count) in self.items():
            if count < 0:
                result[elem] = 0 - count
        return result

    def _keep_positive(self):
        "Internal method to strip elements with a negative or zero count"
        nonpositive = [elem for (elem, count) in self.items() if (not (count > 0))]
        for elem in nonpositive:
            del self[elem]
        return self

    def __iadd__(self, other):
        "Inplace add from another counter, keeping only positive counts.\n\n        >>> c = Counter('abbb')\n        >>> c += Counter('bcc')\n        >>> c\n        Counter({'b': 4, 'c': 2, 'a': 1})\n\n        "
        for (elem, count) in other.items():
            self[elem] += count
        return self._keep_positive()

    def __isub__(self, other):
        "Inplace subtract counter, but keep only results with positive counts.\n\n        >>> c = Counter('abbbc')\n        >>> c -= Counter('bccd')\n        >>> c\n        Counter({'b': 2, 'a': 1})\n\n        "
        for (elem, count) in other.items():
            self[elem] -= count
        return self._keep_positive()

    def __ior__(self, other):
        "Inplace union is the maximum of value from either counter.\n\n        >>> c = Counter('abbb')\n        >>> c |= Counter('bcc')\n        >>> c\n        Counter({'b': 3, 'c': 2, 'a': 1})\n\n        "
        for (elem, other_count) in other.items():
            count = self[elem]
            if other_count > count:
                self[elem] = other_count
        return self._keep_positive()

    def __iand__(self, other):
        "Inplace intersection is the minimum of corresponding counts.\n\n        >>> c = Counter('abbb')\n        >>> c &= Counter('bcc')\n        >>> c\n        Counter({'b': 1})\n\n        "
        for (elem, count) in self.items():
            other_count = other[elem]
            if other_count < count:
                self[elem] = other_count
        return self._keep_positive()


class ChainMap(_collections_abc.MutableMapping):
    " A ChainMap groups multiple dicts (or other mappings) together\n    to create a single, updateable view.\n\n    The underlying mappings are stored in a list.  That list is public and can\n    be accessed or updated using the *maps* attribute.  There is no other\n    state.\n\n    Lookups search the underlying mappings successively until a key is found.\n    In contrast, writes, updates, and deletions only operate on the first\n    mapping.\n\n    "

    def __init__(self, *maps):
        "Initialize a ChainMap by setting *maps* to the given mappings.\n        If no mappings are provided, a single empty dictionary is used.\n\n        "
        self.maps = list(maps) or [{}]

    def __missing__(self, key):
        raise KeyError(key)

    def __getitem__(self, key):
        for mapping in self.maps:
            try:
                return mapping[key]
            except KeyError:
                pass
        return self.__missing__(key)

    def get(self, key, default=None):
        return self[key] if (key in self) else default

    def __len__(self):
        return len(set().union(*self.maps))

    def __iter__(self):
        d = {}
        for mapping in reversed(self.maps):
            d.update(dict.fromkeys(mapping))
        return iter(d)

    def __contains__(self, key):
        return any(((key in m) for m in self.maps))

    def __bool__(self):
        return any(self.maps)

    @_recursive_repr()
    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join(map(repr, self.maps))})"

    @classmethod
    def fromkeys(cls, iterable, *args):
        "Create a ChainMap with a single dict created from the iterable."
        return cls(dict.fromkeys(iterable, *args))

    def copy(self):
        "New ChainMap or subclass with a new copy of maps[0] and refs to maps[1:]"
        return self.__class__(self.maps[0].copy(), *self.maps[1:])

    __copy__ = copy

    def new_child(self, m=None, **kwargs):
        "New ChainMap with a new map followed by all previous maps.\n        If no map is provided, an empty dict is used.\n        Keyword arguments update the map or new empty dict.\n        "
        if m is None:
            m = kwargs
        elif kwargs:
            m.update(kwargs)
        return self.__class__(m, *self.maps)

    @property
    def parents(self):
        "New ChainMap from maps[1:]."
        return self.__class__(*self.maps[1:])

    def __setitem__(self, key, value):
        self.maps[0][key] = value

    def __delitem__(self, key):
        try:
            del self.maps[0][key]
        except KeyError:
            raise KeyError(f"Key not found in the first mapping: {key!r}")

    def popitem(self):
        "Remove and return an item pair from maps[0]. Raise KeyError is maps[0] is empty."
        try:
            return self.maps[0].popitem()
        except KeyError:
            raise KeyError("No keys found in the first mapping.")

    def pop(self, key, *args):
        "Remove *key* from maps[0] and return its value. Raise KeyError if *key* not in maps[0]."
        try:
            return self.maps[0].pop(key, *args)
        except KeyError:
            raise KeyError(f"Key not found in the first mapping: {key!r}")

    def clear(self):
        "Clear maps[0], leaving maps[1:] intact."
        self.maps[0].clear()

    def __ior__(self, other):
        self.maps[0].update(other)
        return self

    def __or__(self, other):
        if not isinstance(other, _collections_abc.Mapping):
            return NotImplemented
        m = self.copy()
        m.maps[0].update(other)
        return m

    def __ror__(self, other):
        if not isinstance(other, _collections_abc.Mapping):
            return NotImplemented
        m = dict(other)
        for child in reversed(self.maps):
            m.update(child)
        return self.__class__(m)


class UserDict(_collections_abc.MutableMapping):
    def __init__(self, dict=None, /, **kwargs):
        self.data = {}
        if dict is not None:
            self.update(dict)
        if kwargs:
            self.update(kwargs)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        if hasattr(self.__class__, "__missing__"):
            return self.__class__.__missing__(self, key)
        raise KeyError(key)

    def __setitem__(self, key, item):
        self.data[key] = item

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __contains__(self, key):
        return key in self.data

    def __repr__(self):
        return repr(self.data)

    def __or__(self, other):
        if isinstance(other, UserDict):
            return self.__class__((self.data | other.data))
        if isinstance(other, dict):
            return self.__class__((self.data | other))
        return NotImplemented

    def __ror__(self, other):
        if isinstance(other, UserDict):
            return self.__class__((other.data | self.data))
        if isinstance(other, dict):
            return self.__class__((other | self.data))
        return NotImplemented

    def __ior__(self, other):
        if isinstance(other, UserDict):
            self.data |= other.data
        else:
            self.data |= other
        return self

    def __copy__(self):
        inst = self.__class__.__new__(self.__class__)
        inst.__dict__.update(self.__dict__)
        inst.__dict__["data"] = self.__dict__["data"].copy()
        return inst

    def copy(self):
        if self.__class__ is UserDict:
            return UserDict(self.data.copy())
        import copy

        data = self.data
        try:
            self.data = {}
            c = copy.copy(self)
        finally:
            self.data = data
        c.update(self)
        return c

    @classmethod
    def fromkeys(cls, iterable, value=None):
        d = cls()
        for key in iterable:
            d[key] = value
        return d


class UserList(_collections_abc.MutableSequence):
    "A more or less complete user-defined wrapper around list objects."

    def __init__(self, initlist=None):
        self.data = []
        if initlist is not None:
            if type(initlist) == type(self.data):
                self.data[:] = initlist
            elif isinstance(initlist, UserList):
                self.data[:] = initlist.data[:]
            else:
                self.data = list(initlist)

    def __repr__(self):
        return repr(self.data)

    def __lt__(self, other):
        return self.data < self.__cast(other)

    def __le__(self, other):
        return self.data <= self.__cast(other)

    def __eq__(self, other):
        return self.data == self.__cast(other)

    def __gt__(self, other):
        return self.data > self.__cast(other)

    def __ge__(self, other):
        return self.data >= self.__cast(other)

    def __cast(self, other):
        return other.data if isinstance(other, UserList) else other

    def __contains__(self, item):
        return item in self.data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, i):
        if isinstance(i, slice):
            return self.__class__(self.data[i])
        else:
            return self.data[i]

    def __setitem__(self, i, item):
        self.data[i] = item

    def __delitem__(self, i):
        del self.data[i]

    def __add__(self, other):
        if isinstance(other, UserList):
            return self.__class__((self.data + other.data))
        elif isinstance(other, type(self.data)):
            return self.__class__((self.data + other))
        return self.__class__((self.data + list(other)))

    def __radd__(self, other):
        if isinstance(other, UserList):
            return self.__class__((other.data + self.data))
        elif isinstance(other, type(self.data)):
            return self.__class__((other + self.data))
        return self.__class__((list(other) + self.data))

    def __iadd__(self, other):
        if isinstance(other, UserList):
            self.data += other.data
        elif isinstance(other, type(self.data)):
            self.data += other
        else:
            self.data += list(other)
        return self

    def __mul__(self, n):
        return self.__class__((self.data * n))

    __rmul__ = __mul__

    def __imul__(self, n):
        self.data *= n
        return self

    def __copy__(self):
        inst = self.__class__.__new__(self.__class__)
        inst.__dict__.update(self.__dict__)
        inst.__dict__["data"] = self.__dict__["data"][:]
        return inst

    def append(self, item):
        self.data.append(item)

    def insert(self, i, item):
        self.data.insert(i, item)

    def pop(self, i=(-1)):
        return self.data.pop(i)

    def remove(self, item):
        self.data.remove(item)

    def clear(self):
        self.data.clear()

    def copy(self):
        return self.__class__(self)

    def count(self, item):
        return self.data.count(item)

    def index(self, item, *args):
        return self.data.index(item, *args)

    def reverse(self):
        self.data.reverse()

    def sort(self, /, *args, **kwds):
        self.data.sort(*args, **kwds)

    def extend(self, other):
        if isinstance(other, UserList):
            self.data.extend(other.data)
        else:
            self.data.extend(other)


class UserString(_collections_abc.Sequence):
    def __init__(self, seq):
        if isinstance(seq, str):
            self.data = seq
        elif isinstance(seq, UserString):
            self.data = seq.data[:]
        else:
            self.data = str(seq)

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return repr(self.data)

    def __int__(self):
        return int(self.data)

    def __float__(self):
        return float(self.data)

    def __complex__(self):
        return complex(self.data)

    def __hash__(self):
        return hash(self.data)

    def __getnewargs__(self):
        return (self.data[:],)

    def __eq__(self, string):
        if isinstance(string, UserString):
            return self.data == string.data
        return self.data == string

    def __lt__(self, string):
        if isinstance(string, UserString):
            return self.data < string.data
        return self.data < string

    def __le__(self, string):
        if isinstance(string, UserString):
            return self.data <= string.data
        return self.data <= string

    def __gt__(self, string):
        if isinstance(string, UserString):
            return self.data > string.data
        return self.data > string

    def __ge__(self, string):
        if isinstance(string, UserString):
            return self.data >= string.data
        return self.data >= string

    def __contains__(self, char):
        if isinstance(char, UserString):
            char = char.data
        return char in self.data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return self.__class__(self.data[index])

    def __add__(self, other):
        if isinstance(other, UserString):
            return self.__class__((self.data + other.data))
        elif isinstance(other, str):
            return self.__class__((self.data + other))
        return self.__class__((self.data + str(other)))

    def __radd__(self, other):
        if isinstance(other, str):
            return self.__class__((other + self.data))
        return self.__class__((str(other) + self.data))

    def __mul__(self, n):
        return self.__class__((self.data * n))

    __rmul__ = __mul__

    def __mod__(self, args):
        return self.__class__((self.data % args))

    def __rmod__(self, template):
        return self.__class__((str(template) % self))

    def capitalize(self):
        return self.__class__(self.data.capitalize())

    def casefold(self):
        return self.__class__(self.data.casefold())

    def center(self, width, *args):
        return self.__class__(self.data.center(width, *args))

    def count(self, sub, start=0, end=_sys.maxsize):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.count(sub, start, end)

    def removeprefix(self, prefix, /):
        if isinstance(prefix, UserString):
            prefix = prefix.data
        return self.__class__(self.data.removeprefix(prefix))

    def removesuffix(self, suffix, /):
        if isinstance(suffix, UserString):
            suffix = suffix.data
        return self.__class__(self.data.removesuffix(suffix))

    def encode(self, encoding="utf-8", errors="strict"):
        encoding = "utf-8" if (encoding is None) else encoding
        errors = "strict" if (errors is None) else errors
        return self.data.encode(encoding, errors)

    def endswith(self, suffix, start=0, end=_sys.maxsize):
        return self.data.endswith(suffix, start, end)

    def expandtabs(self, tabsize=8):
        return self.__class__(self.data.expandtabs(tabsize))

    def find(self, sub, start=0, end=_sys.maxsize):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.find(sub, start, end)

    def format(self, /, *args, **kwds):
        return self.data.format(*args, **kwds)

    def format_map(self, mapping):
        return self.data.format_map(mapping)

    def index(self, sub, start=0, end=_sys.maxsize):
        return self.data.index(sub, start, end)

    def isalpha(self):
        return self.data.isalpha()

    def isalnum(self):
        return self.data.isalnum()

    def isascii(self):
        return self.data.isascii()

    def isdecimal(self):
        return self.data.isdecimal()

    def isdigit(self):
        return self.data.isdigit()

    def isidentifier(self):
        return self.data.isidentifier()

    def islower(self):
        return self.data.islower()

    def isnumeric(self):
        return self.data.isnumeric()

    def isprintable(self):
        return self.data.isprintable()

    def isspace(self):
        return self.data.isspace()

    def istitle(self):
        return self.data.istitle()

    def isupper(self):
        return self.data.isupper()

    def join(self, seq):
        return self.data.join(seq)

    def ljust(self, width, *args):
        return self.__class__(self.data.ljust(width, *args))

    def lower(self):
        return self.__class__(self.data.lower())

    def lstrip(self, chars=None):
        return self.__class__(self.data.lstrip(chars))

    maketrans = str.maketrans

    def partition(self, sep):
        return self.data.partition(sep)

    def replace(self, old, new, maxsplit=(-1)):
        if isinstance(old, UserString):
            old = old.data
        if isinstance(new, UserString):
            new = new.data
        return self.__class__(self.data.replace(old, new, maxsplit))

    def rfind(self, sub, start=0, end=_sys.maxsize):
        if isinstance(sub, UserString):
            sub = sub.data
        return self.data.rfind(sub, start, end)

    def rindex(self, sub, start=0, end=_sys.maxsize):
        return self.data.rindex(sub, start, end)

    def rjust(self, width, *args):
        return self.__class__(self.data.rjust(width, *args))

    def rpartition(self, sep):
        return self.data.rpartition(sep)

    def rstrip(self, chars=None):
        return self.__class__(self.data.rstrip(chars))

    def split(self, sep=None, maxsplit=(-1)):
        return self.data.split(sep, maxsplit)

    def rsplit(self, sep=None, maxsplit=(-1)):
        return self.data.rsplit(sep, maxsplit)

    def splitlines(self, keepends=False):
        return self.data.splitlines(keepends)

    def startswith(self, prefix, start=0, end=_sys.maxsize):
        return self.data.startswith(prefix, start, end)

    def strip(self, chars=None):
        return self.__class__(self.data.strip(chars))

    def swapcase(self):
        return self.__class__(self.data.swapcase())

    def title(self):
        return self.__class__(self.data.title())

    def translate(self, *args):
        return self.__class__(self.data.translate(*args))

    def upper(self):
        return self.__class__(self.data.upper())

    def zfill(self, width):
        return self.__class__(self.data.zfill(width))
