"Fraction, infinite-precision, real numbers."
from decimal import Decimal
import math
import numbers
import operator
import re
import sys

__all__ = ["Fraction"]
_PyHASH_MODULUS = sys.hash_info.modulus
_PyHASH_INF = sys.hash_info.inf
_RATIONAL_FORMAT = re.compile(
    "\n    \\A\\s*                      # optional whitespace at the start, then\n    (?P<sign>[-+]?)            # an optional sign, then\n    (?=\\d|\\.\\d)                # lookahead for digit or .digit\n    (?P<num>\\d*)               # numerator (possibly empty)\n    (?:                        # followed by\n       (?:/(?P<denom>\\d+))?    # an optional denominator\n    |                          # or\n       (?:\\.(?P<decimal>\\d*))? # an optional fractional part\n       (?:E(?P<exp>[-+]?\\d+))? # and optional exponent\n    )\n    \\s*\\Z                      # and optional whitespace to finish\n",
    (re.VERBOSE | re.IGNORECASE),
)


class Fraction(numbers.Rational):
    "This class implements rational numbers.\n\n    In the two-argument form of the constructor, Fraction(8, 6) will\n    produce a rational number equivalent to 4/3. Both arguments must\n    be Rational. The numerator defaults to 0 and the denominator\n    defaults to 1 so that Fraction(3) == 3 and Fraction() == 0.\n\n    Fractions can also be constructed from:\n\n      - numeric strings similar to those accepted by the\n        float constructor (for example, '-2.3' or '1e10')\n\n      - strings of the form '123/456'\n\n      - float and Decimal instances\n\n      - other Rational instances (including integers)\n\n    "
    __slots__ = ("_numerator", "_denominator")

    def __new__(cls, numerator=0, denominator=None, *, _normalize=True):
        "Constructs a Rational.\n\n        Takes a string like '3/2' or '1.5', another Rational instance, a\n        numerator/denominator pair, or a float.\n\n        Examples\n        --------\n\n        >>> Fraction(10, -8)\n        Fraction(-5, 4)\n        >>> Fraction(Fraction(1, 7), 5)\n        Fraction(1, 35)\n        >>> Fraction(Fraction(1, 7), Fraction(2, 3))\n        Fraction(3, 14)\n        >>> Fraction('314')\n        Fraction(314, 1)\n        >>> Fraction('-35/4')\n        Fraction(-35, 4)\n        >>> Fraction('3.1415') # conversion from numeric string\n        Fraction(6283, 2000)\n        >>> Fraction('-47e-2') # string may include a decimal exponent\n        Fraction(-47, 100)\n        >>> Fraction(1.47)  # direct construction from float (exact conversion)\n        Fraction(6620291452234629, 4503599627370496)\n        >>> Fraction(2.25)\n        Fraction(9, 4)\n        >>> Fraction(Decimal('1.47'))\n        Fraction(147, 100)\n\n        "
        self = super(Fraction, cls).__new__(cls)
        if denominator is None:
            if type(numerator) is int:
                self._numerator = numerator
                self._denominator = 1
                return self
            elif isinstance(numerator, numbers.Rational):
                self._numerator = numerator.numerator
                self._denominator = numerator.denominator
                return self
            elif isinstance(numerator, (float, Decimal)):
                (self._numerator, self._denominator) = numerator.as_integer_ratio()
                return self
            elif isinstance(numerator, str):
                m = _RATIONAL_FORMAT.match(numerator)
                if m is None:
                    raise ValueError(("Invalid literal for Fraction: %r" % numerator))
                numerator = int((m.group("num") or "0"))
                denom = m.group("denom")
                if denom:
                    denominator = int(denom)
                else:
                    denominator = 1
                    decimal = m.group("decimal")
                    if decimal:
                        scale = 10 ** len(decimal)
                        numerator = (numerator * scale) + int(decimal)
                        denominator *= scale
                    exp = m.group("exp")
                    if exp:
                        exp = int(exp)
                        if exp >= 0:
                            numerator *= 10 ** exp
                        else:
                            denominator *= 10 ** (-exp)
                if m.group("sign") == "-":
                    numerator = -numerator
            else:
                raise TypeError("argument should be a string or a Rational instance")
        elif type(numerator) is int is type(denominator):
            pass
        elif isinstance(numerator, numbers.Rational) and isinstance(
            denominator, numbers.Rational
        ):
            (numerator, denominator) = (
                (numerator.numerator * denominator.denominator),
                (denominator.numerator * numerator.denominator),
            )
        else:
            raise TypeError("both arguments should be Rational instances")
        if denominator == 0:
            raise ZeroDivisionError(("Fraction(%s, 0)" % numerator))
        if _normalize:
            g = math.gcd(numerator, denominator)
            if denominator < 0:
                g = -g
            numerator //= g
            denominator //= g
        self._numerator = numerator
        self._denominator = denominator
        return self

    @classmethod
    def from_float(cls, f):
        "Converts a finite float to a rational number, exactly.\n\n        Beware that Fraction.from_float(0.3) != Fraction(3, 10).\n\n        "
        if isinstance(f, numbers.Integral):
            return cls(f)
        elif not isinstance(f, float):
            raise TypeError(
                (
                    "%s.from_float() only takes floats, not %r (%s)"
                    % (cls.__name__, f, type(f).__name__)
                )
            )
        return cls(*f.as_integer_ratio())

    @classmethod
    def from_decimal(cls, dec):
        "Converts a finite Decimal instance to a rational number, exactly."
        from decimal import Decimal

        if isinstance(dec, numbers.Integral):
            dec = Decimal(int(dec))
        elif not isinstance(dec, Decimal):
            raise TypeError(
                (
                    "%s.from_decimal() only takes Decimals, not %r (%s)"
                    % (cls.__name__, dec, type(dec).__name__)
                )
            )
        return cls(*dec.as_integer_ratio())

    def as_integer_ratio(self):
        "Return the integer ratio as a tuple.\n\n        Return a tuple of two integers, whose ratio is equal to the\n        Fraction and with a positive denominator.\n        "
        return (self._numerator, self._denominator)

    def limit_denominator(self, max_denominator=1000000):
        "Closest Fraction to self with denominator at most max_denominator.\n\n        >>> Fraction('3.141592653589793').limit_denominator(10)\n        Fraction(22, 7)\n        >>> Fraction('3.141592653589793').limit_denominator(100)\n        Fraction(311, 99)\n        >>> Fraction(4321, 8765).limit_denominator(10000)\n        Fraction(4321, 8765)\n\n        "
        if max_denominator < 1:
            raise ValueError("max_denominator should be at least 1")
        if self._denominator <= max_denominator:
            return Fraction(self)
        (p0, q0, p1, q1) = (0, 1, 1, 0)
        (n, d) = (self._numerator, self._denominator)
        while True:
            a = n // d
            q2 = q0 + (a * q1)
            if q2 > max_denominator:
                break
            (p0, q0, p1, q1) = (p1, q1, (p0 + (a * p1)), q2)
            (n, d) = (d, (n - (a * d)))
        k = (max_denominator - q0) // q1
        bound1 = Fraction((p0 + (k * p1)), (q0 + (k * q1)))
        bound2 = Fraction(p1, q1)
        if abs((bound2 - self)) <= abs((bound1 - self)):
            return bound2
        else:
            return bound1

    @property
    def numerator(a):
        return a._numerator

    @property
    def denominator(a):
        return a._denominator

    def __repr__(self):
        "repr(self)"
        return "%s(%s, %s)" % (
            self.__class__.__name__,
            self._numerator,
            self._denominator,
        )

    def __str__(self):
        "str(self)"
        if self._denominator == 1:
            return str(self._numerator)
        else:
            return "%s/%s" % (self._numerator, self._denominator)

    def _operator_fallbacks(monomorphic_operator, fallback_operator):
        "Generates forward and reverse operators given a purely-rational\n        operator and a function from the operator module.\n\n        Use this like:\n        __op__, __rop__ = _operator_fallbacks(just_rational_op, operator.op)\n\n        In general, we want to implement the arithmetic operations so\n        that mixed-mode operations either call an implementation whose\n        author knew about the types of both arguments, or convert both\n        to the nearest built in type and do the operation there. In\n        Fraction, that means that we define __add__ and __radd__ as:\n\n            def __add__(self, other):\n                # Both types have numerators/denominator attributes,\n                # so do the operation directly\n                if isinstance(other, (int, Fraction)):\n                    return Fraction(self.numerator * other.denominator +\n                                    other.numerator * self.denominator,\n                                    self.denominator * other.denominator)\n                # float and complex don't have those operations, but we\n                # know about those types, so special case them.\n                elif isinstance(other, float):\n                    return float(self) + other\n                elif isinstance(other, complex):\n                    return complex(self) + other\n                # Let the other type take over.\n                return NotImplemented\n\n            def __radd__(self, other):\n                # radd handles more types than add because there's\n                # nothing left to fall back to.\n                if isinstance(other, numbers.Rational):\n                    return Fraction(self.numerator * other.denominator +\n                                    other.numerator * self.denominator,\n                                    self.denominator * other.denominator)\n                elif isinstance(other, Real):\n                    return float(other) + float(self)\n                elif isinstance(other, Complex):\n                    return complex(other) + complex(self)\n                return NotImplemented\n\n\n        There are 5 different cases for a mixed-type addition on\n        Fraction. I'll refer to all of the above code that doesn't\n        refer to Fraction, float, or complex as \"boilerplate\". 'r'\n        will be an instance of Fraction, which is a subtype of\n        Rational (r : Fraction <: Rational), and b : B <:\n        Complex. The first three involve 'r + b':\n\n            1. If B <: Fraction, int, float, or complex, we handle\n               that specially, and all is well.\n            2. If Fraction falls back to the boilerplate code, and it\n               were to return a value from __add__, we'd miss the\n               possibility that B defines a more intelligent __radd__,\n               so the boilerplate should return NotImplemented from\n               __add__. In particular, we don't handle Rational\n               here, even though we could get an exact answer, in case\n               the other type wants to do something special.\n            3. If B <: Fraction, Python tries B.__radd__ before\n               Fraction.__add__. This is ok, because it was\n               implemented with knowledge of Fraction, so it can\n               handle those instances before delegating to Real or\n               Complex.\n\n        The next two situations describe 'b + r'. We assume that b\n        didn't know about Fraction in its implementation, and that it\n        uses similar boilerplate code:\n\n            4. If B <: Rational, then __radd_ converts both to the\n               builtin rational type (hey look, that's us) and\n               proceeds.\n            5. Otherwise, __radd__ tries to find the nearest common\n               base ABC, and fall back to its builtin type. Since this\n               class doesn't subclass a concrete type, there's no\n               implementation to fall back to, so we need to try as\n               hard as possible to return an actual value, or the user\n               will get a TypeError.\n\n        "

        def forward(a, b):
            if isinstance(b, (int, Fraction)):
                return monomorphic_operator(a, b)
            elif isinstance(b, float):
                return fallback_operator(float(a), b)
            elif isinstance(b, complex):
                return fallback_operator(complex(a), b)
            else:
                return NotImplemented

        forward.__name__ = ("__" + fallback_operator.__name__) + "__"
        forward.__doc__ = monomorphic_operator.__doc__

        def reverse(b, a):
            if isinstance(a, numbers.Rational):
                return monomorphic_operator(a, b)
            elif isinstance(a, numbers.Real):
                return fallback_operator(float(a), float(b))
            elif isinstance(a, numbers.Complex):
                return fallback_operator(complex(a), complex(b))
            else:
                return NotImplemented

        reverse.__name__ = ("__r" + fallback_operator.__name__) + "__"
        reverse.__doc__ = monomorphic_operator.__doc__
        return (forward, reverse)

    def _add(a, b):
        "a + b"
        (na, da) = (a.numerator, a.denominator)
        (nb, db) = (b.numerator, b.denominator)
        g = math.gcd(da, db)
        if g == 1:
            return Fraction(((na * db) + (da * nb)), (da * db), _normalize=False)
        s = da // g
        t = (na * (db // g)) + (nb * s)
        g2 = math.gcd(t, g)
        if g2 == 1:
            return Fraction(t, (s * db), _normalize=False)
        return Fraction((t // g2), (s * (db // g2)), _normalize=False)

    (__add__, __radd__) = _operator_fallbacks(_add, operator.add)

    def _sub(a, b):
        "a - b"
        (na, da) = (a.numerator, a.denominator)
        (nb, db) = (b.numerator, b.denominator)
        g = math.gcd(da, db)
        if g == 1:
            return Fraction(((na * db) - (da * nb)), (da * db), _normalize=False)
        s = da // g
        t = (na * (db // g)) - (nb * s)
        g2 = math.gcd(t, g)
        if g2 == 1:
            return Fraction(t, (s * db), _normalize=False)
        return Fraction((t // g2), (s * (db // g2)), _normalize=False)

    (__sub__, __rsub__) = _operator_fallbacks(_sub, operator.sub)

    def _mul(a, b):
        "a * b"
        (na, da) = (a.numerator, a.denominator)
        (nb, db) = (b.numerator, b.denominator)
        g1 = math.gcd(na, db)
        if g1 > 1:
            na //= g1
            db //= g1
        g2 = math.gcd(nb, da)
        if g2 > 1:
            nb //= g2
            da //= g2
        return Fraction((na * nb), (db * da), _normalize=False)

    (__mul__, __rmul__) = _operator_fallbacks(_mul, operator.mul)

    def _div(a, b):
        "a / b"
        (na, da) = (a.numerator, a.denominator)
        (nb, db) = (b.numerator, b.denominator)
        g1 = math.gcd(na, nb)
        if g1 > 1:
            na //= g1
            nb //= g1
        g2 = math.gcd(db, da)
        if g2 > 1:
            da //= g2
            db //= g2
        (n, d) = ((na * db), (nb * da))
        if d < 0:
            (n, d) = ((-n), (-d))
        return Fraction(n, d, _normalize=False)

    (__truediv__, __rtruediv__) = _operator_fallbacks(_div, operator.truediv)

    def _floordiv(a, b):
        "a // b"
        return (a.numerator * b.denominator) // (a.denominator * b.numerator)

    (__floordiv__, __rfloordiv__) = _operator_fallbacks(_floordiv, operator.floordiv)

    def _divmod(a, b):
        "(a // b, a % b)"
        (da, db) = (a.denominator, b.denominator)
        (div, n_mod) = divmod((a.numerator * db), (da * b.numerator))
        return (div, Fraction(n_mod, (da * db)))

    (__divmod__, __rdivmod__) = _operator_fallbacks(_divmod, divmod)

    def _mod(a, b):
        "a % b"
        (da, db) = (a.denominator, b.denominator)
        return Fraction(((a.numerator * db) % (b.numerator * da)), (da * db))

    (__mod__, __rmod__) = _operator_fallbacks(_mod, operator.mod)

    def __pow__(a, b):
        "a ** b\n\n        If b is not an integer, the result will be a float or complex\n        since roots are generally irrational. If b is an integer, the\n        result will be rational.\n\n        "
        if isinstance(b, numbers.Rational):
            if b.denominator == 1:
                power = b.numerator
                if power >= 0:
                    return Fraction(
                        (a._numerator ** power),
                        (a._denominator ** power),
                        _normalize=False,
                    )
                elif a._numerator >= 0:
                    return Fraction(
                        (a._denominator ** (-power)),
                        (a._numerator ** (-power)),
                        _normalize=False,
                    )
                else:
                    return Fraction(
                        ((-a._denominator) ** (-power)),
                        ((-a._numerator) ** (-power)),
                        _normalize=False,
                    )
            else:
                return float(a) ** float(b)
        else:
            return float(a) ** b

    def __rpow__(b, a):
        "a ** b"
        if (b._denominator == 1) and (b._numerator >= 0):
            return a ** b._numerator
        if isinstance(a, numbers.Rational):
            return Fraction(a.numerator, a.denominator) ** b
        if b._denominator == 1:
            return a ** b._numerator
        return a ** float(b)

    def __pos__(a):
        "+a: Coerces a subclass instance to Fraction"
        return Fraction(a._numerator, a._denominator, _normalize=False)

    def __neg__(a):
        "-a"
        return Fraction((-a._numerator), a._denominator, _normalize=False)

    def __abs__(a):
        "abs(a)"
        return Fraction(abs(a._numerator), a._denominator, _normalize=False)

    def __trunc__(a):
        "trunc(a)"
        if a._numerator < 0:
            return -((-a._numerator) // a._denominator)
        else:
            return a._numerator // a._denominator

    def __floor__(a):
        "math.floor(a)"
        return a.numerator // a.denominator

    def __ceil__(a):
        "math.ceil(a)"
        return -((-a.numerator) // a.denominator)

    def __round__(self, ndigits=None):
        "round(self, ndigits)\n\n        Rounds half toward even.\n        "
        if ndigits is None:
            (floor, remainder) = divmod(self.numerator, self.denominator)
            if (remainder * 2) < self.denominator:
                return floor
            elif (remainder * 2) > self.denominator:
                return floor + 1
            elif (floor % 2) == 0:
                return floor
            else:
                return floor + 1
        shift = 10 ** abs(ndigits)
        if ndigits > 0:
            return Fraction(round((self * shift)), shift)
        else:
            return Fraction((round((self / shift)) * shift))

    def __hash__(self):
        "hash(self)"
        try:
            dinv = pow(self._denominator, (-1), _PyHASH_MODULUS)
        except ValueError:
            hash_ = _PyHASH_INF
        else:
            hash_ = hash((hash(abs(self._numerator)) * dinv))
        result = hash_ if (self._numerator >= 0) else (-hash_)
        return (-2) if (result == (-1)) else result

    def __eq__(a, b):
        "a == b"
        if type(b) is int:
            return (a._numerator == b) and (a._denominator == 1)
        if isinstance(b, numbers.Rational):
            return (a._numerator == b.numerator) and (a._denominator == b.denominator)
        if isinstance(b, numbers.Complex) and (b.imag == 0):
            b = b.real
        if isinstance(b, float):
            if math.isnan(b) or math.isinf(b):
                return 0.0 == b
            else:
                return a == a.from_float(b)
        else:
            return NotImplemented

    def _richcmp(self, other, op):
        "Helper for comparison operators, for internal use only.\n\n        Implement comparison between a Rational instance `self`, and\n        either another Rational instance or a float `other`.  If\n        `other` is not a Rational instance or a float, return\n        NotImplemented. `op` should be one of the six standard\n        comparison operators.\n\n        "
        if isinstance(other, numbers.Rational):
            return op(
                (self._numerator * other.denominator),
                (self._denominator * other.numerator),
            )
        if isinstance(other, float):
            if math.isnan(other) or math.isinf(other):
                return op(0.0, other)
            else:
                return op(self, self.from_float(other))
        else:
            return NotImplemented

    def __lt__(a, b):
        "a < b"
        return a._richcmp(b, operator.lt)

    def __gt__(a, b):
        "a > b"
        return a._richcmp(b, operator.gt)

    def __le__(a, b):
        "a <= b"
        return a._richcmp(b, operator.le)

    def __ge__(a, b):
        "a >= b"
        return a._richcmp(b, operator.ge)

    def __bool__(a):
        "a != 0"
        return bool(a._numerator)

    def __reduce__(self):
        return (self.__class__, (str(self),))

    def __copy__(self):
        if type(self) == Fraction:
            return self
        return self.__class__(self._numerator, self._denominator)

    def __deepcopy__(self, memo):
        if type(self) == Fraction:
            return self
        return self.__class__(self._numerator, self._denominator)
