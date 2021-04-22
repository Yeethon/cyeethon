"\nA demonstration of classes and their special methods in Python.\n"


class Vec:
    "A simple vector class.\n\n    Instances of the Vec class can be constructed from numbers\n\n    >>> a = Vec(1, 2, 3)\n    >>> b = Vec(3, 2, 1)\n\n    added\n    >>> a + b\n    Vec(4, 4, 4)\n\n    subtracted\n    >>> a - b\n    Vec(-2, 0, 2)\n\n    and multiplied by a scalar on the left\n    >>> 3.0 * a\n    Vec(3.0, 6.0, 9.0)\n\n    or on the right\n    >>> a * 3.0\n    Vec(3.0, 6.0, 9.0)\n\n    and dot product\n    >>> a.dot(b)\n    10\n\n    and printed in vector notation\n    >>> print(a)\n    <1 2 3>\n\n    "

    def __init__(self, *v):
        self.v = list(v)

    @classmethod
    def fromlist(cls, v):
        if not isinstance(v, list):
            raise TypeError
        inst = cls()
        inst.v = v
        return inst

    def __repr__(self):
        args = ", ".join([repr(x) for x in self.v])
        return f"{type(self).__name__}({args})"

    def __str__(self):
        components = " ".join([str(x) for x in self.v])
        return f"<{components}>"

    def __len__(self):
        return len(self.v)

    def __getitem__(self, i):
        return self.v[i]

    def __add__(self, other):
        "Element-wise addition"
        v = [(x + y) for (x, y) in zip(self.v, other.v)]
        return Vec.fromlist(v)

    def __sub__(self, other):
        "Element-wise subtraction"
        v = [(x - y) for (x, y) in zip(self.v, other.v)]
        return Vec.fromlist(v)

    def __mul__(self, scalar):
        "Multiply by scalar"
        v = [(x * scalar) for x in self.v]
        return Vec.fromlist(v)

    __rmul__ = __mul__

    def dot(self, other):
        "Vector dot product"
        if not isinstance(other, Vec):
            raise TypeError
        return sum(((x_i * y_i) for (x_i, y_i) in zip(self, other)))


def test():
    import doctest

    doctest.testmod()


test()
