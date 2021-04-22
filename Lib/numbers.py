"Abstract Base Classes (ABCs) for numbers, according to PEP 3141.\n\nTODO: Fill out more detailed documentation on the operators."
from abc import ABCMeta, abstractmethod

__all__ = ["Number", "Complex", "Real", "Rational", "Integral"]


class Number(metaclass=ABCMeta):
    "All numbers inherit from this class.\n\n    If you just want to check if an argument x is a number, without\n    caring what kind, use isinstance(x, Number).\n    "
    __slots__ = ()
    __hash__ = None


class Complex(Number):
    "Complex defines the operations that work on the builtin complex type.\n\n    In short, those are: a conversion to complex, .real, .imag, +, -,\n    *, /, abs(), .conjugate, ==, and !=.\n\n    If it is given heterogeneous arguments, and doesn't have special\n    knowledge about them, it should fall back to the builtin complex\n    type as described below.\n    "
    __slots__ = ()

    @abstractmethod
    def __complex__(self):
        "Return a builtin complex instance. Called for complex(self)."

    def __bool__(self):
        "True if self != 0. Called for bool(self)."
        return self != 0

    @property
    @abstractmethod
    def real(self):
        "Retrieve the real component of this number.\n\n        This should subclass Real.\n        "
        raise NotImplementedError

    @property
    @abstractmethod
    def imag(self):
        "Retrieve the imaginary component of this number.\n\n        This should subclass Real.\n        "
        raise NotImplementedError

    @abstractmethod
    def __add__(self, other):
        "self + other"
        raise NotImplementedError

    @abstractmethod
    def __radd__(self, other):
        "other + self"
        raise NotImplementedError

    @abstractmethod
    def __neg__(self):
        "-self"
        raise NotImplementedError

    @abstractmethod
    def __pos__(self):
        "+self"
        raise NotImplementedError

    def __sub__(self, other):
        "self - other"
        return self + (-other)

    def __rsub__(self, other):
        "other - self"
        return (-self) + other

    @abstractmethod
    def __mul__(self, other):
        "self * other"
        raise NotImplementedError

    @abstractmethod
    def __rmul__(self, other):
        "other * self"
        raise NotImplementedError

    @abstractmethod
    def __truediv__(self, other):
        "self / other: Should promote to float when necessary."
        raise NotImplementedError

    @abstractmethod
    def __rtruediv__(self, other):
        "other / self"
        raise NotImplementedError

    @abstractmethod
    def __pow__(self, exponent):
        "self**exponent; should promote to float or complex when necessary."
        raise NotImplementedError

    @abstractmethod
    def __rpow__(self, base):
        "base ** self"
        raise NotImplementedError

    @abstractmethod
    def __abs__(self):
        "Returns the Real distance from 0. Called for abs(self)."
        raise NotImplementedError

    @abstractmethod
    def conjugate(self):
        "(x+y*i).conjugate() returns (x-y*i)."
        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other):
        "self == other"
        raise NotImplementedError


Complex.register(complex)


