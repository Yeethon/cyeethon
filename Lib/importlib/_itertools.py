from itertools import filterfalse


def unique_everseen(iterable, key=None):
    "List unique elements, preserving order. Remember all elements ever seen."
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            (yield element)
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                (yield element)