class Real(Complex):
    "To Complex, Real adds the operations that work on real numbers.\n\n    In short, those are: a conversion to float, trunc(), divmod,\n    %, <, <=, >, and >=.\n\n    Real also provides defaults for the derived operations.\n    "
    __slots__ = ()

    @abstractmethod
    def __float__(self):
        "Any Real can be converted to a native float object.\n\n        Called for float(self)."
        raise NotImplementedError

    @abstractmethod
    def __trunc__(self):
        'trunc(self): Truncates self to an Integral.\n\n        Returns an Integral i such that:\n          * i>0 iff self>0;\n          * abs(i) <= abs(self);\n          * for any Integral j satisfying the first two conditions,\n            abs(i) >= abs(j) [i.e. i has "maximal" abs among those].\n        i.e. "truncate towards 0".\n        '
        raise NotImplementedError

    @abstractmethod
    def __floor__(self):
        "Finds the greatest Integral <= self."
        raise NotImplementedError

    @abstractmethod
    def __ceil__(self):
        "Finds the least Integral >= self."
        raise NotImplementedError

    @abstractmethod
    def __round__(self, ndigits=None):
        "Rounds self to ndigits decimal places, defaulting to 0.\n\n        If ndigits is omitted or None, returns an Integral, otherwise\n        returns a Real. Rounds half toward even.\n        "
        raise NotImplementedError

    def __divmod__(self, other):
        "divmod(self, other): The pair (self // other, self % other).\n\n        Sometimes this can be computed faster than the pair of\n        operations.\n        "
        return ((self // other), (self % other))

    def __rdivmod__(self, other):
        "divmod(other, self): The pair (self // other, self % other).\n\n        Sometimes this can be computed faster than the pair of\n        operations.\n        "
        return ((other // self), (other % self))

    @abstractmethod
    def __floordiv__(self, other):
        "self // other: The floor() of self/other."
        raise NotImplementedError

    @abstractmethod
    def __rfloordiv__(self, other):
        "other // self: The floor() of other/self."
        raise NotImplementedError

    @abstractmethod
    def __mod__(self, other):
        "self % other"
        raise NotImplementedError

    @abstractmethod
    def __rmod__(self, other):
        "other % self"
        raise NotImplementedError

    @abstractmethod
    def __lt__(self, other):
        "self < other\n\n        < on Reals defines a total ordering, except perhaps for NaN."
        raise NotImplementedError

    @abstractmethod
    def __le__(self, other):
        "self <= other"
        raise NotImplementedError

    def __complex__(self):
        "complex(self) == complex(float(self), 0)"
        return complex(float(self))

    @property
    def real(self):
        "Real numbers are their real component."
        return +self

    @property
    def imag(self):
        "Real numbers have no imaginary component."
        return 0

    def conjugate(self):
        "Conjugate is a no-op for Reals."
        return +self


Real.register(float)


class Rational(Real):
    ".numerator and .denominator should be in lowest terms."
    __slots__ = ()

    @property
    @abstractmethod
    def numerator(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def denominator(self):
        raise NotImplementedError

    def __float__(self):
        "float(self) = self.numerator / self.denominator\n\n        It's important that this conversion use the integer's \"true\"\n        division rather than casting one side to float before dividing\n        so that ratios of huge integers convert without overflowing.\n\n        "
        return self.numerator / self.denominator


class Integral(Rational):
    "Integral adds a conversion to int and the bit-string operations."
    __slots__ = ()

    @abstractmethod
    def __int__(self):
        "int(self)"
        raise NotImplementedError

    def __index__(self):
        "Called whenever an index is needed, such as in slicing"
        return int(self)

    @abstractmethod
    def __pow__(self, exponent, modulus=None):
        "self ** exponent % modulus, but maybe faster.\n\n        Accept the modulus argument if you want to support the\n        3-argument version of pow(). Raise a TypeError if exponent < 0\n        or any argument isn't Integral. Otherwise, just implement the\n        2-argument version described in Complex.\n        "
        raise NotImplementedError

    @abstractmethod
    def __lshift__(self, other):
        "self << other"
        raise NotImplementedError

    @abstractmethod
    def __rlshift__(self, other):
        "other << self"
        raise NotImplementedError

    @abstractmethod
    def __rshift__(self, other):
        "self >> other"
        raise NotImplementedError

    @abstractmethod
    def __rrshift__(self, other):
        "other >> self"
        raise NotImplementedError

    @abstractmethod
    def __and__(self, other):
        "self & other"
        raise NotImplementedError

    @abstractmethod
    def __rand__(self, other):
        "other & self"
        raise NotImplementedError

    @abstractmethod
    def __xor__(self, other):
        "self ^ other"
        raise NotImplementedError

    @abstractmethod
    def __rxor__(self, other):
        "other ^ self"
        raise NotImplementedError

    @abstractmethod
    def __or__(self, other):
        "self | other"
        raise NotImplementedError

    @abstractmethod
    def __ror__(self, other):
        "other | self"
        raise NotImplementedError

    @abstractmethod
    def __invert__(self):
        "~self"
        raise NotImplementedError

    def __float__(self):
        "float(self) == float(int(self))"
        return float(int(self))

    @property
    def numerator(self):
        "Integers are their own numerators."
        return +self

    @property
    def denominator(self):
        "Integers have a denominator of 1."
        return 1


Integral.register(int)
