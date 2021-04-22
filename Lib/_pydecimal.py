"\nThis is an implementation of decimal floating point arithmetic based on\nthe General Decimal Arithmetic Specification:\n\n    http://speleotrove.com/decimal/decarith.html\n\nand IEEE standard 854-1987:\n\n    http://en.wikipedia.org/wiki/IEEE_854-1987\n\nDecimal floating point has finite precision with arbitrarily large bounds.\n\nThe purpose of this module is to support arithmetic using familiar\n\"schoolhouse\" rules and to avoid some of the tricky representation\nissues associated with binary floating point.  The package is especially\nuseful for financial applications or for contexts where users have\nexpectations that are at odds with binary floating point (for instance,\nin binary floating point, 1.00 % 0.1 gives 0.09999999999999995 instead\nof 0.0; Decimal('1.00') % Decimal('0.1') returns the expected\nDecimal('0.00')).\n\nHere are some examples of using the decimal module:\n\n>>> from decimal import *\n>>> setcontext(ExtendedContext)\n>>> Decimal(0)\nDecimal('0')\n>>> Decimal('1')\nDecimal('1')\n>>> Decimal('-.0123')\nDecimal('-0.0123')\n>>> Decimal(123456)\nDecimal('123456')\n>>> Decimal('123.45e12345678')\nDecimal('1.2345E+12345680')\n>>> Decimal('1.33') + Decimal('1.27')\nDecimal('2.60')\n>>> Decimal('12.34') + Decimal('3.87') - Decimal('18.41')\nDecimal('-2.20')\n>>> dig = Decimal(1)\n>>> print(dig / Decimal(3))\n0.333333333\n>>> getcontext().prec = 18\n>>> print(dig / Decimal(3))\n0.333333333333333333\n>>> print(dig.sqrt())\n1\n>>> print(Decimal(3).sqrt())\n1.73205080756887729\n>>> print(Decimal(3) ** 123)\n4.85192780976896427E+58\n>>> inf = Decimal(1) / Decimal(0)\n>>> print(inf)\nInfinity\n>>> neginf = Decimal(-1) / Decimal(0)\n>>> print(neginf)\n-Infinity\n>>> print(neginf + inf)\nNaN\n>>> print(neginf * inf)\n-Infinity\n>>> print(dig / 0)\nInfinity\n>>> getcontext().traps[DivisionByZero] = 1\n>>> print(dig / 0)\nTraceback (most recent call last):\n  ...\n  ...\n  ...\ndecimal.DivisionByZero: x / 0\n>>> c = Context()\n>>> c.traps[InvalidOperation] = 0\n>>> print(c.flags[InvalidOperation])\n0\n>>> c.divide(Decimal(0), Decimal(0))\nDecimal('NaN')\n>>> c.traps[InvalidOperation] = 1\n>>> print(c.flags[InvalidOperation])\n1\n>>> c.flags[InvalidOperation] = 0\n>>> print(c.flags[InvalidOperation])\n0\n>>> print(c.divide(Decimal(0), Decimal(0)))\nTraceback (most recent call last):\n  ...\n  ...\n  ...\ndecimal.InvalidOperation: 0 / 0\n>>> print(c.flags[InvalidOperation])\n1\n>>> c.flags[InvalidOperation] = 0\n>>> c.traps[InvalidOperation] = 0\n>>> print(c.divide(Decimal(0), Decimal(0)))\nNaN\n>>> print(c.flags[InvalidOperation])\n1\n>>>\n"
__all__ = [
    "Decimal",
    "Context",
    "DecimalTuple",
    "DefaultContext",
    "BasicContext",
    "ExtendedContext",
    "DecimalException",
    "Clamped",
    "InvalidOperation",
    "DivisionByZero",
    "Inexact",
    "Rounded",
    "Subnormal",
    "Overflow",
    "Underflow",
    "FloatOperation",
    "DivisionImpossible",
    "InvalidContext",
    "ConversionSyntax",
    "DivisionUndefined",
    "ROUND_DOWN",
    "ROUND_HALF_UP",
    "ROUND_HALF_EVEN",
    "ROUND_CEILING",
    "ROUND_FLOOR",
    "ROUND_UP",
    "ROUND_HALF_DOWN",
    "ROUND_05UP",
    "setcontext",
    "getcontext",
    "localcontext",
    "MAX_PREC",
    "MAX_EMAX",
    "MIN_EMIN",
    "MIN_ETINY",
    "HAVE_THREADS",
    "HAVE_CONTEXTVAR",
]
__xname__ = __name__
__name__ = "decimal"
__version__ = "1.70"
__libmpdec_version__ = "2.4.2"
import math as _math
import numbers as _numbers
import sys

try:
    from collections import namedtuple as _namedtuple

    DecimalTuple = _namedtuple("DecimalTuple", "sign digits exponent")
except ImportError:
    DecimalTuple = lambda *args: args
ROUND_DOWN = "ROUND_DOWN"
ROUND_HALF_UP = "ROUND_HALF_UP"
ROUND_HALF_EVEN = "ROUND_HALF_EVEN"
ROUND_CEILING = "ROUND_CEILING"
ROUND_FLOOR = "ROUND_FLOOR"
ROUND_UP = "ROUND_UP"
ROUND_HALF_DOWN = "ROUND_HALF_DOWN"
ROUND_05UP = "ROUND_05UP"
HAVE_THREADS = True
HAVE_CONTEXTVAR = True
if sys.maxsize == ((2 ** 63) - 1):
    MAX_PREC = 999999999999999999
    MAX_EMAX = 999999999999999999
    MIN_EMIN = -999999999999999999
else:
    MAX_PREC = 425000000
    MAX_EMAX = 425000000
    MIN_EMIN = -425000000
MIN_ETINY = MIN_EMIN - (MAX_PREC - 1)


class DecimalException(ArithmeticError):
    "Base exception class.\n\n    Used exceptions derive from this.\n    If an exception derives from another exception besides this (such as\n    Underflow (Inexact, Rounded, Subnormal) that indicates that it is only\n    called if the others are present.  This isn't actually used for\n    anything, though.\n\n    handle  -- Called when context._raise_error is called and the\n               trap_enabler is not set.  First argument is self, second is the\n               context.  More arguments can be given, those being after\n               the explanation in _raise_error (For example,\n               context._raise_error(NewError, '(-x)!', self._sign) would\n               call NewError().handle(context, self._sign).)\n\n    To define a new exception, it should be sufficient to have it derive\n    from DecimalException.\n    "

    def handle(self, context, *args):
        pass


class Clamped(DecimalException):
    'Exponent of a 0 changed to fit bounds.\n\n    This occurs and signals clamped if the exponent of a result has been\n    altered in order to fit the constraints of a specific concrete\n    representation.  This may occur when the exponent of a zero result would\n    be outside the bounds of a representation, or when a large normal\n    number would have an encoded exponent that cannot be represented.  In\n    this latter case, the exponent is reduced to fit and the corresponding\n    number of zero digits are appended to the coefficient ("fold-down").\n    '


class InvalidOperation(DecimalException):
    "An invalid operation was performed.\n\n    Various bad things cause this:\n\n    Something creates a signaling NaN\n    -INF + INF\n    0 * (+-)INF\n    (+-)INF / (+-)INF\n    x % 0\n    (+-)INF % x\n    x._rescale( non-integer )\n    sqrt(-x) , x > 0\n    0 ** 0\n    x ** (non-integer)\n    x ** (+-)INF\n    An operand is invalid\n\n    The result of the operation after these is a quiet positive NaN,\n    except when the cause is a signaling NaN, in which case the result is\n    also a quiet NaN, but with the original sign, and an optional\n    diagnostic information.\n    "

    def handle(self, context, *args):
        if args:
            ans = _dec_from_triple(args[0]._sign, args[0]._int, "n", True)
            return ans._fix_nan(context)
        return _NaN


class ConversionSyntax(InvalidOperation):
    "Trying to convert badly formed string.\n\n    This occurs and signals invalid-operation if a string is being\n    converted to a number and it does not conform to the numeric string\n    syntax.  The result is [0,qNaN].\n    "

    def handle(self, context, *args):
        return _NaN


class DivisionByZero(DecimalException, ZeroDivisionError):
    "Division by 0.\n\n    This occurs and signals division-by-zero if division of a finite number\n    by zero was attempted (during a divide-integer or divide operation, or a\n    power operation with negative right-hand operand), and the dividend was\n    not zero.\n\n    The result of the operation is [sign,inf], where sign is the exclusive\n    or of the signs of the operands for divide, or is 1 for an odd power of\n    -0, for power.\n    "

    def handle(self, context, sign, *args):
        return _SignedInfinity[sign]


class DivisionImpossible(InvalidOperation):
    "Cannot perform the division adequately.\n\n    This occurs and signals invalid-operation if the integer result of a\n    divide-integer or remainder operation had too many digits (would be\n    longer than precision).  The result is [0,qNaN].\n    "

    def handle(self, context, *args):
        return _NaN


class DivisionUndefined(InvalidOperation, ZeroDivisionError):
    "Undefined result of division.\n\n    This occurs and signals invalid-operation if division by zero was\n    attempted (during a divide-integer, divide, or remainder operation), and\n    the dividend is also zero.  The result is [0,qNaN].\n    "

    def handle(self, context, *args):
        return _NaN


class Inexact(DecimalException):
    "Had to round, losing information.\n\n    This occurs and signals inexact whenever the result of an operation is\n    not exact (that is, it needed to be rounded and any discarded digits\n    were non-zero), or if an overflow or underflow condition occurs.  The\n    result in all cases is unchanged.\n\n    The inexact signal may be tested (or trapped) to determine if a given\n    operation (or sequence of operations) was inexact.\n    "


class InvalidContext(InvalidOperation):
    "Invalid context.  Unknown rounding, for example.\n\n    This occurs and signals invalid-operation if an invalid context was\n    detected during an operation.  This can occur if contexts are not checked\n    on creation and either the precision exceeds the capability of the\n    underlying concrete representation or an unknown or unsupported rounding\n    was specified.  These aspects of the context need only be checked when\n    the values are required to be used.  The result is [0,qNaN].\n    "

    def handle(self, context, *args):
        return _NaN


class Rounded(DecimalException):
    "Number got rounded (not  necessarily changed during rounding).\n\n    This occurs and signals rounded whenever the result of an operation is\n    rounded (that is, some zero or non-zero digits were discarded from the\n    coefficient), or if an overflow or underflow condition occurs.  The\n    result in all cases is unchanged.\n\n    The rounded signal may be tested (or trapped) to determine if a given\n    operation (or sequence of operations) caused a loss of precision.\n    "


class Subnormal(DecimalException):
    "Exponent < Emin before rounding.\n\n    This occurs and signals subnormal whenever the result of a conversion or\n    operation is subnormal (that is, its adjusted exponent is less than\n    Emin, before any rounding).  The result in all cases is unchanged.\n\n    The subnormal signal may be tested (or trapped) to determine if a given\n    or operation (or sequence of operations) yielded a subnormal result.\n    "


class Overflow(Inexact, Rounded):
    "Numerical overflow.\n\n    This occurs and signals overflow if the adjusted exponent of a result\n    (from a conversion or from an operation that is not an attempt to divide\n    by zero), after rounding, would be greater than the largest value that\n    can be handled by the implementation (the value Emax).\n\n    The result depends on the rounding mode:\n\n    For round-half-up and round-half-even (and for round-half-down and\n    round-up, if implemented), the result of the operation is [sign,inf],\n    where sign is the sign of the intermediate result.  For round-down, the\n    result is the largest finite number that can be represented in the\n    current precision, with the sign of the intermediate result.  For\n    round-ceiling, the result is the same as for round-down if the sign of\n    the intermediate result is 1, or is [0,inf] otherwise.  For round-floor,\n    the result is the same as for round-down if the sign of the intermediate\n    result is 0, or is [1,inf] otherwise.  In all cases, Inexact and Rounded\n    will also be raised.\n    "

    def handle(self, context, sign, *args):
        if context.rounding in (
            ROUND_HALF_UP,
            ROUND_HALF_EVEN,
            ROUND_HALF_DOWN,
            ROUND_UP,
        ):
            return _SignedInfinity[sign]
        if sign == 0:
            if context.rounding == ROUND_CEILING:
                return _SignedInfinity[sign]
            return _dec_from_triple(
                sign, ("9" * context.prec), ((context.Emax - context.prec) + 1)
            )
        if sign == 1:
            if context.rounding == ROUND_FLOOR:
                return _SignedInfinity[sign]
            return _dec_from_triple(
                sign, ("9" * context.prec), ((context.Emax - context.prec) + 1)
            )


class Underflow(Inexact, Rounded, Subnormal):
    "Numerical underflow with result rounded to 0.\n\n    This occurs and signals underflow if a result is inexact and the\n    adjusted exponent of the result would be smaller (more negative) than\n    the smallest value that can be handled by the implementation (the value\n    Emin).  That is, the result is both inexact and subnormal.\n\n    The result after an underflow will be a subnormal number rounded, if\n    necessary, so that its exponent is not less than Etiny.  This may result\n    in 0 with the sign of the intermediate result and an exponent of Etiny.\n\n    In all cases, Inexact, Rounded, and Subnormal will also be raised.\n    "


class FloatOperation(DecimalException, TypeError):
    "Enable stricter semantics for mixing floats and Decimals.\n\n    If the signal is not trapped (default), mixing floats and Decimals is\n    permitted in the Decimal() constructor, context.create_decimal() and\n    all comparison operators. Both conversion and comparisons are exact.\n    Any occurrence of a mixed operation is silently recorded by setting\n    FloatOperation in the context flags.  Explicit conversions with\n    Decimal.from_float() or context.create_decimal_from_float() do not\n    set the flag.\n\n    Otherwise (the signal is trapped), only equality comparisons and explicit\n    conversions are silent. All other mixed operations raise FloatOperation.\n    "


_signals = [
    Clamped,
    DivisionByZero,
    Inexact,
    Overflow,
    Rounded,
    Underflow,
    InvalidOperation,
    Subnormal,
    FloatOperation,
]
_condition_map = {
    ConversionSyntax: InvalidOperation,
    DivisionImpossible: InvalidOperation,
    DivisionUndefined: InvalidOperation,
    InvalidContext: InvalidOperation,
}
_rounding_modes = (
    ROUND_DOWN,
    ROUND_HALF_UP,
    ROUND_HALF_EVEN,
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_UP,
    ROUND_HALF_DOWN,
    ROUND_05UP,
)
import contextvars

_current_context_var = contextvars.ContextVar("decimal_context")


def getcontext():
    "Returns this thread's context.\n\n    If this thread does not yet have a context, returns\n    a new context and sets this thread's context.\n    New contexts are copies of DefaultContext.\n    "
    try:
        return _current_context_var.get()
    except LookupError:
        context = Context()
        _current_context_var.set(context)
        return context


def setcontext(context):
    "Set this thread's context to context."
    if context in (DefaultContext, BasicContext, ExtendedContext):
        context = context.copy()
        context.clear_flags()
    _current_context_var.set(context)


del contextvars


def localcontext(ctx=None):
    "Return a context manager for a copy of the supplied context\n\n    Uses a copy of the current context if no context is specified\n    The returned context manager creates a local decimal context\n    in a with statement:\n        def sin(x):\n             with localcontext() as ctx:\n                 ctx.prec += 2\n                 # Rest of sin calculation algorithm\n                 # uses a precision 2 greater than normal\n             return +s  # Convert result to normal precision\n\n         def sin(x):\n             with localcontext(ExtendedContext):\n                 # Rest of sin calculation algorithm\n                 # uses the Extended Context from the\n                 # General Decimal Arithmetic Specification\n             return +s  # Convert result to normal context\n\n    >>> setcontext(DefaultContext)\n    >>> print(getcontext().prec)\n    28\n    >>> with localcontext():\n    ...     ctx = getcontext()\n    ...     ctx.prec += 2\n    ...     print(ctx.prec)\n    ...\n    30\n    >>> with localcontext(ExtendedContext):\n    ...     print(getcontext().prec)\n    ...\n    9\n    >>> print(getcontext().prec)\n    28\n    "
    if ctx is None:
        ctx = getcontext()
    return _ContextManager(ctx)


class Decimal(object):
    "Floating point class for decimal arithmetic."
    __slots__ = ("_exp", "_int", "_sign", "_is_special")

    def __new__(cls, value="0", context=None):
        "Create a decimal point instance.\n\n        >>> Decimal('3.14')              # string input\n        Decimal('3.14')\n        >>> Decimal((0, (3, 1, 4), -2))  # tuple (sign, digit_tuple, exponent)\n        Decimal('3.14')\n        >>> Decimal(314)                 # int\n        Decimal('314')\n        >>> Decimal(Decimal(314))        # another decimal instance\n        Decimal('314')\n        >>> Decimal('  3.14  \\n')        # leading and trailing whitespace okay\n        Decimal('3.14')\n        "
        self = object.__new__(cls)
        if isinstance(value, str):
            m = _parser(value.strip().replace("_", ""))
            if m is None:
                if context is None:
                    context = getcontext()
                return context._raise_error(
                    ConversionSyntax, ("Invalid literal for Decimal: %r" % value)
                )
            if m.group("sign") == "-":
                self._sign = 1
            else:
                self._sign = 0
            intpart = m.group("int")
            if intpart is not None:
                fracpart = m.group("frac") or ""
                exp = int((m.group("exp") or "0"))
                self._int = str(int((intpart + fracpart)))
                self._exp = exp - len(fracpart)
                self._is_special = False
            else:
                diag = m.group("diag")
                if diag is not None:
                    self._int = str(int((diag or "0"))).lstrip("0")
                    if m.group("signal"):
                        self._exp = "N"
                    else:
                        self._exp = "n"
                else:
                    self._int = "0"
                    self._exp = "F"
                self._is_special = True
            return self
        if isinstance(value, int):
            if value >= 0:
                self._sign = 0
            else:
                self._sign = 1
            self._exp = 0
            self._int = str(abs(value))
            self._is_special = False
            return self
        if isinstance(value, Decimal):
            self._exp = value._exp
            self._sign = value._sign
            self._int = value._int
            self._is_special = value._is_special
            return self
        if isinstance(value, _WorkRep):
            self._sign = value.sign
            self._int = str(value.int)
            self._exp = int(value.exp)
            self._is_special = False
            return self
        if isinstance(value, (list, tuple)):
            if len(value) != 3:
                raise ValueError(
                    "Invalid tuple size in creation of Decimal from list or tuple.  The list or tuple should have exactly three elements."
                )
            if not (isinstance(value[0], int) and (value[0] in (0, 1))):
                raise ValueError(
                    "Invalid sign.  The first value in the tuple should be an integer; either 0 for a positive number or 1 for a negative number."
                )
            self._sign = value[0]
            if value[2] == "F":
                self._int = "0"
                self._exp = value[2]
                self._is_special = True
            else:
                digits = []
                for digit in value[1]:
                    if isinstance(digit, int) and (0 <= digit <= 9):
                        if digits or (digit != 0):
                            digits.append(digit)
                    else:
                        raise ValueError(
                            "The second value in the tuple must be composed of integers in the range 0 through 9."
                        )
                if value[2] in ("n", "N"):
                    self._int = "".join(map(str, digits))
                    self._exp = value[2]
                    self._is_special = True
                elif isinstance(value[2], int):
                    self._int = "".join(map(str, (digits or [0])))
                    self._exp = value[2]
                    self._is_special = False
                else:
                    raise ValueError(
                        "The third value in the tuple must be an integer, or one of the strings 'F', 'n', 'N'."
                    )
            return self
        if isinstance(value, float):
            if context is None:
                context = getcontext()
            context._raise_error(
                FloatOperation,
                "strict semantics for mixing floats and Decimals are enabled",
            )
            value = Decimal.from_float(value)
            self._exp = value._exp
            self._sign = value._sign
            self._int = value._int
            self._is_special = value._is_special
            return self
        raise TypeError(("Cannot convert %r to Decimal" % value))

    @classmethod
    def from_float(cls, f):
        "Converts a float to a decimal number, exactly.\n\n        Note that Decimal.from_float(0.1) is not the same as Decimal('0.1').\n        Since 0.1 is not exactly representable in binary floating point, the\n        value is stored as the nearest representable value which is\n        0x1.999999999999ap-4.  The exact equivalent of the value in decimal\n        is 0.1000000000000000055511151231257827021181583404541015625.\n\n        >>> Decimal.from_float(0.1)\n        Decimal('0.1000000000000000055511151231257827021181583404541015625')\n        >>> Decimal.from_float(float('nan'))\n        Decimal('NaN')\n        >>> Decimal.from_float(float('inf'))\n        Decimal('Infinity')\n        >>> Decimal.from_float(-float('inf'))\n        Decimal('-Infinity')\n        >>> Decimal.from_float(-0.0)\n        Decimal('-0')\n\n        "
        if isinstance(f, int):
            sign = 0 if (f >= 0) else 1
            k = 0
            coeff = str(abs(f))
        elif isinstance(f, float):
            if _math.isinf(f) or _math.isnan(f):
                return cls(repr(f))
            if _math.copysign(1.0, f) == 1.0:
                sign = 0
            else:
                sign = 1
            (n, d) = abs(f).as_integer_ratio()
            k = d.bit_length() - 1
            coeff = str((n * (5 ** k)))
        else:
            raise TypeError("argument must be int or float.")
        result = _dec_from_triple(sign, coeff, (-k))
        if cls is Decimal:
            return result
        else:
            return cls(result)

    def _isnan(self):
        "Returns whether the number is not actually one.\n\n        0 if a number\n        1 if NaN\n        2 if sNaN\n        "
        if self._is_special:
            exp = self._exp
            if exp == "n":
                return 1
            elif exp == "N":
                return 2
        return 0

    def _isinfinity(self):
        "Returns whether the number is infinite\n\n        0 if finite or not a number\n        1 if +INF\n        -1 if -INF\n        "
        if self._exp == "F":
            if self._sign:
                return -1
            return 1
        return 0

    def _check_nans(self, other=None, context=None):
        "Returns whether the number is not actually one.\n\n        if self, other are sNaN, signal\n        if self, other are NaN return nan\n        return 0\n\n        Done before operations.\n        "
        self_is_nan = self._isnan()
        if other is None:
            other_is_nan = False
        else:
            other_is_nan = other._isnan()
        if self_is_nan or other_is_nan:
            if context is None:
                context = getcontext()
            if self_is_nan == 2:
                return context._raise_error(InvalidOperation, "sNaN", self)
            if other_is_nan == 2:
                return context._raise_error(InvalidOperation, "sNaN", other)
            if self_is_nan:
                return self._fix_nan(context)
            return other._fix_nan(context)
        return 0

    def _compare_check_nans(self, other, context):
        "Version of _check_nans used for the signaling comparisons\n        compare_signal, __le__, __lt__, __ge__, __gt__.\n\n        Signal InvalidOperation if either self or other is a (quiet\n        or signaling) NaN.  Signaling NaNs take precedence over quiet\n        NaNs.\n\n        Return 0 if neither operand is a NaN.\n\n        "
        if context is None:
            context = getcontext()
        if self._is_special or other._is_special:
            if self.is_snan():
                return context._raise_error(
                    InvalidOperation, "comparison involving sNaN", self
                )
            elif other.is_snan():
                return context._raise_error(
                    InvalidOperation, "comparison involving sNaN", other
                )
            elif self.is_qnan():
                return context._raise_error(
                    InvalidOperation, "comparison involving NaN", self
                )
            elif other.is_qnan():
                return context._raise_error(
                    InvalidOperation, "comparison involving NaN", other
                )
        return 0

    def __bool__(self):
        "Return True if self is nonzero; otherwise return False.\n\n        NaNs and infinities are considered nonzero.\n        "
        return self._is_special or (self._int != "0")

    def _cmp(self, other):
        "Compare the two non-NaN decimal instances self and other.\n\n        Returns -1 if self < other, 0 if self == other and 1\n        if self > other.  This routine is for internal use only."
        if self._is_special or other._is_special:
            self_inf = self._isinfinity()
            other_inf = other._isinfinity()
            if self_inf == other_inf:
                return 0
            elif self_inf < other_inf:
                return -1
            else:
                return 1
        if not self:
            if not other:
                return 0
            else:
                return -((-1) ** other._sign)
        if not other:
            return (-1) ** self._sign
        if other._sign < self._sign:
            return -1
        if self._sign < other._sign:
            return 1
        self_adjusted = self.adjusted()
        other_adjusted = other.adjusted()
        if self_adjusted == other_adjusted:
            self_padded = self._int + ("0" * (self._exp - other._exp))
            other_padded = other._int + ("0" * (other._exp - self._exp))
            if self_padded == other_padded:
                return 0
            elif self_padded < other_padded:
                return -((-1) ** self._sign)
            else:
                return (-1) ** self._sign
        elif self_adjusted > other_adjusted:
            return (-1) ** self._sign
        else:
            return -((-1) ** self._sign)

    def __eq__(self, other, context=None):
        (self, other) = _convert_for_comparison(self, other, equality_op=True)
        if other is NotImplemented:
            return other
        if self._check_nans(other, context):
            return False
        return self._cmp(other) == 0

    def __lt__(self, other, context=None):
        (self, other) = _convert_for_comparison(self, other)
        if other is NotImplemented:
            return other
        ans = self._compare_check_nans(other, context)
        if ans:
            return False
        return self._cmp(other) < 0

    def __le__(self, other, context=None):
        (self, other) = _convert_for_comparison(self, other)
        if other is NotImplemented:
            return other
        ans = self._compare_check_nans(other, context)
        if ans:
            return False
        return self._cmp(other) <= 0

    def __gt__(self, other, context=None):
        (self, other) = _convert_for_comparison(self, other)
        if other is NotImplemented:
            return other
        ans = self._compare_check_nans(other, context)
        if ans:
            return False
        return self._cmp(other) > 0

    def __ge__(self, other, context=None):
        (self, other) = _convert_for_comparison(self, other)
        if other is NotImplemented:
            return other
        ans = self._compare_check_nans(other, context)
        if ans:
            return False
        return self._cmp(other) >= 0

    def compare(self, other, context=None):
        "Compare self to other.  Return a decimal value:\n\n        a or b is a NaN ==> Decimal('NaN')\n        a < b           ==> Decimal('-1')\n        a == b          ==> Decimal('0')\n        a > b           ==> Decimal('1')\n        "
        other = _convert_other(other, raiseit=True)
        if self._is_special or (other and other._is_special):
            ans = self._check_nans(other, context)
            if ans:
                return ans
        return Decimal(self._cmp(other))

    def __hash__(self):
        "x.__hash__() <==> hash(x)"
        if self._is_special:
            if self.is_snan():
                raise TypeError("Cannot hash a signaling NaN value.")
            elif self.is_nan():
                return _PyHASH_NAN
            elif self._sign:
                return -_PyHASH_INF
            else:
                return _PyHASH_INF
        if self._exp >= 0:
            exp_hash = pow(10, self._exp, _PyHASH_MODULUS)
        else:
            exp_hash = pow(_PyHASH_10INV, (-self._exp), _PyHASH_MODULUS)
        hash_ = (int(self._int) * exp_hash) % _PyHASH_MODULUS
        ans = hash_ if (self >= 0) else (-hash_)
        return (-2) if (ans == (-1)) else ans

    def as_tuple(self):
        "Represents the number as a triple tuple.\n\n        To show the internals exactly as they are.\n        "
        return DecimalTuple(self._sign, tuple(map(int, self._int)), self._exp)

    def as_integer_ratio(self):
        "Express a finite Decimal instance in the form n / d.\n\n        Returns a pair (n, d) of integers.  When called on an infinity\n        or NaN, raises OverflowError or ValueError respectively.\n\n        >>> Decimal('3.14').as_integer_ratio()\n        (157, 50)\n        >>> Decimal('-123e5').as_integer_ratio()\n        (-12300000, 1)\n        >>> Decimal('0.00').as_integer_ratio()\n        (0, 1)\n\n        "
        if self._is_special:
            if self.is_nan():
                raise ValueError("cannot convert NaN to integer ratio")
            else:
                raise OverflowError("cannot convert Infinity to integer ratio")
        if not self:
            return (0, 1)
        n = int(self._int)
        if self._exp >= 0:
            (n, d) = ((n * (10 ** self._exp)), 1)
        else:
            d5 = -self._exp
            while (d5 > 0) and ((n % 5) == 0):
                n //= 5
                d5 -= 1
            d2 = -self._exp
            shift2 = min(((n & (-n)).bit_length() - 1), d2)
            if shift2:
                n >>= shift2
                d2 -= shift2
            d = (5 ** d5) << d2
        if self._sign:
            n = -n
        return (n, d)

    def __repr__(self):
        "Represents the number as an instance of Decimal."
        return "Decimal('%s')" % str(self)

    def __str__(self, eng=False, context=None):
        "Return string representation of the number in scientific notation.\n\n        Captures all of the information in the underlying representation.\n        "
        sign = ["", "-"][self._sign]
        if self._is_special:
            if self._exp == "F":
                return sign + "Infinity"
            elif self._exp == "n":
                return (sign + "NaN") + self._int
            else:
                return (sign + "sNaN") + self._int
        leftdigits = self._exp + len(self._int)
        if (self._exp <= 0) and (leftdigits > (-6)):
            dotplace = leftdigits
        elif not eng:
            dotplace = 1
        elif self._int == "0":
            dotplace = ((leftdigits + 1) % 3) - 1
        else:
            dotplace = ((leftdigits - 1) % 3) + 1
        if dotplace <= 0:
            intpart = "0"
            fracpart = ("." + ("0" * (-dotplace))) + self._int
        elif dotplace >= len(self._int):
            intpart = self._int + ("0" * (dotplace - len(self._int)))
            fracpart = ""
        else:
            intpart = self._int[:dotplace]
            fracpart = "." + self._int[dotplace:]
        if leftdigits == dotplace:
            exp = ""
        else:
            if context is None:
                context = getcontext()
            exp = ["e", "E"][context.capitals] + ("%+d" % (leftdigits - dotplace))
        return ((sign + intpart) + fracpart) + exp

    def to_eng_string(self, context=None):
        "Convert to a string, using engineering notation if an exponent is needed.\n\n        Engineering notation has an exponent which is a multiple of 3.  This\n        can leave up to 3 digits to the left of the decimal place and may\n        require the addition of either one or two trailing zeros.\n        "
        return self.__str__(eng=True, context=context)

    def __neg__(self, context=None):
        "Returns a copy with the sign switched.\n\n        Rounds, if it has reason.\n        "
        if self._is_special:
            ans = self._check_nans(context=context)
            if ans:
                return ans
        if context is None:
            context = getcontext()
        if (not self) and (context.rounding != ROUND_FLOOR):
            ans = self.copy_abs()
        else:
            ans = self.copy_negate()
        return ans._fix(context)

    def __pos__(self, context=None):
        "Returns a copy, unless it is a sNaN.\n\n        Rounds the number (if more than precision digits)\n        "
        if self._is_special:
            ans = self._check_nans(context=context)
            if ans:
                return ans
        if context is None:
            context = getcontext()
        if (not self) and (context.rounding != ROUND_FLOOR):
            ans = self.copy_abs()
        else:
            ans = Decimal(self)
        return ans._fix(context)

    def __abs__(self, round=True, context=None):
        "Returns the absolute value of self.\n\n        If the keyword argument 'round' is false, do not round.  The\n        expression self.__abs__(round=False) is equivalent to\n        self.copy_abs().\n        "
        if not round:
            return self.copy_abs()
        if self._is_special:
            ans = self._check_nans(context=context)
            if ans:
                return ans
        if self._sign:
            ans = self.__neg__(context=context)
        else:
            ans = self.__pos__(context=context)
        return ans

    def __add__(self, other, context=None):
        "Returns self + other.\n\n        -INF + INF (or the reverse) cause InvalidOperation errors.\n        "
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        if context is None:
            context = getcontext()
        if self._is_special or other._is_special:
            ans = self._check_nans(other, context)
            if ans:
                return ans
            if self._isinfinity():
                if (self._sign != other._sign) and other._isinfinity():
                    return context._raise_error(InvalidOperation, "-INF + INF")
                return Decimal(self)
            if other._isinfinity():
                return Decimal(other)
        exp = min(self._exp, other._exp)
        negativezero = 0
        if (context.rounding == ROUND_FLOOR) and (self._sign != other._sign):
            negativezero = 1
        if (not self) and (not other):
            sign = min(self._sign, other._sign)
            if negativezero:
                sign = 1
            ans = _dec_from_triple(sign, "0", exp)
            ans = ans._fix(context)
            return ans
        if not self:
            exp = max(exp, ((other._exp - context.prec) - 1))
            ans = other._rescale(exp, context.rounding)
            ans = ans._fix(context)
            return ans
        if not other:
            exp = max(exp, ((self._exp - context.prec) - 1))
            ans = self._rescale(exp, context.rounding)
            ans = ans._fix(context)
            return ans
        op1 = _WorkRep(self)
        op2 = _WorkRep(other)
        (op1, op2) = _normalize(op1, op2, context.prec)
        result = _WorkRep()
        if op1.sign != op2.sign:
            if op1.int == op2.int:
                ans = _dec_from_triple(negativezero, "0", exp)
                ans = ans._fix(context)
                return ans
            if op1.int < op2.int:
                (op1, op2) = (op2, op1)
            if op1.sign == 1:
                result.sign = 1
                (op1.sign, op2.sign) = (op2.sign, op1.sign)
            else:
                result.sign = 0
        elif op1.sign == 1:
            result.sign = 1
            (op1.sign, op2.sign) = (0, 0)
        else:
            result.sign = 0
        if op2.sign == 0:
            result.int = op1.int + op2.int
        else:
            result.int = op1.int - op2.int
        result.exp = op1.exp
        ans = Decimal(result)
        ans = ans._fix(context)
        return ans

    __radd__ = __add__

    def __sub__(self, other, context=None):
        "Return self - other"
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        if self._is_special or other._is_special:
            ans = self._check_nans(other, context=context)
            if ans:
                return ans
        return self.__add__(other.copy_negate(), context=context)

    def __rsub__(self, other, context=None):
        "Return other - self"
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        return other.__sub__(self, context=context)

    def __mul__(self, other, context=None):
        "Return self * other.\n\n        (+-) INF * 0 (or its reverse) raise InvalidOperation.\n        "
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        if context is None:
            context = getcontext()
        resultsign = self._sign ^ other._sign
        if self._is_special or other._is_special:
            ans = self._check_nans(other, context)
            if ans:
                return ans
            if self._isinfinity():
                if not other:
                    return context._raise_error(InvalidOperation, "(+-)INF * 0")
                return _SignedInfinity[resultsign]
            if other._isinfinity():
                if not self:
                    return context._raise_error(InvalidOperation, "0 * (+-)INF")
                return _SignedInfinity[resultsign]
        resultexp = self._exp + other._exp
        if (not self) or (not other):
            ans = _dec_from_triple(resultsign, "0", resultexp)
            ans = ans._fix(context)
            return ans
        if self._int == "1":
            ans = _dec_from_triple(resultsign, other._int, resultexp)
            ans = ans._fix(context)
            return ans
        if other._int == "1":
            ans = _dec_from_triple(resultsign, self._int, resultexp)
            ans = ans._fix(context)
            return ans
        op1 = _WorkRep(self)
        op2 = _WorkRep(other)
        ans = _dec_from_triple(resultsign, str((op1.int * op2.int)), resultexp)
        ans = ans._fix(context)
        return ans

    __rmul__ = __mul__

    def __truediv__(self, other, context=None):
        "Return self / other."
        other = _convert_other(other)
        if other is NotImplemented:
            return NotImplemented
        if context is None:
            context = getcontext()
        sign = self._sign ^ other._sign
        if self._is_special or other._is_special:
            ans = self._check_nans(other, context)
            if ans:
                return ans
            if self._isinfinity() and other._isinfinity():
                return context._raise_error(InvalidOperation, "(+-)INF/(+-)INF")
            if self._isinfinity():
                return _SignedInfinity[sign]
            if other._isinfinity():
                context._raise_error(Clamped, "Division by infinity")
                return _dec_from_triple(sign, "0", context.Etiny())
        if not other:
            if not self:
                return context._raise_error(DivisionUndefined, "0 / 0")
            return context._raise_error(DivisionByZero, "x / 0", sign)
        if not self:
            exp = self._exp - other._exp
            coeff = 0
        else:
            shift = ((len(other._int) - len(self._int)) + context.prec) + 1
            exp = (self._exp - other._exp) - shift
            op1 = _WorkRep(self)
            op2 = _WorkRep(other)
            if shift >= 0:
                (coeff, remainder) = divmod((op1.int * (10 ** shift)), op2.int)
            else:
                (coeff, remainder) = divmod(op1.int, (op2.int * (10 ** (-shift))))
            if remainder:
                if (coeff % 5) == 0:
                    coeff += 1
            else:
                ideal_exp = self._exp - other._exp
                while (exp < ideal_exp) and ((coeff % 10) == 0):
                    coeff //= 10
                    exp += 1
        ans = _dec_from_triple(sign, str(coeff), exp)
        return ans._fix(context)

    def _divide(self, other, context):
        "Return (self // other, self % other), to context.prec precision.\n\n        Assumes that neither self nor other is a NaN, that self is not\n        infinite and that other is nonzero.\n        "
        sign = self._sign ^ other._sign
        if other._isinfinity():
            ideal_exp = self._exp
        else:
            ideal_exp = min(self._exp, other._exp)
        expdiff = self.adjusted() - other.adjusted()
        if (not self) or other._isinfinity() or (expdiff <= (-2)):
            return (
                _dec_from_triple(sign, "0", 0),
                self._rescale(ideal_exp, context.rounding),
            )
        if expdiff <= context.prec:
            op1 = _WorkRep(self)
            op2 = _WorkRep(other)
            if op1.exp >= op2.exp:
                op1.int *= 10 ** (op1.exp - op2.exp)
            else:
                op2.int *= 10 ** (op2.exp - op1.exp)
            (q, r) = divmod(op1.int, op2.int)
            if q < (10 ** context.prec):
                return (
                    _dec_from_triple(sign, str(q), 0),
                    _dec_from_triple(self._sign, str(r), ideal_exp),
                )
        ans = context._raise_error(
            DivisionImpossible, "quotient too large in //, % or divmod"
        )
        return (ans, ans)

    def __rtruediv__(self, other, context=None):
        "Swaps self/other and returns __truediv__."
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        return other.__truediv__(self, context=context)

    def __divmod__(self, other, context=None):
        "\n        Return (self // other, self % other)\n        "
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        if context is None:
            context = getcontext()
        ans = self._check_nans(other, context)
        if ans:
            return (ans, ans)
        sign = self._sign ^ other._sign
        if self._isinfinity():
            if other._isinfinity():
                ans = context._raise_error(InvalidOperation, "divmod(INF, INF)")
                return (ans, ans)
            else:
                return (
                    _SignedInfinity[sign],
                    context._raise_error(InvalidOperation, "INF % x"),
                )
        if not other:
            if not self:
                ans = context._raise_error(DivisionUndefined, "divmod(0, 0)")
                return (ans, ans)
            else:
                return (
                    context._raise_error(DivisionByZero, "x // 0", sign),
                    context._raise_error(InvalidOperation, "x % 0"),
                )
        (quotient, remainder) = self._divide(other, context)
        remainder = remainder._fix(context)
        return (quotient, remainder)

    def __rdivmod__(self, other, context=None):
        "Swaps self/other and returns __divmod__."
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        return other.__divmod__(self, context=context)

    def __mod__(self, other, context=None):
        "\n        self % other\n        "
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        if context is None:
            context = getcontext()
        ans = self._check_nans(other, context)
        if ans:
            return ans
        if self._isinfinity():
            return context._raise_error(InvalidOperation, "INF % x")
        elif not other:
            if self:
                return context._raise_error(InvalidOperation, "x % 0")
            else:
                return context._raise_error(DivisionUndefined, "0 % 0")
        remainder = self._divide(other, context)[1]
        remainder = remainder._fix(context)
        return remainder

    def __rmod__(self, other, context=None):
        "Swaps self/other and returns __mod__."
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        return other.__mod__(self, context=context)

    def remainder_near(self, other, context=None):
        "\n        Remainder nearest to 0-  abs(remainder-near) <= other/2\n        "
        if context is None:
            context = getcontext()
        other = _convert_other(other, raiseit=True)
        ans = self._check_nans(other, context)
        if ans:
            return ans
        if self._isinfinity():
            return context._raise_error(InvalidOperation, "remainder_near(infinity, x)")
        if not other:
            if self:
                return context._raise_error(InvalidOperation, "remainder_near(x, 0)")
            else:
                return context._raise_error(DivisionUndefined, "remainder_near(0, 0)")
        if other._isinfinity():
            ans = Decimal(self)
            return ans._fix(context)
        ideal_exponent = min(self._exp, other._exp)
        if not self:
            ans = _dec_from_triple(self._sign, "0", ideal_exponent)
            return ans._fix(context)
        expdiff = self.adjusted() - other.adjusted()
        if expdiff >= (context.prec + 1):
            return context._raise_error(DivisionImpossible)
        if expdiff <= (-2):
            ans = self._rescale(ideal_exponent, context.rounding)
            return ans._fix(context)
        op1 = _WorkRep(self)
        op2 = _WorkRep(other)
        if op1.exp >= op2.exp:
            op1.int *= 10 ** (op1.exp - op2.exp)
        else:
            op2.int *= 10 ** (op2.exp - op1.exp)
        (q, r) = divmod(op1.int, op2.int)
        if ((2 * r) + (q & 1)) > op2.int:
            r -= op2.int
            q += 1
        if q >= (10 ** context.prec):
            return context._raise_error(DivisionImpossible)
        sign = self._sign
        if r < 0:
            sign = 1 - sign
            r = -r
        ans = _dec_from_triple(sign, str(r), ideal_exponent)
        return ans._fix(context)

    def __floordiv__(self, other, context=None):
        "self // other"
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        if context is None:
            context = getcontext()
        ans = self._check_nans(other, context)
        if ans:
            return ans
        if self._isinfinity():
            if other._isinfinity():
                return context._raise_error(InvalidOperation, "INF // INF")
            else:
                return _SignedInfinity[(self._sign ^ other._sign)]
        if not other:
            if self:
                return context._raise_error(
                    DivisionByZero, "x // 0", (self._sign ^ other._sign)
                )
            else:
                return context._raise_error(DivisionUndefined, "0 // 0")
        return self._divide(other, context)[0]

    def __rfloordiv__(self, other, context=None):
        "Swaps self/other and returns __floordiv__."
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        return other.__floordiv__(self, context=context)

    def __float__(self):
        "Float representation."
        if self._isnan():
            if self.is_snan():
                raise ValueError("Cannot convert signaling NaN to float")
            s = "-nan" if self._sign else "nan"
        else:
            s = str(self)
        return float(s)

    def __int__(self):
        "Converts self to an int, truncating if necessary."
        if self._is_special:
            if self._isnan():
                raise ValueError("Cannot convert NaN to integer")
            elif self._isinfinity():
                raise OverflowError("Cannot convert infinity to integer")
        s = (-1) ** self._sign
        if self._exp >= 0:
            return (s * int(self._int)) * (10 ** self._exp)
        else:
            return s * int((self._int[: self._exp] or "0"))

    __trunc__ = __int__

    @property
    def real(self):
        return self

    @property
    def imag(self):
        return Decimal(0)

    def conjugate(self):
        return self

    def __complex__(self):
        return complex(float(self))

    def _fix_nan(self, context):
        "Decapitate the payload of a NaN to fit the context"
        payload = self._int
        max_payload_len = context.prec - context.clamp
        if len(payload) > max_payload_len:
            payload = payload[(len(payload) - max_payload_len) :].lstrip("0")
            return _dec_from_triple(self._sign, payload, self._exp, True)
        return Decimal(self)

    def _fix(self, context):
        "Round if it is necessary to keep self within prec precision.\n\n        Rounds and fixes the exponent.  Does not raise on a sNaN.\n\n        Arguments:\n        self - Decimal instance\n        context - context used.\n        "
        if self._is_special:
            if self._isnan():
                return self._fix_nan(context)
            else:
                return Decimal(self)
        Etiny = context.Etiny()
        Etop = context.Etop()
        if not self:
            exp_max = [context.Emax, Etop][context.clamp]
            new_exp = min(max(self._exp, Etiny), exp_max)
            if new_exp != self._exp:
                context._raise_error(Clamped)
                return _dec_from_triple(self._sign, "0", new_exp)
            else:
                return Decimal(self)
        exp_min = (len(self._int) + self._exp) - context.prec
        if exp_min > Etop:
            ans = context._raise_error(Overflow, "above Emax", self._sign)
            context._raise_error(Inexact)
            context._raise_error(Rounded)
            return ans
        self_is_subnormal = exp_min < Etiny
        if self_is_subnormal:
            exp_min = Etiny
        if self._exp < exp_min:
            digits = (len(self._int) + self._exp) - exp_min
            if digits < 0:
                self = _dec_from_triple(self._sign, "1", (exp_min - 1))
                digits = 0
            rounding_method = self._pick_rounding_function[context.rounding]
            changed = rounding_method(self, digits)
            coeff = self._int[:digits] or "0"
            if changed > 0:
                coeff = str((int(coeff) + 1))
                if len(coeff) > context.prec:
                    coeff = coeff[:(-1)]
                    exp_min += 1
            if exp_min > Etop:
                ans = context._raise_error(Overflow, "above Emax", self._sign)
            else:
                ans = _dec_from_triple(self._sign, coeff, exp_min)
            if changed and self_is_subnormal:
                context._raise_error(Underflow)
            if self_is_subnormal:
                context._raise_error(Subnormal)
            if changed:
                context._raise_error(Inexact)
            context._raise_error(Rounded)
            if not ans:
                context._raise_error(Clamped)
            return ans
        if self_is_subnormal:
            context._raise_error(Subnormal)
        if (context.clamp == 1) and (self._exp > Etop):
            context._raise_error(Clamped)
            self_padded = self._int + ("0" * (self._exp - Etop))
            return _dec_from_triple(self._sign, self_padded, Etop)
        return Decimal(self)

    def _round_down(self, prec):
        "Also known as round-towards-0, truncate."
        if _all_zeros(self._int, prec):
            return 0
        else:
            return -1

    def _round_up(self, prec):
        "Rounds away from 0."
        return -self._round_down(prec)

    def _round_half_up(self, prec):
        "Rounds 5 up (away from 0)"
        if self._int[prec] in "56789":
            return 1
        elif _all_zeros(self._int, prec):
            return 0
        else:
            return -1

    def _round_half_down(self, prec):
        "Round 5 down"
        if _exact_half(self._int, prec):
            return -1
        else:
            return self._round_half_up(prec)

    def _round_half_even(self, prec):
        "Round 5 to even, rest to nearest."
        if _exact_half(self._int, prec) and (
            (prec == 0) or (self._int[(prec - 1)] in "02468")
        ):
            return -1
        else:
            return self._round_half_up(prec)

    def _round_ceiling(self, prec):
        "Rounds up (not away from 0 if negative.)"
        if self._sign:
            return self._round_down(prec)
        else:
            return -self._round_down(prec)

    def _round_floor(self, prec):
        "Rounds down (not towards 0 if negative)"
        if not self._sign:
            return self._round_down(prec)
        else:
            return -self._round_down(prec)

    def _round_05up(self, prec):
        "Round down unless digit prec-1 is 0 or 5."
        if prec and (self._int[(prec - 1)] not in "05"):
            return self._round_down(prec)
        else:
            return -self._round_down(prec)

    _pick_rounding_function = dict(
        ROUND_DOWN=_round_down,
        ROUND_UP=_round_up,
        ROUND_HALF_UP=_round_half_up,
        ROUND_HALF_DOWN=_round_half_down,
        ROUND_HALF_EVEN=_round_half_even,
        ROUND_CEILING=_round_ceiling,
        ROUND_FLOOR=_round_floor,
        ROUND_05UP=_round_05up,
    )

    def __round__(self, n=None):
        "Round self to the nearest integer, or to a given precision.\n\n        If only one argument is supplied, round a finite Decimal\n        instance self to the nearest integer.  If self is infinite or\n        a NaN then a Python exception is raised.  If self is finite\n        and lies exactly halfway between two integers then it is\n        rounded to the integer with even last digit.\n\n        >>> round(Decimal('123.456'))\n        123\n        >>> round(Decimal('-456.789'))\n        -457\n        >>> round(Decimal('-3.0'))\n        -3\n        >>> round(Decimal('2.5'))\n        2\n        >>> round(Decimal('3.5'))\n        4\n        >>> round(Decimal('Inf'))\n        Traceback (most recent call last):\n          ...\n        OverflowError: cannot round an infinity\n        >>> round(Decimal('NaN'))\n        Traceback (most recent call last):\n          ...\n        ValueError: cannot round a NaN\n\n        If a second argument n is supplied, self is rounded to n\n        decimal places using the rounding mode for the current\n        context.\n\n        For an integer n, round(self, -n) is exactly equivalent to\n        self.quantize(Decimal('1En')).\n\n        >>> round(Decimal('123.456'), 0)\n        Decimal('123')\n        >>> round(Decimal('123.456'), 2)\n        Decimal('123.46')\n        >>> round(Decimal('123.456'), -2)\n        Decimal('1E+2')\n        >>> round(Decimal('-Infinity'), 37)\n        Decimal('NaN')\n        >>> round(Decimal('sNaN123'), 0)\n        Decimal('NaN123')\n\n        "
        if n is not None:
            if not isinstance(n, int):
                raise TypeError("Second argument to round should be integral")
            exp = _dec_from_triple(0, "1", (-n))
            return self.quantize(exp)
        if self._is_special:
            if self.is_nan():
                raise ValueError("cannot round a NaN")
            else:
                raise OverflowError("cannot round an infinity")
        return int(self._rescale(0, ROUND_HALF_EVEN))

    def __floor__(self):
        "Return the floor of self, as an integer.\n\n        For a finite Decimal instance self, return the greatest\n        integer n such that n <= self.  If self is infinite or a NaN\n        then a Python exception is raised.\n\n        "
        if self._is_special:
            if self.is_nan():
                raise ValueError("cannot round a NaN")
            else:
                raise OverflowError("cannot round an infinity")
        return int(self._rescale(0, ROUND_FLOOR))

    def __ceil__(self):
        "Return the ceiling of self, as an integer.\n\n        For a finite Decimal instance self, return the least integer n\n        such that n >= self.  If self is infinite or a NaN then a\n        Python exception is raised.\n\n        "
        if self._is_special:
            if self.is_nan():
                raise ValueError("cannot round a NaN")
            else:
                raise OverflowError("cannot round an infinity")
        return int(self._rescale(0, ROUND_CEILING))

    def fma(self, other, third, context=None):
        "Fused multiply-add.\n\n        Returns self*other+third with no rounding of the intermediate\n        product self*other.\n\n        self and other are multiplied together, with no rounding of\n        the result.  The third operand is then added to the result,\n        and a single final rounding is performed.\n        "
        other = _convert_other(other, raiseit=True)
        third = _convert_other(third, raiseit=True)
        if self._is_special or other._is_special:
            if context is None:
                context = getcontext()
            if self._exp == "N":
                return context._raise_error(InvalidOperation, "sNaN", self)
            if other._exp == "N":
                return context._raise_error(InvalidOperation, "sNaN", other)
            if self._exp == "n":
                product = self
            elif other._exp == "n":
                product = other
            elif self._exp == "F":
                if not other:
                    return context._raise_error(InvalidOperation, "INF * 0 in fma")
                product = _SignedInfinity[(self._sign ^ other._sign)]
            elif other._exp == "F":
                if not self:
                    return context._raise_error(InvalidOperation, "0 * INF in fma")
                product = _SignedInfinity[(self._sign ^ other._sign)]
        else:
            product = _dec_from_triple(
                (self._sign ^ other._sign),
                str((int(self._int) * int(other._int))),
                (self._exp + other._exp),
            )
        return product.__add__(third, context)

    def _power_modulo(self, other, modulo, context=None):
        "Three argument version of __pow__"
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        modulo = _convert_other(modulo)
        if modulo is NotImplemented:
            return modulo
        if context is None:
            context = getcontext()
        self_is_nan = self._isnan()
        other_is_nan = other._isnan()
        modulo_is_nan = modulo._isnan()
        if self_is_nan or other_is_nan or modulo_is_nan:
            if self_is_nan == 2:
                return context._raise_error(InvalidOperation, "sNaN", self)
            if other_is_nan == 2:
                return context._raise_error(InvalidOperation, "sNaN", other)
            if modulo_is_nan == 2:
                return context._raise_error(InvalidOperation, "sNaN", modulo)
            if self_is_nan:
                return self._fix_nan(context)
            if other_is_nan:
                return other._fix_nan(context)
            return modulo._fix_nan(context)
        if not (self._isinteger() and other._isinteger() and modulo._isinteger()):
            return context._raise_error(
                InvalidOperation,
                "pow() 3rd argument not allowed unless all arguments are integers",
            )
        if other < 0:
            return context._raise_error(
                InvalidOperation,
                "pow() 2nd argument cannot be negative when 3rd argument specified",
            )
        if not modulo:
            return context._raise_error(
                InvalidOperation, "pow() 3rd argument cannot be 0"
            )
        if modulo.adjusted() >= context.prec:
            return context._raise_error(
                InvalidOperation,
                "insufficient precision: pow() 3rd argument must not have more than precision digits",
            )
        if (not other) and (not self):
            return context._raise_error(
                InvalidOperation,
                "at least one of pow() 1st argument and 2nd argument must be nonzero; 0**0 is not defined",
            )
        if other._iseven():
            sign = 0
        else:
            sign = self._sign
        modulo = abs(int(modulo))
        base = _WorkRep(self.to_integral_value())
        exponent = _WorkRep(other.to_integral_value())
        base = ((base.int % modulo) * pow(10, base.exp, modulo)) % modulo
        for i in range(exponent.exp):
            base = pow(base, 10, modulo)
        base = pow(base, exponent.int, modulo)
        return _dec_from_triple(sign, str(base), 0)

    def _power_exact(self, other, p):
        "Attempt to compute self**other exactly.\n\n        Given Decimals self and other and an integer p, attempt to\n        compute an exact result for the power self**other, with p\n        digits of precision.  Return None if self**other is not\n        exactly representable in p digits.\n\n        Assumes that elimination of special cases has already been\n        performed: self and other must both be nonspecial; self must\n        be positive and not numerically equal to 1; other must be\n        nonzero.  For efficiency, other._exp should not be too large,\n        so that 10**abs(other._exp) is a feasible calculation."
        x = _WorkRep(self)
        (xc, xe) = (x.int, x.exp)
        while (xc % 10) == 0:
            xc //= 10
            xe += 1
        y = _WorkRep(other)
        (yc, ye) = (y.int, y.exp)
        while (yc % 10) == 0:
            yc //= 10
            ye += 1
        if xc == 1:
            xe *= yc
            while (xe % 10) == 0:
                xe //= 10
                ye += 1
            if ye < 0:
                return None
            exponent = xe * (10 ** ye)
            if y.sign == 1:
                exponent = -exponent
            if other._isinteger() and (other._sign == 0):
                ideal_exponent = self._exp * int(other)
                zeros = min((exponent - ideal_exponent), (p - 1))
            else:
                zeros = 0
            return _dec_from_triple(0, ("1" + ("0" * zeros)), (exponent - zeros))
        if y.sign == 1:
            last_digit = xc % 10
            if last_digit in (2, 4, 6, 8):
                if (xc & (-xc)) != xc:
                    return None
                e = _nbits(xc) - 1
                emax = (p * 93) // 65
                if ye >= len(str(emax)):
                    return None
                e = _decimal_lshift_exact((e * yc), ye)
                xe = _decimal_lshift_exact((xe * yc), ye)
                if (e is None) or (xe is None):
                    return None
                if e > emax:
                    return None
                xc = 5 ** e
            elif last_digit == 5:
                e = (_nbits(xc) * 28) // 65
                (xc, remainder) = divmod((5 ** e), xc)
                if remainder:
                    return None
                while (xc % 5) == 0:
                    xc //= 5
                    e -= 1
                emax = (p * 10) // 3
                if ye >= len(str(emax)):
                    return None
                e = _decimal_lshift_exact((e * yc), ye)
                xe = _decimal_lshift_exact((xe * yc), ye)
                if (e is None) or (xe is None):
                    return None
                if e > emax:
                    return None
                xc = 2 ** e
            else:
                return None
            if xc >= (10 ** p):
                return None
            xe = (-e) - xe
            return _dec_from_triple(0, str(xc), xe)
        if ye >= 0:
            (m, n) = ((yc * (10 ** ye)), 1)
        else:
            if (xe != 0) and (len(str(abs((yc * xe)))) <= (-ye)):
                return None
            xc_bits = _nbits(xc)
            if (xc != 1) and (len(str((abs(yc) * xc_bits))) <= (-ye)):
                return None
            (m, n) = (yc, (10 ** (-ye)))
            while (m % 2) == (n % 2) == 0:
                m //= 2
                n //= 2
            while (m % 5) == (n % 5) == 0:
                m //= 5
                n //= 5
        if n > 1:
            if (xc != 1) and (xc_bits <= n):
                return None
            (xe, rem) = divmod(xe, n)
            if rem != 0:
                return None
            a = 1 << (-((-_nbits(xc)) // n))
            while True:
                (q, r) = divmod(xc, (a ** (n - 1)))
                if a <= q:
                    break
                else:
                    a = ((a * (n - 1)) + q) // n
            if not ((a == q) and (r == 0)):
                return None
            xc = a
        if (xc > 1) and (m > ((p * 100) // _log10_lb(xc))):
            return None
        xc = xc ** m
        xe *= m
        if xc > (10 ** p):
            return None
        str_xc = str(xc)
        if other._isinteger() and (other._sign == 0):
            ideal_exponent = self._exp * int(other)
            zeros = min((xe - ideal_exponent), (p - len(str_xc)))
        else:
            zeros = 0
        return _dec_from_triple(0, (str_xc + ("0" * zeros)), (xe - zeros))

    def __pow__(self, other, modulo=None, context=None):
        "Return self ** other [ % modulo].\n\n        With two arguments, compute self**other.\n\n        With three arguments, compute (self**other) % modulo.  For the\n        three argument form, the following restrictions on the\n        arguments hold:\n\n         - all three arguments must be integral\n         - other must be nonnegative\n         - either self or other (or both) must be nonzero\n         - modulo must be nonzero and must have at most p digits,\n           where p is the context precision.\n\n        If any of these restrictions is violated the InvalidOperation\n        flag is raised.\n\n        The result of pow(self, other, modulo) is identical to the\n        result that would be obtained by computing (self**other) %\n        modulo with unbounded precision, but is computed more\n        efficiently.  It is always exact.\n        "
        if modulo is not None:
            return self._power_modulo(other, modulo, context)
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        if context is None:
            context = getcontext()
        ans = self._check_nans(other, context)
        if ans:
            return ans
        if not other:
            if not self:
                return context._raise_error(InvalidOperation, "0 ** 0")
            else:
                return _One
        result_sign = 0
        if self._sign == 1:
            if other._isinteger():
                if not other._iseven():
                    result_sign = 1
            elif self:
                return context._raise_error(
                    InvalidOperation, "x ** y with x negative and y not an integer"
                )
            self = self.copy_negate()
        if not self:
            if other._sign == 0:
                return _dec_from_triple(result_sign, "0", 0)
            else:
                return _SignedInfinity[result_sign]
        if self._isinfinity():
            if other._sign == 0:
                return _SignedInfinity[result_sign]
            else:
                return _dec_from_triple(result_sign, "0", 0)
        if self == _One:
            if other._isinteger():
                if other._sign == 1:
                    multiplier = 0
                elif other > context.prec:
                    multiplier = context.prec
                else:
                    multiplier = int(other)
                exp = self._exp * multiplier
                if exp < (1 - context.prec):
                    exp = 1 - context.prec
                    context._raise_error(Rounded)
            else:
                context._raise_error(Inexact)
                context._raise_error(Rounded)
                exp = 1 - context.prec
            return _dec_from_triple(result_sign, ("1" + ("0" * (-exp))), exp)
        self_adj = self.adjusted()
        if other._isinfinity():
            if (other._sign == 0) == (self_adj < 0):
                return _dec_from_triple(result_sign, "0", 0)
            else:
                return _SignedInfinity[result_sign]
        ans = None
        exact = False
        bound = self._log10_exp_bound() + other.adjusted()
        if (self_adj >= 0) == (other._sign == 0):
            if bound >= len(str(context.Emax)):
                ans = _dec_from_triple(result_sign, "1", (context.Emax + 1))
        else:
            Etiny = context.Etiny()
            if bound >= len(str((-Etiny))):
                ans = _dec_from_triple(result_sign, "1", (Etiny - 1))
        if ans is None:
            ans = self._power_exact(other, (context.prec + 1))
            if ans is not None:
                if result_sign == 1:
                    ans = _dec_from_triple(1, ans._int, ans._exp)
                exact = True
        if ans is None:
            p = context.prec
            x = _WorkRep(self)
            (xc, xe) = (x.int, x.exp)
            y = _WorkRep(other)
            (yc, ye) = (y.int, y.exp)
            if y.sign == 1:
                yc = -yc
            extra = 3
            while True:
                (coeff, exp) = _dpower(xc, xe, yc, ye, (p + extra))
                if coeff % (5 * (10 ** ((len(str(coeff)) - p) - 1))):
                    break
                extra += 3
            ans = _dec_from_triple(result_sign, str(coeff), exp)
        if exact and (not other._isinteger()):
            if len(ans._int) <= context.prec:
                expdiff = (context.prec + 1) - len(ans._int)
                ans = _dec_from_triple(
                    ans._sign, (ans._int + ("0" * expdiff)), (ans._exp - expdiff)
                )
            newcontext = context.copy()
            newcontext.clear_flags()
            for exception in _signals:
                newcontext.traps[exception] = 0
            ans = ans._fix(newcontext)
            newcontext._raise_error(Inexact)
            if newcontext.flags[Subnormal]:
                newcontext._raise_error(Underflow)
            if newcontext.flags[Overflow]:
                context._raise_error(Overflow, "above Emax", ans._sign)
            for exception in (Underflow, Subnormal, Inexact, Rounded, Clamped):
                if newcontext.flags[exception]:
                    context._raise_error(exception)
        else:
            ans = ans._fix(context)
        return ans

    def __rpow__(self, other, context=None):
        "Swaps self/other and returns __pow__."
        other = _convert_other(other)
        if other is NotImplemented:
            return other
        return other.__pow__(self, context=context)

    def normalize(self, context=None):
        "Normalize- strip trailing 0s, change anything equal to 0 to 0e0"
        if context is None:
            context = getcontext()
        if self._is_special:
            ans = self._check_nans(context=context)
            if ans:
                return ans
        dup = self._fix(context)
        if dup._isinfinity():
            return dup
        if not dup:
            return _dec_from_triple(dup._sign, "0", 0)
        exp_max = [context.Emax, context.Etop()][context.clamp]
        end = len(dup._int)
        exp = dup._exp
        while (dup._int[(end - 1)] == "0") and (exp < exp_max):
            exp += 1
            end -= 1
        return _dec_from_triple(dup._sign, dup._int[:end], exp)

    def quantize(self, exp, rounding=None, context=None):
        "Quantize self so its exponent is the same as that of exp.\n\n        Similar to self._rescale(exp._exp) but with error checking.\n        "
        exp = _convert_other(exp, raiseit=True)
        if context is None:
            context = getcontext()
        if rounding is None:
            rounding = context.rounding
        if self._is_special or exp._is_special:
            ans = self._check_nans(exp, context)
            if ans:
                return ans
            if exp._isinfinity() or self._isinfinity():
                if exp._isinfinity() and self._isinfinity():
                    return Decimal(self)
                return context._raise_error(InvalidOperation, "quantize with one INF")
        if not (context.Etiny() <= exp._exp <= context.Emax):
            return context._raise_error(
                InvalidOperation, "target exponent out of bounds in quantize"
            )
        if not self:
            ans = _dec_from_triple(self._sign, "0", exp._exp)
            return ans._fix(context)
        self_adjusted = self.adjusted()
        if self_adjusted > context.Emax:
            return context._raise_error(
                InvalidOperation,
                "exponent of quantize result too large for current context",
            )
        if ((self_adjusted - exp._exp) + 1) > context.prec:
            return context._raise_error(
                InvalidOperation,
                "quantize result has too many digits for current context",
            )
        ans = self._rescale(exp._exp, rounding)
        if ans.adjusted() > context.Emax:
            return context._raise_error(
                InvalidOperation,
                "exponent of quantize result too large for current context",
            )
        if len(ans._int) > context.prec:
            return context._raise_error(
                InvalidOperation,
                "quantize result has too many digits for current context",
            )
        if ans and (ans.adjusted() < context.Emin):
            context._raise_error(Subnormal)
        if ans._exp > self._exp:
            if ans != self:
                context._raise_error(Inexact)
            context._raise_error(Rounded)
        ans = ans._fix(context)
        return ans

    def same_quantum(self, other, context=None):
        "Return True if self and other have the same exponent; otherwise\n        return False.\n\n        If either operand is a special value, the following rules are used:\n           * return True if both operands are infinities\n           * return True if both operands are NaNs\n           * otherwise, return False.\n        "
        other = _convert_other(other, raiseit=True)
        if self._is_special or other._is_special:
            return (self.is_nan() and other.is_nan()) or (
                self.is_infinite() and other.is_infinite()
            )
        return self._exp == other._exp

    def _rescale(self, exp, rounding):
        "Rescale self so that the exponent is exp, either by padding with zeros\n        or by truncating digits, using the given rounding mode.\n\n        Specials are returned without change.  This operation is\n        quiet: it raises no flags, and uses no information from the\n        context.\n\n        exp = exp to scale to (an integer)\n        rounding = rounding mode\n        "
        if self._is_special:
            return Decimal(self)
        if not self:
            return _dec_from_triple(self._sign, "0", exp)
        if self._exp >= exp:
            return _dec_from_triple(
                self._sign, (self._int + ("0" * (self._exp - exp))), exp
            )
        digits = (len(self._int) + self._exp) - exp
        if digits < 0:
            self = _dec_from_triple(self._sign, "1", (exp - 1))
            digits = 0
        this_function = self._pick_rounding_function[rounding]
        changed = this_function(self, digits)
        coeff = self._int[:digits] or "0"
        if changed == 1:
            coeff = str((int(coeff) + 1))
        return _dec_from_triple(self._sign, coeff, exp)

    def _round(self, places, rounding):
        "Round a nonzero, nonspecial Decimal to a fixed number of\n        significant figures, using the given rounding mode.\n\n        Infinities, NaNs and zeros are returned unaltered.\n\n        This operation is quiet: it raises no flags, and uses no\n        information from the context.\n\n        "
        if places <= 0:
            raise ValueError("argument should be at least 1 in _round")
        if self._is_special or (not self):
            return Decimal(self)
        ans = self._rescale(((self.adjusted() + 1) - places), rounding)
        if ans.adjusted() != self.adjusted():
            ans = ans._rescale(((ans.adjusted() + 1) - places), rounding)
        return ans

    def to_integral_exact(self, rounding=None, context=None):
        "Rounds to a nearby integer.\n\n        If no rounding mode is specified, take the rounding mode from\n        the context.  This method raises the Rounded and Inexact flags\n        when appropriate.\n\n        See also: to_integral_value, which does exactly the same as\n        this method except that it doesn't raise Inexact or Rounded.\n        "
        if self._is_special:
            ans = self._check_nans(context=context)
            if ans:
                return ans
            return Decimal(self)
        if self._exp >= 0:
            return Decimal(self)
        if not self:
            return _dec_from_triple(self._sign, "0", 0)
        if context is None:
            context = getcontext()
        if rounding is None:
            rounding = context.rounding
        ans = self._rescale(0, rounding)
        if ans != self:
            context._raise_error(Inexact)
        context._raise_error(Rounded)
        return ans

    def to_integral_value(self, rounding=None, context=None):
        "Rounds to the nearest integer, without raising inexact, rounded."
        if context is None:
            context = getcontext()
        if rounding is None:
            rounding = context.rounding
        if self._is_special:
            ans = self._check_nans(context=context)
            if ans:
                return ans
            return Decimal(self)
        if self._exp >= 0:
            return Decimal(self)
        else:
            return self._rescale(0, rounding)

    to_integral = to_integral_value

    def sqrt(self, context=None):
        "Return the square root of self."
        if context is None:
            context = getcontext()
        if self._is_special:
            ans = self._check_nans(context=context)
            if ans:
                return ans
            if self._isinfinity() and (self._sign == 0):
                return Decimal(self)
        if not self:
            ans = _dec_from_triple(self._sign, "0", (self._exp // 2))
            return ans._fix(context)
        if self._sign == 1:
            return context._raise_error(InvalidOperation, "sqrt(-x), x > 0")
        prec = context.prec + 1
        op = _WorkRep(self)
        e = op.exp >> 1
        if op.exp & 1:
            c = op.int * 10
            l = (len(self._int) >> 1) + 1
        else:
            c = op.int
            l = (len(self._int) + 1) >> 1
        shift = prec - l
        if shift >= 0:
            c *= 100 ** shift
            exact = True
        else:
            (c, remainder) = divmod(c, (100 ** (-shift)))
            exact = not remainder
        e -= shift
        n = 10 ** prec
        while True:
            q = c // n
            if n <= q:
                break
            else:
                n = (n + q) >> 1
        exact = exact and ((n * n) == c)
        if exact:
            if shift >= 0:
                n //= 10 ** shift
            else:
                n *= 10 ** (-shift)
            e += shift
        elif (n % 5) == 0:
            n += 1
        ans = _dec_from_triple(0, str(n), e)
        context = context._shallow_copy()
        rounding = context._set_rounding(ROUND_HALF_EVEN)
        ans = ans._fix(context)
        context.rounding = rounding
        return ans

    def max(self, other, context=None):
        "Returns the larger value.\n\n        Like max(self, other) except if one is not a number, returns\n        NaN (and signals if one is sNaN).  Also rounds.\n        "
        other = _convert_other(other, raiseit=True)
        if context is None:
            context = getcontext()
        if self._is_special or other._is_special:
            sn = self._isnan()
            on = other._isnan()
            if sn or on:
                if (on == 1) and (sn == 0):
                    return self._fix(context)
                if (sn == 1) and (on == 0):
                    return other._fix(context)
                return self._check_nans(other, context)
        c = self._cmp(other)
        if c == 0:
            c = self.compare_total(other)
        if c == (-1):
            ans = other
        else:
            ans = self
        return ans._fix(context)

    def min(self, other, context=None):
        "Returns the smaller value.\n\n        Like min(self, other) except if one is not a number, returns\n        NaN (and signals if one is sNaN).  Also rounds.\n        "
        other = _convert_other(other, raiseit=True)
        if context is None:
            context = getcontext()
        if self._is_special or other._is_special:
            sn = self._isnan()
            on = other._isnan()
            if sn or on:
                if (on == 1) and (sn == 0):
                    return self._fix(context)
                if (sn == 1) and (on == 0):
                    return other._fix(context)
                return self._check_nans(other, context)
        c = self._cmp(other)
        if c == 0:
            c = self.compare_total(other)
        if c == (-1):
            ans = self
        else:
            ans = other
        return ans._fix(context)

    def _isinteger(self):
        "Returns whether self is an integer"
        if self._is_special:
            return False
        if self._exp >= 0:
            return True
        rest = self._int[self._exp :]
        return rest == ("0" * len(rest))

    def _iseven(self):
        "Returns True if self is even.  Assumes self is an integer."
        if (not self) or (self._exp > 0):
            return True
        return self._int[((-1) + self._exp)] in "02468"

    def adjusted(self):
        "Return the adjusted exponent of self"
        try:
            return (self._exp + len(self._int)) - 1
        except TypeError:
            return 0

    def canonical(self):
        "Returns the same Decimal object.\n\n        As we do not have different encodings for the same number, the\n        received object already is in its canonical form.\n        "
        return self

    def compare_signal(self, other, context=None):
        "Compares self to the other operand numerically.\n\n        It's pretty much like compare(), but all NaNs signal, with signaling\n        NaNs taking precedence over quiet NaNs.\n        "
        other = _convert_other(other, raiseit=True)
        ans = self._compare_check_nans(other, context)
        if ans:
            return ans
        return self.compare(other, context=context)

    def compare_total(self, other, context=None):
        "Compares self to other using the abstract representations.\n\n        This is not like the standard compare, which use their numerical\n        value. Note that a total ordering is defined for all possible abstract\n        representations.\n        "
        other = _convert_other(other, raiseit=True)
        if self._sign and (not other._sign):
            return _NegativeOne
        if (not self._sign) and other._sign:
            return _One
        sign = self._sign
        self_nan = self._isnan()
        other_nan = other._isnan()
        if self_nan or other_nan:
            if self_nan == other_nan:
                self_key = (len(self._int), self._int)
                other_key = (len(other._int), other._int)
                if self_key < other_key:
                    if sign:
                        return _One
                    else:
                        return _NegativeOne
                if self_key > other_key:
                    if sign:
                        return _NegativeOne
                    else:
                        return _One
                return _Zero
            if sign:
                if self_nan == 1:
                    return _NegativeOne
                if other_nan == 1:
                    return _One
                if self_nan == 2:
                    return _NegativeOne
                if other_nan == 2:
                    return _One
            else:
                if self_nan == 1:
                    return _One
                if other_nan == 1:
                    return _NegativeOne
                if self_nan == 2:
                    return _One
                if other_nan == 2:
                    return _NegativeOne
        if self < other:
            return _NegativeOne
        if self > other:
            return _One
        if self._exp < other._exp:
            if sign:
                return _One
            else:
                return _NegativeOne
        if self._exp > other._exp:
            if sign:
                return _NegativeOne
            else:
                return _One
        return _Zero

    def compare_total_mag(self, other, context=None):
        "Compares self to other using abstract repr., ignoring sign.\n\n        Like compare_total, but with operand's sign ignored and assumed to be 0.\n        "
        other = _convert_other(other, raiseit=True)
        s = self.copy_abs()
        o = other.copy_abs()
        return s.compare_total(o)

    def copy_abs(self):
        "Returns a copy with the sign set to 0. "
        return _dec_from_triple(0, self._int, self._exp, self._is_special)

    def copy_negate(self):
        "Returns a copy with the sign inverted."
        if self._sign:
            return _dec_from_triple(0, self._int, self._exp, self._is_special)
        else:
            return _dec_from_triple(1, self._int, self._exp, self._is_special)

    def copy_sign(self, other, context=None):
        "Returns self with the sign of other."
        other = _convert_other(other, raiseit=True)
        return _dec_from_triple(other._sign, self._int, self._exp, self._is_special)

    def exp(self, context=None):
        "Returns e ** self."
        if context is None:
            context = getcontext()
        ans = self._check_nans(context=context)
        if ans:
            return ans
        if self._isinfinity() == (-1):
            return _Zero
        if not self:
            return _One
        if self._isinfinity() == 1:
            return Decimal(self)
        p = context.prec
        adj = self.adjusted()
        if (self._sign == 0) and (adj > len(str(((context.Emax + 1) * 3)))):
            ans = _dec_from_triple(0, "1", (context.Emax + 1))
        elif (self._sign == 1) and (adj > len(str((((-context.Etiny()) + 1) * 3)))):
            ans = _dec_from_triple(0, "1", (context.Etiny() - 1))
        elif (self._sign == 0) and (adj < (-p)):
            ans = _dec_from_triple(0, (("1" + ("0" * (p - 1))) + "1"), (-p))
        elif (self._sign == 1) and (adj < ((-p) - 1)):
            ans = _dec_from_triple(0, ("9" * (p + 1)), ((-p) - 1))
        else:
            op = _WorkRep(self)
            (c, e) = (op.int, op.exp)
            if op.sign == 1:
                c = -c
            extra = 3
            while True:
                (coeff, exp) = _dexp(c, e, (p + extra))
                if coeff % (5 * (10 ** ((len(str(coeff)) - p) - 1))):
                    break
                extra += 3
            ans = _dec_from_triple(0, str(coeff), exp)
        context = context._shallow_copy()
        rounding = context._set_rounding(ROUND_HALF_EVEN)
        ans = ans._fix(context)
        context.rounding = rounding
        return ans

    def is_canonical(self):
        "Return True if self is canonical; otherwise return False.\n\n        Currently, the encoding of a Decimal instance is always\n        canonical, so this method returns True for any Decimal.\n        "
        return True

    def is_finite(self):
        "Return True if self is finite; otherwise return False.\n\n        A Decimal instance is considered finite if it is neither\n        infinite nor a NaN.\n        "
        return not self._is_special

    def is_infinite(self):
        "Return True if self is infinite; otherwise return False."
        return self._exp == "F"

    def is_nan(self):
        "Return True if self is a qNaN or sNaN; otherwise return False."
        return self._exp in ("n", "N")

    def is_normal(self, context=None):
        "Return True if self is a normal number; otherwise return False."
        if self._is_special or (not self):
            return False
        if context is None:
            context = getcontext()
        return context.Emin <= self.adjusted()

    def is_qnan(self):
        "Return True if self is a quiet NaN; otherwise return False."
        return self._exp == "n"

    def is_signed(self):
        "Return True if self is negative; otherwise return False."
        return self._sign == 1

    def is_snan(self):
        "Return True if self is a signaling NaN; otherwise return False."
        return self._exp == "N"

    def is_subnormal(self, context=None):
        "Return True if self is subnormal; otherwise return False."
        if self._is_special or (not self):
            return False
        if context is None:
            context = getcontext()
        return self.adjusted() < context.Emin

    def is_zero(self):
        "Return True if self is a zero; otherwise return False."
        return (not self._is_special) and (self._int == "0")

    def _ln_exp_bound(self):
        "Compute a lower bound for the adjusted exponent of self.ln().\n        In other words, compute r such that self.ln() >= 10**r.  Assumes\n        that self is finite and positive and that self != 1.\n        "
        adj = (self._exp + len(self._int)) - 1
        if adj >= 1:
            return len(str(((adj * 23) // 10))) - 1
        if adj <= (-2):
            return len(str(((((-1) - adj) * 23) // 10))) - 1
        op = _WorkRep(self)
        (c, e) = (op.int, op.exp)
        if adj == 0:
            num = str((c - (10 ** (-e))))
            den = str(c)
            return (len(num) - len(den)) - (num < den)
        return (e + len(str(((10 ** (-e)) - c)))) - 1

    def ln(self, context=None):
        "Returns the natural (base e) logarithm of self."
        if context is None:
            context = getcontext()
        ans = self._check_nans(context=context)
        if ans:
            return ans
        if not self:
            return _NegativeInfinity
        if self._isinfinity() == 1:
            return _Infinity
        if self == _One:
            return _Zero
        if self._sign == 1:
            return context._raise_error(InvalidOperation, "ln of a negative value")
        op = _WorkRep(self)
        (c, e) = (op.int, op.exp)
        p = context.prec
        places = (p - self._ln_exp_bound()) + 2
        while True:
            coeff = _dlog(c, e, places)
            if coeff % (5 * (10 ** ((len(str(abs(coeff))) - p) - 1))):
                break
            places += 3
        ans = _dec_from_triple(int((coeff < 0)), str(abs(coeff)), (-places))
        context = context._shallow_copy()
        rounding = context._set_rounding(ROUND_HALF_EVEN)
        ans = ans._fix(context)
        context.rounding = rounding
        return ans

    def _log10_exp_bound(self):
        "Compute a lower bound for the adjusted exponent of self.log10().\n        In other words, find r such that self.log10() >= 10**r.\n        Assumes that self is finite and positive and that self != 1.\n        "
        adj = (self._exp + len(self._int)) - 1
        if adj >= 1:
            return len(str(adj)) - 1
        if adj <= (-2):
            return len(str(((-1) - adj))) - 1
        op = _WorkRep(self)
        (c, e) = (op.int, op.exp)
        if adj == 0:
            num = str((c - (10 ** (-e))))
            den = str((231 * c))
            return ((len(num) - len(den)) - (num < den)) + 2
        num = str(((10 ** (-e)) - c))
        return ((len(num) + e) - (num < "231")) - 1

    def log10(self, context=None):
        "Returns the base 10 logarithm of self."
        if context is None:
            context = getcontext()
        ans = self._check_nans(context=context)
        if ans:
            return ans
        if not self:
            return _NegativeInfinity
        if self._isinfinity() == 1:
            return _Infinity
        if self._sign == 1:
            return context._raise_error(InvalidOperation, "log10 of a negative value")
        if (self._int[0] == "1") and (self._int[1:] == ("0" * (len(self._int) - 1))):
            ans = Decimal(((self._exp + len(self._int)) - 1))
        else:
            op = _WorkRep(self)
            (c, e) = (op.int, op.exp)
            p = context.prec
            places = (p - self._log10_exp_bound()) + 2
            while True:
                coeff = _dlog10(c, e, places)
                if coeff % (5 * (10 ** ((len(str(abs(coeff))) - p) - 1))):
                    break
                places += 3
            ans = _dec_from_triple(int((coeff < 0)), str(abs(coeff)), (-places))
        context = context._shallow_copy()
        rounding = context._set_rounding(ROUND_HALF_EVEN)
        ans = ans._fix(context)
        context.rounding = rounding
        return ans

    def logb(self, context=None):
        " Returns the exponent of the magnitude of self's MSD.\n\n        The result is the integer which is the exponent of the magnitude\n        of the most significant digit of self (as though it were truncated\n        to a single digit while maintaining the value of that digit and\n        without limiting the resulting exponent).\n        "
        ans = self._check_nans(context=context)
        if ans:
            return ans
        if context is None:
            context = getcontext()
        if self._isinfinity():
            return _Infinity
        if not self:
            return context._raise_error(DivisionByZero, "logb(0)", 1)
        ans = Decimal(self.adjusted())
        return ans._fix(context)

    def _islogical(self):
        "Return True if self is a logical operand.\n\n        For being logical, it must be a finite number with a sign of 0,\n        an exponent of 0, and a coefficient whose digits must all be\n        either 0 or 1.\n        "
        if (self._sign != 0) or (self._exp != 0):
            return False
        for dig in self._int:
            if dig not in "01":
                return False
        return True

    def _fill_logical(self, context, opa, opb):
        dif = context.prec - len(opa)
        if dif > 0:
            opa = ("0" * dif) + opa
        elif dif < 0:
            opa = opa[(-context.prec) :]
        dif = context.prec - len(opb)
        if dif > 0:
            opb = ("0" * dif) + opb
        elif dif < 0:
            opb = opb[(-context.prec) :]
        return (opa, opb)

    def logical_and(self, other, context=None):
        "Applies an 'and' operation between self and other's digits."
        if context is None:
            context = getcontext()
        other = _convert_other(other, raiseit=True)
        if (not self._islogical()) or (not other._islogical()):
            return context._raise_error(InvalidOperation)
        (opa, opb) = self._fill_logical(context, self._int, other._int)
        result = "".join([str((int(a) & int(b))) for (a, b) in zip(opa, opb)])
        return _dec_from_triple(0, (result.lstrip("0") or "0"), 0)

    def logical_invert(self, context=None):
        "Invert all its digits."
        if context is None:
            context = getcontext()
        return self.logical_xor(_dec_from_triple(0, ("1" * context.prec), 0), context)

    def logical_or(self, other, context=None):
        "Applies an 'or' operation between self and other's digits."
        if context is None:
            context = getcontext()
        other = _convert_other(other, raiseit=True)
        if (not self._islogical()) or (not other._islogical()):
            return context._raise_error(InvalidOperation)
        (opa, opb) = self._fill_logical(context, self._int, other._int)
        result = "".join([str((int(a) | int(b))) for (a, b) in zip(opa, opb)])
        return _dec_from_triple(0, (result.lstrip("0") or "0"), 0)

    def logical_xor(self, other, context=None):
        "Applies an 'xor' operation between self and other's digits."
        if context is None:
            context = getcontext()
        other = _convert_other(other, raiseit=True)
        if (not self._islogical()) or (not other._islogical()):
            return context._raise_error(InvalidOperation)
        (opa, opb) = self._fill_logical(context, self._int, other._int)
        result = "".join([str((int(a) ^ int(b))) for (a, b) in zip(opa, opb)])
        return _dec_from_triple(0, (result.lstrip("0") or "0"), 0)

    def max_mag(self, other, context=None):
        "Compares the values numerically with their sign ignored."
        other = _convert_other(other, raiseit=True)
        if context is None:
            context = getcontext()
        if self._is_special or other._is_special:
            sn = self._isnan()
            on = other._isnan()
            if sn or on:
                if (on == 1) and (sn == 0):
                    return self._fix(context)
                if (sn == 1) and (on == 0):
                    return other._fix(context)
                return self._check_nans(other, context)
        c = self.copy_abs()._cmp(other.copy_abs())
        if c == 0:
            c = self.compare_total(other)
        if c == (-1):
            ans = other
        else:
            ans = self
        return ans._fix(context)

    def min_mag(self, other, context=None):
        "Compares the values numerically with their sign ignored."
        other = _convert_other(other, raiseit=True)
        if context is None:
            context = getcontext()
        if self._is_special or other._is_special:
            sn = self._isnan()
            on = other._isnan()
            if sn or on:
                if (on == 1) and (sn == 0):
                    return self._fix(context)
                if (sn == 1) and (on == 0):
                    return other._fix(context)
                return self._check_nans(other, context)
        c = self.copy_abs()._cmp(other.copy_abs())
        if c == 0:
            c = self.compare_total(other)
        if c == (-1):
            ans = self
        else:
            ans = other
        return ans._fix(context)

    def next_minus(self, context=None):
        "Returns the largest representable number smaller than itself."
        if context is None:
            context = getcontext()
        ans = self._check_nans(context=context)
        if ans:
            return ans
        if self._isinfinity() == (-1):
            return _NegativeInfinity
        if self._isinfinity() == 1:
            return _dec_from_triple(0, ("9" * context.prec), context.Etop())
        context = context.copy()
        context._set_rounding(ROUND_FLOOR)
        context._ignore_all_flags()
        new_self = self._fix(context)
        if new_self != self:
            return new_self
        return self.__sub__(_dec_from_triple(0, "1", (context.Etiny() - 1)), context)

    def next_plus(self, context=None):
        "Returns the smallest representable number larger than itself."
        if context is None:
            context = getcontext()
        ans = self._check_nans(context=context)
        if ans:
            return ans
        if self._isinfinity() == 1:
            return _Infinity
        if self._isinfinity() == (-1):
            return _dec_from_triple(1, ("9" * context.prec), context.Etop())
        context = context.copy()
        context._set_rounding(ROUND_CEILING)
        context._ignore_all_flags()
        new_self = self._fix(context)
        if new_self != self:
            return new_self
        return self.__add__(_dec_from_triple(0, "1", (context.Etiny() - 1)), context)

    def next_toward(self, other, context=None):
        "Returns the number closest to self, in the direction towards other.\n\n        The result is the closest representable number to self\n        (excluding self) that is in the direction towards other,\n        unless both have the same value.  If the two operands are\n        numerically equal, then the result is a copy of self with the\n        sign set to be the same as the sign of other.\n        "
        other = _convert_other(other, raiseit=True)
        if context is None:
            context = getcontext()
        ans = self._check_nans(other, context)
        if ans:
            return ans
        comparison = self._cmp(other)
        if comparison == 0:
            return self.copy_sign(other)
        if comparison == (-1):
            ans = self.next_plus(context)
        else:
            ans = self.next_minus(context)
        if ans._isinfinity():
            context._raise_error(
                Overflow, "Infinite result from next_toward", ans._sign
            )
            context._raise_error(Inexact)
            context._raise_error(Rounded)
        elif ans.adjusted() < context.Emin:
            context._raise_error(Underflow)
            context._raise_error(Subnormal)
            context._raise_error(Inexact)
            context._raise_error(Rounded)
            if not ans:
                context._raise_error(Clamped)
        return ans

    def number_class(self, context=None):
        "Returns an indication of the class of self.\n\n        The class is one of the following strings:\n          sNaN\n          NaN\n          -Infinity\n          -Normal\n          -Subnormal\n          -Zero\n          +Zero\n          +Subnormal\n          +Normal\n          +Infinity\n        "
        if self.is_snan():
            return "sNaN"
        if self.is_qnan():
            return "NaN"
        inf = self._isinfinity()
        if inf == 1:
            return "+Infinity"
        if inf == (-1):
            return "-Infinity"
        if self.is_zero():
            if self._sign:
                return "-Zero"
            else:
                return "+Zero"
        if context is None:
            context = getcontext()
        if self.is_subnormal(context=context):
            if self._sign:
                return "-Subnormal"
            else:
                return "+Subnormal"
        if self._sign:
            return "-Normal"
        else:
            return "+Normal"

    def radix(self):
        "Just returns 10, as this is Decimal, :)"
        return Decimal(10)

    def rotate(self, other, context=None):
        "Returns a rotated copy of self, value-of-other times."
        if context is None:
            context = getcontext()
        other = _convert_other(other, raiseit=True)
        ans = self._check_nans(other, context)
        if ans:
            return ans
        if other._exp != 0:
            return context._raise_error(InvalidOperation)
        if not ((-context.prec) <= int(other) <= context.prec):
            return context._raise_error(InvalidOperation)
        if self._isinfinity():
            return Decimal(self)
        torot = int(other)
        rotdig = self._int
        topad = context.prec - len(rotdig)
        if topad > 0:
            rotdig = ("0" * topad) + rotdig
        elif topad < 0:
            rotdig = rotdig[(-topad):]
        rotated = rotdig[torot:] + rotdig[:torot]
        return _dec_from_triple(self._sign, (rotated.lstrip("0") or "0"), self._exp)

    def scaleb(self, other, context=None):
        "Returns self operand after adding the second value to its exp."
        if context is None:
            context = getcontext()
        other = _convert_other(other, raiseit=True)
        ans = self._check_nans(other, context)
        if ans:
            return ans
        if other._exp != 0:
            return context._raise_error(InvalidOperation)
        liminf = (-2) * (context.Emax + context.prec)
        limsup = 2 * (context.Emax + context.prec)
        if not (liminf <= int(other) <= limsup):
            return context._raise_error(InvalidOperation)
        if self._isinfinity():
            return Decimal(self)
        d = _dec_from_triple(self._sign, self._int, (self._exp + int(other)))
        d = d._fix(context)
        return d

    def shift(self, other, context=None):
        "Returns a shifted copy of self, value-of-other times."
        if context is None:
            context = getcontext()
        other = _convert_other(other, raiseit=True)
        ans = self._check_nans(other, context)
        if ans:
            return ans
        if other._exp != 0:
            return context._raise_error(InvalidOperation)
        if not ((-context.prec) <= int(other) <= context.prec):
            return context._raise_error(InvalidOperation)
        if self._isinfinity():
            return Decimal(self)
        torot = int(other)
        rotdig = self._int
        topad = context.prec - len(rotdig)
        if topad > 0:
            rotdig = ("0" * topad) + rotdig
        elif topad < 0:
            rotdig = rotdig[(-topad):]
        if torot < 0:
            shifted = rotdig[:torot]
        else:
            shifted = rotdig + ("0" * torot)
            shifted = shifted[(-context.prec) :]
        return _dec_from_triple(self._sign, (shifted.lstrip("0") or "0"), self._exp)

    def __reduce__(self):
        return (self.__class__, (str(self),))

    def __copy__(self):
        if type(self) is Decimal:
            return self
        return self.__class__(str(self))

    def __deepcopy__(self, memo):
        if type(self) is Decimal:
            return self
        return self.__class__(str(self))

    def __format__(self, specifier, context=None, _localeconv=None):
        "Format a Decimal instance according to the given specifier.\n\n        The specifier should be a standard format specifier, with the\n        form described in PEP 3101.  Formatting types 'e', 'E', 'f',\n        'F', 'g', 'G', 'n' and '%' are supported.  If the formatting\n        type is omitted it defaults to 'g' or 'G', depending on the\n        value of context.capitals.\n        "
        if context is None:
            context = getcontext()
        spec = _parse_format_specifier(specifier, _localeconv=_localeconv)
        if self._is_special:
            sign = _format_sign(self._sign, spec)
            body = str(self.copy_abs())
            if spec["type"] == "%":
                body += "%"
            return _format_align(sign, body, spec)
        if spec["type"] is None:
            spec["type"] = ["g", "G"][context.capitals]
        if spec["type"] == "%":
            self = _dec_from_triple(self._sign, self._int, (self._exp + 2))
        rounding = context.rounding
        precision = spec["precision"]
        if precision is not None:
            if spec["type"] in "eE":
                self = self._round((precision + 1), rounding)
            elif spec["type"] in "fF%":
                self = self._rescale((-precision), rounding)
            elif (spec["type"] in "gG") and (len(self._int) > precision):
                self = self._round(precision, rounding)
        if (not self) and (self._exp > 0) and (spec["type"] in "fF%"):
            self = self._rescale(0, rounding)
        leftdigits = self._exp + len(self._int)
        if spec["type"] in "eE":
            if (not self) and (precision is not None):
                dotplace = 1 - precision
            else:
                dotplace = 1
        elif spec["type"] in "fF%":
            dotplace = leftdigits
        elif spec["type"] in "gG":
            if (self._exp <= 0) and (leftdigits > (-6)):
                dotplace = leftdigits
            else:
                dotplace = 1
        if dotplace < 0:
            intpart = "0"
            fracpart = ("0" * (-dotplace)) + self._int
        elif dotplace > len(self._int):
            intpart = self._int + ("0" * (dotplace - len(self._int)))
            fracpart = ""
        else:
            intpart = self._int[:dotplace] or "0"
            fracpart = self._int[dotplace:]
        exp = leftdigits - dotplace
        return _format_number(self._sign, intpart, fracpart, exp, spec)


def _dec_from_triple(sign, coefficient, exponent, special=False):
    "Create a decimal instance directly, without any validation,\n    normalization (e.g. removal of leading zeros) or argument\n    conversion.\n\n    This function is for *internal use only*.\n    "
    self = object.__new__(Decimal)
    self._sign = sign
    self._int = coefficient
    self._exp = exponent
    self._is_special = special
    return self


_numbers.Number.register(Decimal)


class _ContextManager(object):
    "Context manager class to support localcontext().\n\n      Sets a copy of the supplied context in __enter__() and restores\n      the previous decimal context in __exit__()\n    "

    def __init__(self, new_context):
        self.new_context = new_context.copy()

    def __enter__(self):
        self.saved_context = getcontext()
        setcontext(self.new_context)
        return self.new_context

    def __exit__(self, t, v, tb):
        setcontext(self.saved_context)


class Context(object):
    "Contains the context for a Decimal instance.\n\n    Contains:\n    prec - precision (for use in rounding, division, square roots..)\n    rounding - rounding type (how you round)\n    traps - If traps[exception] = 1, then the exception is\n                    raised when it is caused.  Otherwise, a value is\n                    substituted in.\n    flags  - When an exception is caused, flags[exception] is set.\n             (Whether or not the trap_enabler is set)\n             Should be reset by user of Decimal instance.\n    Emin -   Minimum exponent\n    Emax -   Maximum exponent\n    capitals -      If 1, 1*10^1 is printed as 1E+1.\n                    If 0, printed as 1e1\n    clamp -  If 1, change exponents if too high (Default 0)\n    "

    def __init__(
        self,
        prec=None,
        rounding=None,
        Emin=None,
        Emax=None,
        capitals=None,
        clamp=None,
        flags=None,
        traps=None,
        _ignored_flags=None,
    ):
        try:
            dc = DefaultContext
        except NameError:
            pass
        self.prec = prec if (prec is not None) else dc.prec
        self.rounding = rounding if (rounding is not None) else dc.rounding
        self.Emin = Emin if (Emin is not None) else dc.Emin
        self.Emax = Emax if (Emax is not None) else dc.Emax
        self.capitals = capitals if (capitals is not None) else dc.capitals
        self.clamp = clamp if (clamp is not None) else dc.clamp
        if _ignored_flags is None:
            self._ignored_flags = []
        else:
            self._ignored_flags = _ignored_flags
        if traps is None:
            self.traps = dc.traps.copy()
        elif not isinstance(traps, dict):
            self.traps = dict(((s, int((s in traps))) for s in (_signals + traps)))
        else:
            self.traps = traps
        if flags is None:
            self.flags = dict.fromkeys(_signals, 0)
        elif not isinstance(flags, dict):
            self.flags = dict(((s, int((s in flags))) for s in (_signals + flags)))
        else:
            self.flags = flags

    def _set_integer_check(self, name, value, vmin, vmax):
        if not isinstance(value, int):
            raise TypeError(("%s must be an integer" % name))
        if vmin == "-inf":
            if value > vmax:
                raise ValueError(
                    ("%s must be in [%s, %d]. got: %s" % (name, vmin, vmax, value))
                )
        elif vmax == "inf":
            if value < vmin:
                raise ValueError(
                    ("%s must be in [%d, %s]. got: %s" % (name, vmin, vmax, value))
                )
        elif (value < vmin) or (value > vmax):
            raise ValueError(
                ("%s must be in [%d, %d]. got %s" % (name, vmin, vmax, value))
            )
        return object.__setattr__(self, name, value)

    def _set_signal_dict(self, name, d):
        if not isinstance(d, dict):
            raise TypeError(("%s must be a signal dict" % d))
        for key in d:
            if not (key in _signals):
                raise KeyError(("%s is not a valid signal dict" % d))
        for key in _signals:
            if not (key in d):
                raise KeyError(("%s is not a valid signal dict" % d))
        return object.__setattr__(self, name, d)

    def __setattr__(self, name, value):
        if name == "prec":
            return self._set_integer_check(name, value, 1, "inf")
        elif name == "Emin":
            return self._set_integer_check(name, value, "-inf", 0)
        elif name == "Emax":
            return self._set_integer_check(name, value, 0, "inf")
        elif name == "capitals":
            return self._set_integer_check(name, value, 0, 1)
        elif name == "clamp":
            return self._set_integer_check(name, value, 0, 1)
        elif name == "rounding":
            if not (value in _rounding_modes):
                raise TypeError(("%s: invalid rounding mode" % value))
            return object.__setattr__(self, name, value)
        elif (name == "flags") or (name == "traps"):
            return self._set_signal_dict(name, value)
        elif name == "_ignored_flags":
            return object.__setattr__(self, name, value)
        else:
            raise AttributeError(
                ("'decimal.Context' object has no attribute '%s'" % name)
            )

    def __delattr__(self, name):
        raise AttributeError(("%s cannot be deleted" % name))

    def __reduce__(self):
        flags = [sig for (sig, v) in self.flags.items() if v]
        traps = [sig for (sig, v) in self.traps.items() if v]
        return (
            self.__class__,
            (
                self.prec,
                self.rounding,
                self.Emin,
                self.Emax,
                self.capitals,
                self.clamp,
                flags,
                traps,
            ),
        )

    def __repr__(self):
        "Show the current context."
        s = []
        s.append(
            (
                "Context(prec=%(prec)d, rounding=%(rounding)s, Emin=%(Emin)d, Emax=%(Emax)d, capitals=%(capitals)d, clamp=%(clamp)d"
                % vars(self)
            )
        )
        names = [f.__name__ for (f, v) in self.flags.items() if v]
        s.append((("flags=[" + ", ".join(names)) + "]"))
        names = [t.__name__ for (t, v) in self.traps.items() if v]
        s.append((("traps=[" + ", ".join(names)) + "]"))
        return ", ".join(s) + ")"

    def clear_flags(self):
        "Reset all flags to zero"
        for flag in self.flags:
            self.flags[flag] = 0

    def clear_traps(self):
        "Reset all traps to zero"
        for flag in self.traps:
            self.traps[flag] = 0

    def _shallow_copy(self):
        "Returns a shallow copy from self."
        nc = Context(
            self.prec,
            self.rounding,
            self.Emin,
            self.Emax,
            self.capitals,
            self.clamp,
            self.flags,
            self.traps,
            self._ignored_flags,
        )
        return nc

    def copy(self):
        "Returns a deep copy from self."
        nc = Context(
            self.prec,
            self.rounding,
            self.Emin,
            self.Emax,
            self.capitals,
            self.clamp,
            self.flags.copy(),
            self.traps.copy(),
            self._ignored_flags,
        )
        return nc

    __copy__ = copy

    def _raise_error(self, condition, explanation=None, *args):
        "Handles an error\n\n        If the flag is in _ignored_flags, returns the default response.\n        Otherwise, it sets the flag, then, if the corresponding\n        trap_enabler is set, it reraises the exception.  Otherwise, it returns\n        the default value after setting the flag.\n        "
        error = _condition_map.get(condition, condition)
        if error in self._ignored_flags:
            return error().handle(self, *args)
        self.flags[error] = 1
        if not self.traps[error]:
            return condition().handle(self, *args)
        raise error(explanation)

    def _ignore_all_flags(self):
        "Ignore all flags, if they are raised"
        return self._ignore_flags(*_signals)

    def _ignore_flags(self, *flags):
        "Ignore the flags, if they are raised"
        self._ignored_flags = self._ignored_flags + list(flags)
        return list(flags)

    def _regard_flags(self, *flags):
        "Stop ignoring the flags, if they are raised"
        if flags and isinstance(flags[0], (tuple, list)):
            flags = flags[0]
        for flag in flags:
            self._ignored_flags.remove(flag)

    __hash__ = None

    def Etiny(self):
        "Returns Etiny (= Emin - prec + 1)"
        return int(((self.Emin - self.prec) + 1))

    def Etop(self):
        "Returns maximum exponent (= Emax - prec + 1)"
        return int(((self.Emax - self.prec) + 1))

    def _set_rounding(self, type):
        "Sets the rounding type.\n\n        Sets the rounding type, and returns the current (previous)\n        rounding type.  Often used like:\n\n        context = context.copy()\n        # so you don't change the calling context\n        # if an error occurs in the middle.\n        rounding = context._set_rounding(ROUND_UP)\n        val = self.__sub__(other, context=context)\n        context._set_rounding(rounding)\n\n        This will make it round up for that operation.\n        "
        rounding = self.rounding
        self.rounding = type
        return rounding

    def create_decimal(self, num="0"):
        "Creates a new Decimal instance but using self as context.\n\n        This method implements the to-number operation of the\n        IBM Decimal specification."
        if isinstance(num, str) and ((num != num.strip()) or ("_" in num)):
            return self._raise_error(
                ConversionSyntax,
                "trailing or leading whitespace and underscores are not permitted.",
            )
        d = Decimal(num, context=self)
        if d._isnan() and (len(d._int) > (self.prec - self.clamp)):
            return self._raise_error(
                ConversionSyntax, "diagnostic info too long in NaN"
            )
        return d._fix(self)

    def create_decimal_from_float(self, f):
        "Creates a new Decimal instance from a float but rounding using self\n        as the context.\n\n        >>> context = Context(prec=5, rounding=ROUND_DOWN)\n        >>> context.create_decimal_from_float(3.1415926535897932)\n        Decimal('3.1415')\n        >>> context = Context(prec=5, traps=[Inexact])\n        >>> context.create_decimal_from_float(3.1415926535897932)\n        Traceback (most recent call last):\n            ...\n        decimal.Inexact: None\n\n        "
        d = Decimal.from_float(f)
        return d._fix(self)

    def abs(self, a):
        "Returns the absolute value of the operand.\n\n        If the operand is negative, the result is the same as using the minus\n        operation on the operand.  Otherwise, the result is the same as using\n        the plus operation on the operand.\n\n        >>> ExtendedContext.abs(Decimal('2.1'))\n        Decimal('2.1')\n        >>> ExtendedContext.abs(Decimal('-100'))\n        Decimal('100')\n        >>> ExtendedContext.abs(Decimal('101.5'))\n        Decimal('101.5')\n        >>> ExtendedContext.abs(Decimal('-101.5'))\n        Decimal('101.5')\n        >>> ExtendedContext.abs(-1)\n        Decimal('1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.__abs__(context=self)

    def add(self, a, b):
        "Return the sum of the two operands.\n\n        >>> ExtendedContext.add(Decimal('12'), Decimal('7.00'))\n        Decimal('19.00')\n        >>> ExtendedContext.add(Decimal('1E+2'), Decimal('1.01E+4'))\n        Decimal('1.02E+4')\n        >>> ExtendedContext.add(1, Decimal(2))\n        Decimal('3')\n        >>> ExtendedContext.add(Decimal(8), 5)\n        Decimal('13')\n        >>> ExtendedContext.add(5, 5)\n        Decimal('10')\n        "
        a = _convert_other(a, raiseit=True)
        r = a.__add__(b, context=self)
        if r is NotImplemented:
            raise TypeError(("Unable to convert %s to Decimal" % b))
        else:
            return r

    def _apply(self, a):
        return str(a._fix(self))

    def canonical(self, a):
        "Returns the same Decimal object.\n\n        As we do not have different encodings for the same number, the\n        received object already is in its canonical form.\n\n        >>> ExtendedContext.canonical(Decimal('2.50'))\n        Decimal('2.50')\n        "
        if not isinstance(a, Decimal):
            raise TypeError("canonical requires a Decimal as an argument.")
        return a.canonical()

    def compare(self, a, b):
        "Compares values numerically.\n\n        If the signs of the operands differ, a value representing each operand\n        ('-1' if the operand is less than zero, '0' if the operand is zero or\n        negative zero, or '1' if the operand is greater than zero) is used in\n        place of that operand for the comparison instead of the actual\n        operand.\n\n        The comparison is then effected by subtracting the second operand from\n        the first and then returning a value according to the result of the\n        subtraction: '-1' if the result is less than zero, '0' if the result is\n        zero or negative zero, or '1' if the result is greater than zero.\n\n        >>> ExtendedContext.compare(Decimal('2.1'), Decimal('3'))\n        Decimal('-1')\n        >>> ExtendedContext.compare(Decimal('2.1'), Decimal('2.1'))\n        Decimal('0')\n        >>> ExtendedContext.compare(Decimal('2.1'), Decimal('2.10'))\n        Decimal('0')\n        >>> ExtendedContext.compare(Decimal('3'), Decimal('2.1'))\n        Decimal('1')\n        >>> ExtendedContext.compare(Decimal('2.1'), Decimal('-3'))\n        Decimal('1')\n        >>> ExtendedContext.compare(Decimal('-3'), Decimal('2.1'))\n        Decimal('-1')\n        >>> ExtendedContext.compare(1, 2)\n        Decimal('-1')\n        >>> ExtendedContext.compare(Decimal(1), 2)\n        Decimal('-1')\n        >>> ExtendedContext.compare(1, Decimal(2))\n        Decimal('-1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.compare(b, context=self)

    def compare_signal(self, a, b):
        "Compares the values of the two operands numerically.\n\n        It's pretty much like compare(), but all NaNs signal, with signaling\n        NaNs taking precedence over quiet NaNs.\n\n        >>> c = ExtendedContext\n        >>> c.compare_signal(Decimal('2.1'), Decimal('3'))\n        Decimal('-1')\n        >>> c.compare_signal(Decimal('2.1'), Decimal('2.1'))\n        Decimal('0')\n        >>> c.flags[InvalidOperation] = 0\n        >>> print(c.flags[InvalidOperation])\n        0\n        >>> c.compare_signal(Decimal('NaN'), Decimal('2.1'))\n        Decimal('NaN')\n        >>> print(c.flags[InvalidOperation])\n        1\n        >>> c.flags[InvalidOperation] = 0\n        >>> print(c.flags[InvalidOperation])\n        0\n        >>> c.compare_signal(Decimal('sNaN'), Decimal('2.1'))\n        Decimal('NaN')\n        >>> print(c.flags[InvalidOperation])\n        1\n        >>> c.compare_signal(-1, 2)\n        Decimal('-1')\n        >>> c.compare_signal(Decimal(-1), 2)\n        Decimal('-1')\n        >>> c.compare_signal(-1, Decimal(2))\n        Decimal('-1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.compare_signal(b, context=self)

    def compare_total(self, a, b):
        "Compares two operands using their abstract representation.\n\n        This is not like the standard compare, which use their numerical\n        value. Note that a total ordering is defined for all possible abstract\n        representations.\n\n        >>> ExtendedContext.compare_total(Decimal('12.73'), Decimal('127.9'))\n        Decimal('-1')\n        >>> ExtendedContext.compare_total(Decimal('-127'),  Decimal('12'))\n        Decimal('-1')\n        >>> ExtendedContext.compare_total(Decimal('12.30'), Decimal('12.3'))\n        Decimal('-1')\n        >>> ExtendedContext.compare_total(Decimal('12.30'), Decimal('12.30'))\n        Decimal('0')\n        >>> ExtendedContext.compare_total(Decimal('12.3'),  Decimal('12.300'))\n        Decimal('1')\n        >>> ExtendedContext.compare_total(Decimal('12.3'),  Decimal('NaN'))\n        Decimal('-1')\n        >>> ExtendedContext.compare_total(1, 2)\n        Decimal('-1')\n        >>> ExtendedContext.compare_total(Decimal(1), 2)\n        Decimal('-1')\n        >>> ExtendedContext.compare_total(1, Decimal(2))\n        Decimal('-1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.compare_total(b)

    def compare_total_mag(self, a, b):
        "Compares two operands using their abstract representation ignoring sign.\n\n        Like compare_total, but with operand's sign ignored and assumed to be 0.\n        "
        a = _convert_other(a, raiseit=True)
        return a.compare_total_mag(b)

    def copy_abs(self, a):
        "Returns a copy of the operand with the sign set to 0.\n\n        >>> ExtendedContext.copy_abs(Decimal('2.1'))\n        Decimal('2.1')\n        >>> ExtendedContext.copy_abs(Decimal('-100'))\n        Decimal('100')\n        >>> ExtendedContext.copy_abs(-1)\n        Decimal('1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.copy_abs()

    def copy_decimal(self, a):
        "Returns a copy of the decimal object.\n\n        >>> ExtendedContext.copy_decimal(Decimal('2.1'))\n        Decimal('2.1')\n        >>> ExtendedContext.copy_decimal(Decimal('-1.00'))\n        Decimal('-1.00')\n        >>> ExtendedContext.copy_decimal(1)\n        Decimal('1')\n        "
        a = _convert_other(a, raiseit=True)
        return Decimal(a)

    def copy_negate(self, a):
        "Returns a copy of the operand with the sign inverted.\n\n        >>> ExtendedContext.copy_negate(Decimal('101.5'))\n        Decimal('-101.5')\n        >>> ExtendedContext.copy_negate(Decimal('-101.5'))\n        Decimal('101.5')\n        >>> ExtendedContext.copy_negate(1)\n        Decimal('-1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.copy_negate()

    def copy_sign(self, a, b):
        "Copies the second operand's sign to the first one.\n\n        In detail, it returns a copy of the first operand with the sign\n        equal to the sign of the second operand.\n\n        >>> ExtendedContext.copy_sign(Decimal( '1.50'), Decimal('7.33'))\n        Decimal('1.50')\n        >>> ExtendedContext.copy_sign(Decimal('-1.50'), Decimal('7.33'))\n        Decimal('1.50')\n        >>> ExtendedContext.copy_sign(Decimal( '1.50'), Decimal('-7.33'))\n        Decimal('-1.50')\n        >>> ExtendedContext.copy_sign(Decimal('-1.50'), Decimal('-7.33'))\n        Decimal('-1.50')\n        >>> ExtendedContext.copy_sign(1, -2)\n        Decimal('-1')\n        >>> ExtendedContext.copy_sign(Decimal(1), -2)\n        Decimal('-1')\n        >>> ExtendedContext.copy_sign(1, Decimal(-2))\n        Decimal('-1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.copy_sign(b)

    def divide(self, a, b):
        "Decimal division in a specified context.\n\n        >>> ExtendedContext.divide(Decimal('1'), Decimal('3'))\n        Decimal('0.333333333')\n        >>> ExtendedContext.divide(Decimal('2'), Decimal('3'))\n        Decimal('0.666666667')\n        >>> ExtendedContext.divide(Decimal('5'), Decimal('2'))\n        Decimal('2.5')\n        >>> ExtendedContext.divide(Decimal('1'), Decimal('10'))\n        Decimal('0.1')\n        >>> ExtendedContext.divide(Decimal('12'), Decimal('12'))\n        Decimal('1')\n        >>> ExtendedContext.divide(Decimal('8.00'), Decimal('2'))\n        Decimal('4.00')\n        >>> ExtendedContext.divide(Decimal('2.400'), Decimal('2.0'))\n        Decimal('1.20')\n        >>> ExtendedContext.divide(Decimal('1000'), Decimal('100'))\n        Decimal('10')\n        >>> ExtendedContext.divide(Decimal('1000'), Decimal('1'))\n        Decimal('1000')\n        >>> ExtendedContext.divide(Decimal('2.40E+6'), Decimal('2'))\n        Decimal('1.20E+6')\n        >>> ExtendedContext.divide(5, 5)\n        Decimal('1')\n        >>> ExtendedContext.divide(Decimal(5), 5)\n        Decimal('1')\n        >>> ExtendedContext.divide(5, Decimal(5))\n        Decimal('1')\n        "
        a = _convert_other(a, raiseit=True)
        r = a.__truediv__(b, context=self)
        if r is NotImplemented:
            raise TypeError(("Unable to convert %s to Decimal" % b))
        else:
            return r

    def divide_int(self, a, b):
        "Divides two numbers and returns the integer part of the result.\n\n        >>> ExtendedContext.divide_int(Decimal('2'), Decimal('3'))\n        Decimal('0')\n        >>> ExtendedContext.divide_int(Decimal('10'), Decimal('3'))\n        Decimal('3')\n        >>> ExtendedContext.divide_int(Decimal('1'), Decimal('0.3'))\n        Decimal('3')\n        >>> ExtendedContext.divide_int(10, 3)\n        Decimal('3')\n        >>> ExtendedContext.divide_int(Decimal(10), 3)\n        Decimal('3')\n        >>> ExtendedContext.divide_int(10, Decimal(3))\n        Decimal('3')\n        "
        a = _convert_other(a, raiseit=True)
        r = a.__floordiv__(b, context=self)
        if r is NotImplemented:
            raise TypeError(("Unable to convert %s to Decimal" % b))
        else:
            return r

    def divmod(self, a, b):
        "Return (a // b, a % b).\n\n        >>> ExtendedContext.divmod(Decimal(8), Decimal(3))\n        (Decimal('2'), Decimal('2'))\n        >>> ExtendedContext.divmod(Decimal(8), Decimal(4))\n        (Decimal('2'), Decimal('0'))\n        >>> ExtendedContext.divmod(8, 4)\n        (Decimal('2'), Decimal('0'))\n        >>> ExtendedContext.divmod(Decimal(8), 4)\n        (Decimal('2'), Decimal('0'))\n        >>> ExtendedContext.divmod(8, Decimal(4))\n        (Decimal('2'), Decimal('0'))\n        "
        a = _convert_other(a, raiseit=True)
        r = a.__divmod__(b, context=self)
        if r is NotImplemented:
            raise TypeError(("Unable to convert %s to Decimal" % b))
        else:
            return r

    def exp(self, a):
        "Returns e ** a.\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> c.exp(Decimal('-Infinity'))\n        Decimal('0')\n        >>> c.exp(Decimal('-1'))\n        Decimal('0.367879441')\n        >>> c.exp(Decimal('0'))\n        Decimal('1')\n        >>> c.exp(Decimal('1'))\n        Decimal('2.71828183')\n        >>> c.exp(Decimal('0.693147181'))\n        Decimal('2.00000000')\n        >>> c.exp(Decimal('+Infinity'))\n        Decimal('Infinity')\n        >>> c.exp(10)\n        Decimal('22026.4658')\n        "
        a = _convert_other(a, raiseit=True)
        return a.exp(context=self)

    def fma(self, a, b, c):
        "Returns a multiplied by b, plus c.\n\n        The first two operands are multiplied together, using multiply,\n        the third operand is then added to the result of that\n        multiplication, using add, all with only one final rounding.\n\n        >>> ExtendedContext.fma(Decimal('3'), Decimal('5'), Decimal('7'))\n        Decimal('22')\n        >>> ExtendedContext.fma(Decimal('3'), Decimal('-5'), Decimal('7'))\n        Decimal('-8')\n        >>> ExtendedContext.fma(Decimal('888565290'), Decimal('1557.96930'), Decimal('-86087.7578'))\n        Decimal('1.38435736E+12')\n        >>> ExtendedContext.fma(1, 3, 4)\n        Decimal('7')\n        >>> ExtendedContext.fma(1, Decimal(3), 4)\n        Decimal('7')\n        >>> ExtendedContext.fma(1, 3, Decimal(4))\n        Decimal('7')\n        "
        a = _convert_other(a, raiseit=True)
        return a.fma(b, c, context=self)

    def is_canonical(self, a):
        "Return True if the operand is canonical; otherwise return False.\n\n        Currently, the encoding of a Decimal instance is always\n        canonical, so this method returns True for any Decimal.\n\n        >>> ExtendedContext.is_canonical(Decimal('2.50'))\n        True\n        "
        if not isinstance(a, Decimal):
            raise TypeError("is_canonical requires a Decimal as an argument.")
        return a.is_canonical()

    def is_finite(self, a):
        "Return True if the operand is finite; otherwise return False.\n\n        A Decimal instance is considered finite if it is neither\n        infinite nor a NaN.\n\n        >>> ExtendedContext.is_finite(Decimal('2.50'))\n        True\n        >>> ExtendedContext.is_finite(Decimal('-0.3'))\n        True\n        >>> ExtendedContext.is_finite(Decimal('0'))\n        True\n        >>> ExtendedContext.is_finite(Decimal('Inf'))\n        False\n        >>> ExtendedContext.is_finite(Decimal('NaN'))\n        False\n        >>> ExtendedContext.is_finite(1)\n        True\n        "
        a = _convert_other(a, raiseit=True)
        return a.is_finite()

    def is_infinite(self, a):
        "Return True if the operand is infinite; otherwise return False.\n\n        >>> ExtendedContext.is_infinite(Decimal('2.50'))\n        False\n        >>> ExtendedContext.is_infinite(Decimal('-Inf'))\n        True\n        >>> ExtendedContext.is_infinite(Decimal('NaN'))\n        False\n        >>> ExtendedContext.is_infinite(1)\n        False\n        "
        a = _convert_other(a, raiseit=True)
        return a.is_infinite()

    def is_nan(self, a):
        "Return True if the operand is a qNaN or sNaN;\n        otherwise return False.\n\n        >>> ExtendedContext.is_nan(Decimal('2.50'))\n        False\n        >>> ExtendedContext.is_nan(Decimal('NaN'))\n        True\n        >>> ExtendedContext.is_nan(Decimal('-sNaN'))\n        True\n        >>> ExtendedContext.is_nan(1)\n        False\n        "
        a = _convert_other(a, raiseit=True)
        return a.is_nan()

    def is_normal(self, a):
        "Return True if the operand is a normal number;\n        otherwise return False.\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> c.is_normal(Decimal('2.50'))\n        True\n        >>> c.is_normal(Decimal('0.1E-999'))\n        False\n        >>> c.is_normal(Decimal('0.00'))\n        False\n        >>> c.is_normal(Decimal('-Inf'))\n        False\n        >>> c.is_normal(Decimal('NaN'))\n        False\n        >>> c.is_normal(1)\n        True\n        "
        a = _convert_other(a, raiseit=True)
        return a.is_normal(context=self)

    def is_qnan(self, a):
        "Return True if the operand is a quiet NaN; otherwise return False.\n\n        >>> ExtendedContext.is_qnan(Decimal('2.50'))\n        False\n        >>> ExtendedContext.is_qnan(Decimal('NaN'))\n        True\n        >>> ExtendedContext.is_qnan(Decimal('sNaN'))\n        False\n        >>> ExtendedContext.is_qnan(1)\n        False\n        "
        a = _convert_other(a, raiseit=True)
        return a.is_qnan()

    def is_signed(self, a):
        "Return True if the operand is negative; otherwise return False.\n\n        >>> ExtendedContext.is_signed(Decimal('2.50'))\n        False\n        >>> ExtendedContext.is_signed(Decimal('-12'))\n        True\n        >>> ExtendedContext.is_signed(Decimal('-0'))\n        True\n        >>> ExtendedContext.is_signed(8)\n        False\n        >>> ExtendedContext.is_signed(-8)\n        True\n        "
        a = _convert_other(a, raiseit=True)
        return a.is_signed()

    def is_snan(self, a):
        "Return True if the operand is a signaling NaN;\n        otherwise return False.\n\n        >>> ExtendedContext.is_snan(Decimal('2.50'))\n        False\n        >>> ExtendedContext.is_snan(Decimal('NaN'))\n        False\n        >>> ExtendedContext.is_snan(Decimal('sNaN'))\n        True\n        >>> ExtendedContext.is_snan(1)\n        False\n        "
        a = _convert_other(a, raiseit=True)
        return a.is_snan()

    def is_subnormal(self, a):
        "Return True if the operand is subnormal; otherwise return False.\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> c.is_subnormal(Decimal('2.50'))\n        False\n        >>> c.is_subnormal(Decimal('0.1E-999'))\n        True\n        >>> c.is_subnormal(Decimal('0.00'))\n        False\n        >>> c.is_subnormal(Decimal('-Inf'))\n        False\n        >>> c.is_subnormal(Decimal('NaN'))\n        False\n        >>> c.is_subnormal(1)\n        False\n        "
        a = _convert_other(a, raiseit=True)
        return a.is_subnormal(context=self)

    def is_zero(self, a):
        "Return True if the operand is a zero; otherwise return False.\n\n        >>> ExtendedContext.is_zero(Decimal('0'))\n        True\n        >>> ExtendedContext.is_zero(Decimal('2.50'))\n        False\n        >>> ExtendedContext.is_zero(Decimal('-0E+2'))\n        True\n        >>> ExtendedContext.is_zero(1)\n        False\n        >>> ExtendedContext.is_zero(0)\n        True\n        "
        a = _convert_other(a, raiseit=True)
        return a.is_zero()

    def ln(self, a):
        "Returns the natural (base e) logarithm of the operand.\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> c.ln(Decimal('0'))\n        Decimal('-Infinity')\n        >>> c.ln(Decimal('1.000'))\n        Decimal('0')\n        >>> c.ln(Decimal('2.71828183'))\n        Decimal('1.00000000')\n        >>> c.ln(Decimal('10'))\n        Decimal('2.30258509')\n        >>> c.ln(Decimal('+Infinity'))\n        Decimal('Infinity')\n        >>> c.ln(1)\n        Decimal('0')\n        "
        a = _convert_other(a, raiseit=True)
        return a.ln(context=self)

    def log10(self, a):
        "Returns the base 10 logarithm of the operand.\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> c.log10(Decimal('0'))\n        Decimal('-Infinity')\n        >>> c.log10(Decimal('0.001'))\n        Decimal('-3')\n        >>> c.log10(Decimal('1.000'))\n        Decimal('0')\n        >>> c.log10(Decimal('2'))\n        Decimal('0.301029996')\n        >>> c.log10(Decimal('10'))\n        Decimal('1')\n        >>> c.log10(Decimal('70'))\n        Decimal('1.84509804')\n        >>> c.log10(Decimal('+Infinity'))\n        Decimal('Infinity')\n        >>> c.log10(0)\n        Decimal('-Infinity')\n        >>> c.log10(1)\n        Decimal('0')\n        "
        a = _convert_other(a, raiseit=True)
        return a.log10(context=self)

    def logb(self, a):
        " Returns the exponent of the magnitude of the operand's MSD.\n\n        The result is the integer which is the exponent of the magnitude\n        of the most significant digit of the operand (as though the\n        operand were truncated to a single digit while maintaining the\n        value of that digit and without limiting the resulting exponent).\n\n        >>> ExtendedContext.logb(Decimal('250'))\n        Decimal('2')\n        >>> ExtendedContext.logb(Decimal('2.50'))\n        Decimal('0')\n        >>> ExtendedContext.logb(Decimal('0.03'))\n        Decimal('-2')\n        >>> ExtendedContext.logb(Decimal('0'))\n        Decimal('-Infinity')\n        >>> ExtendedContext.logb(1)\n        Decimal('0')\n        >>> ExtendedContext.logb(10)\n        Decimal('1')\n        >>> ExtendedContext.logb(100)\n        Decimal('2')\n        "
        a = _convert_other(a, raiseit=True)
        return a.logb(context=self)

    def logical_and(self, a, b):
        "Applies the logical operation 'and' between each operand's digits.\n\n        The operands must be both logical numbers.\n\n        >>> ExtendedContext.logical_and(Decimal('0'), Decimal('0'))\n        Decimal('0')\n        >>> ExtendedContext.logical_and(Decimal('0'), Decimal('1'))\n        Decimal('0')\n        >>> ExtendedContext.logical_and(Decimal('1'), Decimal('0'))\n        Decimal('0')\n        >>> ExtendedContext.logical_and(Decimal('1'), Decimal('1'))\n        Decimal('1')\n        >>> ExtendedContext.logical_and(Decimal('1100'), Decimal('1010'))\n        Decimal('1000')\n        >>> ExtendedContext.logical_and(Decimal('1111'), Decimal('10'))\n        Decimal('10')\n        >>> ExtendedContext.logical_and(110, 1101)\n        Decimal('100')\n        >>> ExtendedContext.logical_and(Decimal(110), 1101)\n        Decimal('100')\n        >>> ExtendedContext.logical_and(110, Decimal(1101))\n        Decimal('100')\n        "
        a = _convert_other(a, raiseit=True)
        return a.logical_and(b, context=self)

    def logical_invert(self, a):
        "Invert all the digits in the operand.\n\n        The operand must be a logical number.\n\n        >>> ExtendedContext.logical_invert(Decimal('0'))\n        Decimal('111111111')\n        >>> ExtendedContext.logical_invert(Decimal('1'))\n        Decimal('111111110')\n        >>> ExtendedContext.logical_invert(Decimal('111111111'))\n        Decimal('0')\n        >>> ExtendedContext.logical_invert(Decimal('101010101'))\n        Decimal('10101010')\n        >>> ExtendedContext.logical_invert(1101)\n        Decimal('111110010')\n        "
        a = _convert_other(a, raiseit=True)
        return a.logical_invert(context=self)

    def logical_or(self, a, b):
        "Applies the logical operation 'or' between each operand's digits.\n\n        The operands must be both logical numbers.\n\n        >>> ExtendedContext.logical_or(Decimal('0'), Decimal('0'))\n        Decimal('0')\n        >>> ExtendedContext.logical_or(Decimal('0'), Decimal('1'))\n        Decimal('1')\n        >>> ExtendedContext.logical_or(Decimal('1'), Decimal('0'))\n        Decimal('1')\n        >>> ExtendedContext.logical_or(Decimal('1'), Decimal('1'))\n        Decimal('1')\n        >>> ExtendedContext.logical_or(Decimal('1100'), Decimal('1010'))\n        Decimal('1110')\n        >>> ExtendedContext.logical_or(Decimal('1110'), Decimal('10'))\n        Decimal('1110')\n        >>> ExtendedContext.logical_or(110, 1101)\n        Decimal('1111')\n        >>> ExtendedContext.logical_or(Decimal(110), 1101)\n        Decimal('1111')\n        >>> ExtendedContext.logical_or(110, Decimal(1101))\n        Decimal('1111')\n        "
        a = _convert_other(a, raiseit=True)
        return a.logical_or(b, context=self)

    def logical_xor(self, a, b):
        "Applies the logical operation 'xor' between each operand's digits.\n\n        The operands must be both logical numbers.\n\n        >>> ExtendedContext.logical_xor(Decimal('0'), Decimal('0'))\n        Decimal('0')\n        >>> ExtendedContext.logical_xor(Decimal('0'), Decimal('1'))\n        Decimal('1')\n        >>> ExtendedContext.logical_xor(Decimal('1'), Decimal('0'))\n        Decimal('1')\n        >>> ExtendedContext.logical_xor(Decimal('1'), Decimal('1'))\n        Decimal('0')\n        >>> ExtendedContext.logical_xor(Decimal('1100'), Decimal('1010'))\n        Decimal('110')\n        >>> ExtendedContext.logical_xor(Decimal('1111'), Decimal('10'))\n        Decimal('1101')\n        >>> ExtendedContext.logical_xor(110, 1101)\n        Decimal('1011')\n        >>> ExtendedContext.logical_xor(Decimal(110), 1101)\n        Decimal('1011')\n        >>> ExtendedContext.logical_xor(110, Decimal(1101))\n        Decimal('1011')\n        "
        a = _convert_other(a, raiseit=True)
        return a.logical_xor(b, context=self)

    def max(self, a, b):
        "max compares two values numerically and returns the maximum.\n\n        If either operand is a NaN then the general rules apply.\n        Otherwise, the operands are compared as though by the compare\n        operation.  If they are numerically equal then the left-hand operand\n        is chosen as the result.  Otherwise the maximum (closer to positive\n        infinity) of the two operands is chosen as the result.\n\n        >>> ExtendedContext.max(Decimal('3'), Decimal('2'))\n        Decimal('3')\n        >>> ExtendedContext.max(Decimal('-10'), Decimal('3'))\n        Decimal('3')\n        >>> ExtendedContext.max(Decimal('1.0'), Decimal('1'))\n        Decimal('1')\n        >>> ExtendedContext.max(Decimal('7'), Decimal('NaN'))\n        Decimal('7')\n        >>> ExtendedContext.max(1, 2)\n        Decimal('2')\n        >>> ExtendedContext.max(Decimal(1), 2)\n        Decimal('2')\n        >>> ExtendedContext.max(1, Decimal(2))\n        Decimal('2')\n        "
        a = _convert_other(a, raiseit=True)
        return a.max(b, context=self)

    def max_mag(self, a, b):
        "Compares the values numerically with their sign ignored.\n\n        >>> ExtendedContext.max_mag(Decimal('7'), Decimal('NaN'))\n        Decimal('7')\n        >>> ExtendedContext.max_mag(Decimal('7'), Decimal('-10'))\n        Decimal('-10')\n        >>> ExtendedContext.max_mag(1, -2)\n        Decimal('-2')\n        >>> ExtendedContext.max_mag(Decimal(1), -2)\n        Decimal('-2')\n        >>> ExtendedContext.max_mag(1, Decimal(-2))\n        Decimal('-2')\n        "
        a = _convert_other(a, raiseit=True)
        return a.max_mag(b, context=self)

    def min(self, a, b):
        "min compares two values numerically and returns the minimum.\n\n        If either operand is a NaN then the general rules apply.\n        Otherwise, the operands are compared as though by the compare\n        operation.  If they are numerically equal then the left-hand operand\n        is chosen as the result.  Otherwise the minimum (closer to negative\n        infinity) of the two operands is chosen as the result.\n\n        >>> ExtendedContext.min(Decimal('3'), Decimal('2'))\n        Decimal('2')\n        >>> ExtendedContext.min(Decimal('-10'), Decimal('3'))\n        Decimal('-10')\n        >>> ExtendedContext.min(Decimal('1.0'), Decimal('1'))\n        Decimal('1.0')\n        >>> ExtendedContext.min(Decimal('7'), Decimal('NaN'))\n        Decimal('7')\n        >>> ExtendedContext.min(1, 2)\n        Decimal('1')\n        >>> ExtendedContext.min(Decimal(1), 2)\n        Decimal('1')\n        >>> ExtendedContext.min(1, Decimal(29))\n        Decimal('1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.min(b, context=self)

    def min_mag(self, a, b):
        "Compares the values numerically with their sign ignored.\n\n        >>> ExtendedContext.min_mag(Decimal('3'), Decimal('-2'))\n        Decimal('-2')\n        >>> ExtendedContext.min_mag(Decimal('-3'), Decimal('NaN'))\n        Decimal('-3')\n        >>> ExtendedContext.min_mag(1, -2)\n        Decimal('1')\n        >>> ExtendedContext.min_mag(Decimal(1), -2)\n        Decimal('1')\n        >>> ExtendedContext.min_mag(1, Decimal(-2))\n        Decimal('1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.min_mag(b, context=self)

    def minus(self, a):
        "Minus corresponds to unary prefix minus in Python.\n\n        The operation is evaluated using the same rules as subtract; the\n        operation minus(a) is calculated as subtract('0', a) where the '0'\n        has the same exponent as the operand.\n\n        >>> ExtendedContext.minus(Decimal('1.3'))\n        Decimal('-1.3')\n        >>> ExtendedContext.minus(Decimal('-1.3'))\n        Decimal('1.3')\n        >>> ExtendedContext.minus(1)\n        Decimal('-1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.__neg__(context=self)

    def multiply(self, a, b):
        "multiply multiplies two operands.\n\n        If either operand is a special value then the general rules apply.\n        Otherwise, the operands are multiplied together\n        ('long multiplication'), resulting in a number which may be as long as\n        the sum of the lengths of the two operands.\n\n        >>> ExtendedContext.multiply(Decimal('1.20'), Decimal('3'))\n        Decimal('3.60')\n        >>> ExtendedContext.multiply(Decimal('7'), Decimal('3'))\n        Decimal('21')\n        >>> ExtendedContext.multiply(Decimal('0.9'), Decimal('0.8'))\n        Decimal('0.72')\n        >>> ExtendedContext.multiply(Decimal('0.9'), Decimal('-0'))\n        Decimal('-0.0')\n        >>> ExtendedContext.multiply(Decimal('654321'), Decimal('654321'))\n        Decimal('4.28135971E+11')\n        >>> ExtendedContext.multiply(7, 7)\n        Decimal('49')\n        >>> ExtendedContext.multiply(Decimal(7), 7)\n        Decimal('49')\n        >>> ExtendedContext.multiply(7, Decimal(7))\n        Decimal('49')\n        "
        a = _convert_other(a, raiseit=True)
        r = a.__mul__(b, context=self)
        if r is NotImplemented:
            raise TypeError(("Unable to convert %s to Decimal" % b))
        else:
            return r

    def next_minus(self, a):
        "Returns the largest representable number smaller than a.\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> ExtendedContext.next_minus(Decimal('1'))\n        Decimal('0.999999999')\n        >>> c.next_minus(Decimal('1E-1007'))\n        Decimal('0E-1007')\n        >>> ExtendedContext.next_minus(Decimal('-1.00000003'))\n        Decimal('-1.00000004')\n        >>> c.next_minus(Decimal('Infinity'))\n        Decimal('9.99999999E+999')\n        >>> c.next_minus(1)\n        Decimal('0.999999999')\n        "
        a = _convert_other(a, raiseit=True)
        return a.next_minus(context=self)

    def next_plus(self, a):
        "Returns the smallest representable number larger than a.\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> ExtendedContext.next_plus(Decimal('1'))\n        Decimal('1.00000001')\n        >>> c.next_plus(Decimal('-1E-1007'))\n        Decimal('-0E-1007')\n        >>> ExtendedContext.next_plus(Decimal('-1.00000003'))\n        Decimal('-1.00000002')\n        >>> c.next_plus(Decimal('-Infinity'))\n        Decimal('-9.99999999E+999')\n        >>> c.next_plus(1)\n        Decimal('1.00000001')\n        "
        a = _convert_other(a, raiseit=True)
        return a.next_plus(context=self)

    def next_toward(self, a, b):
        "Returns the number closest to a, in direction towards b.\n\n        The result is the closest representable number from the first\n        operand (but not the first operand) that is in the direction\n        towards the second operand, unless the operands have the same\n        value.\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> c.next_toward(Decimal('1'), Decimal('2'))\n        Decimal('1.00000001')\n        >>> c.next_toward(Decimal('-1E-1007'), Decimal('1'))\n        Decimal('-0E-1007')\n        >>> c.next_toward(Decimal('-1.00000003'), Decimal('0'))\n        Decimal('-1.00000002')\n        >>> c.next_toward(Decimal('1'), Decimal('0'))\n        Decimal('0.999999999')\n        >>> c.next_toward(Decimal('1E-1007'), Decimal('-100'))\n        Decimal('0E-1007')\n        >>> c.next_toward(Decimal('-1.00000003'), Decimal('-10'))\n        Decimal('-1.00000004')\n        >>> c.next_toward(Decimal('0.00'), Decimal('-0.0000'))\n        Decimal('-0.00')\n        >>> c.next_toward(0, 1)\n        Decimal('1E-1007')\n        >>> c.next_toward(Decimal(0), 1)\n        Decimal('1E-1007')\n        >>> c.next_toward(0, Decimal(1))\n        Decimal('1E-1007')\n        "
        a = _convert_other(a, raiseit=True)
        return a.next_toward(b, context=self)

    def normalize(self, a):
        "normalize reduces an operand to its simplest form.\n\n        Essentially a plus operation with all trailing zeros removed from the\n        result.\n\n        >>> ExtendedContext.normalize(Decimal('2.1'))\n        Decimal('2.1')\n        >>> ExtendedContext.normalize(Decimal('-2.0'))\n        Decimal('-2')\n        >>> ExtendedContext.normalize(Decimal('1.200'))\n        Decimal('1.2')\n        >>> ExtendedContext.normalize(Decimal('-120'))\n        Decimal('-1.2E+2')\n        >>> ExtendedContext.normalize(Decimal('120.00'))\n        Decimal('1.2E+2')\n        >>> ExtendedContext.normalize(Decimal('0.00'))\n        Decimal('0')\n        >>> ExtendedContext.normalize(6)\n        Decimal('6')\n        "
        a = _convert_other(a, raiseit=True)
        return a.normalize(context=self)

    def number_class(self, a):
        "Returns an indication of the class of the operand.\n\n        The class is one of the following strings:\n          -sNaN\n          -NaN\n          -Infinity\n          -Normal\n          -Subnormal\n          -Zero\n          +Zero\n          +Subnormal\n          +Normal\n          +Infinity\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> c.number_class(Decimal('Infinity'))\n        '+Infinity'\n        >>> c.number_class(Decimal('1E-10'))\n        '+Normal'\n        >>> c.number_class(Decimal('2.50'))\n        '+Normal'\n        >>> c.number_class(Decimal('0.1E-999'))\n        '+Subnormal'\n        >>> c.number_class(Decimal('0'))\n        '+Zero'\n        >>> c.number_class(Decimal('-0'))\n        '-Zero'\n        >>> c.number_class(Decimal('-0.1E-999'))\n        '-Subnormal'\n        >>> c.number_class(Decimal('-1E-10'))\n        '-Normal'\n        >>> c.number_class(Decimal('-2.50'))\n        '-Normal'\n        >>> c.number_class(Decimal('-Infinity'))\n        '-Infinity'\n        >>> c.number_class(Decimal('NaN'))\n        'NaN'\n        >>> c.number_class(Decimal('-NaN'))\n        'NaN'\n        >>> c.number_class(Decimal('sNaN'))\n        'sNaN'\n        >>> c.number_class(123)\n        '+Normal'\n        "
        a = _convert_other(a, raiseit=True)
        return a.number_class(context=self)

    def plus(self, a):
        "Plus corresponds to unary prefix plus in Python.\n\n        The operation is evaluated using the same rules as add; the\n        operation plus(a) is calculated as add('0', a) where the '0'\n        has the same exponent as the operand.\n\n        >>> ExtendedContext.plus(Decimal('1.3'))\n        Decimal('1.3')\n        >>> ExtendedContext.plus(Decimal('-1.3'))\n        Decimal('-1.3')\n        >>> ExtendedContext.plus(-1)\n        Decimal('-1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.__pos__(context=self)

    def power(self, a, b, modulo=None):
        "Raises a to the power of b, to modulo if given.\n\n        With two arguments, compute a**b.  If a is negative then b\n        must be integral.  The result will be inexact unless b is\n        integral and the result is finite and can be expressed exactly\n        in 'precision' digits.\n\n        With three arguments, compute (a**b) % modulo.  For the\n        three argument form, the following restrictions on the\n        arguments hold:\n\n         - all three arguments must be integral\n         - b must be nonnegative\n         - at least one of a or b must be nonzero\n         - modulo must be nonzero and have at most 'precision' digits\n\n        The result of pow(a, b, modulo) is identical to the result\n        that would be obtained by computing (a**b) % modulo with\n        unbounded precision, but is computed more efficiently.  It is\n        always exact.\n\n        >>> c = ExtendedContext.copy()\n        >>> c.Emin = -999\n        >>> c.Emax = 999\n        >>> c.power(Decimal('2'), Decimal('3'))\n        Decimal('8')\n        >>> c.power(Decimal('-2'), Decimal('3'))\n        Decimal('-8')\n        >>> c.power(Decimal('2'), Decimal('-3'))\n        Decimal('0.125')\n        >>> c.power(Decimal('1.7'), Decimal('8'))\n        Decimal('69.7575744')\n        >>> c.power(Decimal('10'), Decimal('0.301029996'))\n        Decimal('2.00000000')\n        >>> c.power(Decimal('Infinity'), Decimal('-1'))\n        Decimal('0')\n        >>> c.power(Decimal('Infinity'), Decimal('0'))\n        Decimal('1')\n        >>> c.power(Decimal('Infinity'), Decimal('1'))\n        Decimal('Infinity')\n        >>> c.power(Decimal('-Infinity'), Decimal('-1'))\n        Decimal('-0')\n        >>> c.power(Decimal('-Infinity'), Decimal('0'))\n        Decimal('1')\n        >>> c.power(Decimal('-Infinity'), Decimal('1'))\n        Decimal('-Infinity')\n        >>> c.power(Decimal('-Infinity'), Decimal('2'))\n        Decimal('Infinity')\n        >>> c.power(Decimal('0'), Decimal('0'))\n        Decimal('NaN')\n\n        >>> c.power(Decimal('3'), Decimal('7'), Decimal('16'))\n        Decimal('11')\n        >>> c.power(Decimal('-3'), Decimal('7'), Decimal('16'))\n        Decimal('-11')\n        >>> c.power(Decimal('-3'), Decimal('8'), Decimal('16'))\n        Decimal('1')\n        >>> c.power(Decimal('3'), Decimal('7'), Decimal('-16'))\n        Decimal('11')\n        >>> c.power(Decimal('23E12345'), Decimal('67E189'), Decimal('123456789'))\n        Decimal('11729830')\n        >>> c.power(Decimal('-0'), Decimal('17'), Decimal('1729'))\n        Decimal('-0')\n        >>> c.power(Decimal('-23'), Decimal('0'), Decimal('65537'))\n        Decimal('1')\n        >>> ExtendedContext.power(7, 7)\n        Decimal('823543')\n        >>> ExtendedContext.power(Decimal(7), 7)\n        Decimal('823543')\n        >>> ExtendedContext.power(7, Decimal(7), 2)\n        Decimal('1')\n        "
        a = _convert_other(a, raiseit=True)
        r = a.__pow__(b, modulo, context=self)
        if r is NotImplemented:
            raise TypeError(("Unable to convert %s to Decimal" % b))
        else:
            return r

    def quantize(self, a, b):
        "Returns a value equal to 'a' (rounded), having the exponent of 'b'.\n\n        The coefficient of the result is derived from that of the left-hand\n        operand.  It may be rounded using the current rounding setting (if the\n        exponent is being increased), multiplied by a positive power of ten (if\n        the exponent is being decreased), or is unchanged (if the exponent is\n        already equal to that of the right-hand operand).\n\n        Unlike other operations, if the length of the coefficient after the\n        quantize operation would be greater than precision then an Invalid\n        operation condition is raised.  This guarantees that, unless there is\n        an error condition, the exponent of the result of a quantize is always\n        equal to that of the right-hand operand.\n\n        Also unlike other operations, quantize will never raise Underflow, even\n        if the result is subnormal and inexact.\n\n        >>> ExtendedContext.quantize(Decimal('2.17'), Decimal('0.001'))\n        Decimal('2.170')\n        >>> ExtendedContext.quantize(Decimal('2.17'), Decimal('0.01'))\n        Decimal('2.17')\n        >>> ExtendedContext.quantize(Decimal('2.17'), Decimal('0.1'))\n        Decimal('2.2')\n        >>> ExtendedContext.quantize(Decimal('2.17'), Decimal('1e+0'))\n        Decimal('2')\n        >>> ExtendedContext.quantize(Decimal('2.17'), Decimal('1e+1'))\n        Decimal('0E+1')\n        >>> ExtendedContext.quantize(Decimal('-Inf'), Decimal('Infinity'))\n        Decimal('-Infinity')\n        >>> ExtendedContext.quantize(Decimal('2'), Decimal('Infinity'))\n        Decimal('NaN')\n        >>> ExtendedContext.quantize(Decimal('-0.1'), Decimal('1'))\n        Decimal('-0')\n        >>> ExtendedContext.quantize(Decimal('-0'), Decimal('1e+5'))\n        Decimal('-0E+5')\n        >>> ExtendedContext.quantize(Decimal('+35236450.6'), Decimal('1e-2'))\n        Decimal('NaN')\n        >>> ExtendedContext.quantize(Decimal('-35236450.6'), Decimal('1e-2'))\n        Decimal('NaN')\n        >>> ExtendedContext.quantize(Decimal('217'), Decimal('1e-1'))\n        Decimal('217.0')\n        >>> ExtendedContext.quantize(Decimal('217'), Decimal('1e-0'))\n        Decimal('217')\n        >>> ExtendedContext.quantize(Decimal('217'), Decimal('1e+1'))\n        Decimal('2.2E+2')\n        >>> ExtendedContext.quantize(Decimal('217'), Decimal('1e+2'))\n        Decimal('2E+2')\n        >>> ExtendedContext.quantize(1, 2)\n        Decimal('1')\n        >>> ExtendedContext.quantize(Decimal(1), 2)\n        Decimal('1')\n        >>> ExtendedContext.quantize(1, Decimal(2))\n        Decimal('1')\n        "
        a = _convert_other(a, raiseit=True)
        return a.quantize(b, context=self)

    def radix(self):
        "Just returns 10, as this is Decimal, :)\n\n        >>> ExtendedContext.radix()\n        Decimal('10')\n        "
        return Decimal(10)

    def remainder(self, a, b):
        "Returns the remainder from integer division.\n\n        The result is the residue of the dividend after the operation of\n        calculating integer division as described for divide-integer, rounded\n        to precision digits if necessary.  The sign of the result, if\n        non-zero, is the same as that of the original dividend.\n\n        This operation will fail under the same conditions as integer division\n        (that is, if integer division on the same two operands would fail, the\n        remainder cannot be calculated).\n\n        >>> ExtendedContext.remainder(Decimal('2.1'), Decimal('3'))\n        Decimal('2.1')\n        >>> ExtendedContext.remainder(Decimal('10'), Decimal('3'))\n        Decimal('1')\n        >>> ExtendedContext.remainder(Decimal('-10'), Decimal('3'))\n        Decimal('-1')\n        >>> ExtendedContext.remainder(Decimal('10.2'), Decimal('1'))\n        Decimal('0.2')\n        >>> ExtendedContext.remainder(Decimal('10'), Decimal('0.3'))\n        Decimal('0.1')\n        >>> ExtendedContext.remainder(Decimal('3.6'), Decimal('1.3'))\n        Decimal('1.0')\n        >>> ExtendedContext.remainder(22, 6)\n        Decimal('4')\n        >>> ExtendedContext.remainder(Decimal(22), 6)\n        Decimal('4')\n        >>> ExtendedContext.remainder(22, Decimal(6))\n        Decimal('4')\n        "
        a = _convert_other(a, raiseit=True)
        r = a.__mod__(b, context=self)
        if r is NotImplemented:
            raise TypeError(("Unable to convert %s to Decimal" % b))
        else:
            return r

    def remainder_near(self, a, b):
        "Returns to be \"a - b * n\", where n is the integer nearest the exact\n        value of \"x / b\" (if two integers are equally near then the even one\n        is chosen).  If the result is equal to 0 then its sign will be the\n        sign of a.\n\n        This operation will fail under the same conditions as integer division\n        (that is, if integer division on the same two operands would fail, the\n        remainder cannot be calculated).\n\n        >>> ExtendedContext.remainder_near(Decimal('2.1'), Decimal('3'))\n        Decimal('-0.9')\n        >>> ExtendedContext.remainder_near(Decimal('10'), Decimal('6'))\n        Decimal('-2')\n        >>> ExtendedContext.remainder_near(Decimal('10'), Decimal('3'))\n        Decimal('1')\n        >>> ExtendedContext.remainder_near(Decimal('-10'), Decimal('3'))\n        Decimal('-1')\n        >>> ExtendedContext.remainder_near(Decimal('10.2'), Decimal('1'))\n        Decimal('0.2')\n        >>> ExtendedContext.remainder_near(Decimal('10'), Decimal('0.3'))\n        Decimal('0.1')\n        >>> ExtendedContext.remainder_near(Decimal('3.6'), Decimal('1.3'))\n        Decimal('-0.3')\n        >>> ExtendedContext.remainder_near(3, 11)\n        Decimal('3')\n        >>> ExtendedContext.remainder_near(Decimal(3), 11)\n        Decimal('3')\n        >>> ExtendedContext.remainder_near(3, Decimal(11))\n        Decimal('3')\n        "
        a = _convert_other(a, raiseit=True)
        return a.remainder_near(b, context=self)

    def rotate(self, a, b):
        "Returns a rotated copy of a, b times.\n\n        The coefficient of the result is a rotated copy of the digits in\n        the coefficient of the first operand.  The number of places of\n        rotation is taken from the absolute value of the second operand,\n        with the rotation being to the left if the second operand is\n        positive or to the right otherwise.\n\n        >>> ExtendedContext.rotate(Decimal('34'), Decimal('8'))\n        Decimal('400000003')\n        >>> ExtendedContext.rotate(Decimal('12'), Decimal('9'))\n        Decimal('12')\n        >>> ExtendedContext.rotate(Decimal('123456789'), Decimal('-2'))\n        Decimal('891234567')\n        >>> ExtendedContext.rotate(Decimal('123456789'), Decimal('0'))\n        Decimal('123456789')\n        >>> ExtendedContext.rotate(Decimal('123456789'), Decimal('+2'))\n        Decimal('345678912')\n        >>> ExtendedContext.rotate(1333333, 1)\n        Decimal('13333330')\n        >>> ExtendedContext.rotate(Decimal(1333333), 1)\n        Decimal('13333330')\n        >>> ExtendedContext.rotate(1333333, Decimal(1))\n        Decimal('13333330')\n        "
        a = _convert_other(a, raiseit=True)
        return a.rotate(b, context=self)

    def same_quantum(self, a, b):
        "Returns True if the two operands have the same exponent.\n\n        The result is never affected by either the sign or the coefficient of\n        either operand.\n\n        >>> ExtendedContext.same_quantum(Decimal('2.17'), Decimal('0.001'))\n        False\n        >>> ExtendedContext.same_quantum(Decimal('2.17'), Decimal('0.01'))\n        True\n        >>> ExtendedContext.same_quantum(Decimal('2.17'), Decimal('1'))\n        False\n        >>> ExtendedContext.same_quantum(Decimal('Inf'), Decimal('-Inf'))\n        True\n        >>> ExtendedContext.same_quantum(10000, -1)\n        True\n        >>> ExtendedContext.same_quantum(Decimal(10000), -1)\n        True\n        >>> ExtendedContext.same_quantum(10000, Decimal(-1))\n        True\n        "
        a = _convert_other(a, raiseit=True)
        return a.same_quantum(b)

    def scaleb(self, a, b):
        "Returns the first operand after adding the second value its exp.\n\n        >>> ExtendedContext.scaleb(Decimal('7.50'), Decimal('-2'))\n        Decimal('0.0750')\n        >>> ExtendedContext.scaleb(Decimal('7.50'), Decimal('0'))\n        Decimal('7.50')\n        >>> ExtendedContext.scaleb(Decimal('7.50'), Decimal('3'))\n        Decimal('7.50E+3')\n        >>> ExtendedContext.scaleb(1, 4)\n        Decimal('1E+4')\n        >>> ExtendedContext.scaleb(Decimal(1), 4)\n        Decimal('1E+4')\n        >>> ExtendedContext.scaleb(1, Decimal(4))\n        Decimal('1E+4')\n        "
        a = _convert_other(a, raiseit=True)
        return a.scaleb(b, context=self)

    def shift(self, a, b):
        "Returns a shifted copy of a, b times.\n\n        The coefficient of the result is a shifted copy of the digits\n        in the coefficient of the first operand.  The number of places\n        to shift is taken from the absolute value of the second operand,\n        with the shift being to the left if the second operand is\n        positive or to the right otherwise.  Digits shifted into the\n        coefficient are zeros.\n\n        >>> ExtendedContext.shift(Decimal('34'), Decimal('8'))\n        Decimal('400000000')\n        >>> ExtendedContext.shift(Decimal('12'), Decimal('9'))\n        Decimal('0')\n        >>> ExtendedContext.shift(Decimal('123456789'), Decimal('-2'))\n        Decimal('1234567')\n        >>> ExtendedContext.shift(Decimal('123456789'), Decimal('0'))\n        Decimal('123456789')\n        >>> ExtendedContext.shift(Decimal('123456789'), Decimal('+2'))\n        Decimal('345678900')\n        >>> ExtendedContext.shift(88888888, 2)\n        Decimal('888888800')\n        >>> ExtendedContext.shift(Decimal(88888888), 2)\n        Decimal('888888800')\n        >>> ExtendedContext.shift(88888888, Decimal(2))\n        Decimal('888888800')\n        "
        a = _convert_other(a, raiseit=True)
        return a.shift(b, context=self)

    def sqrt(self, a):
        "Square root of a non-negative number to context precision.\n\n        If the result must be inexact, it is rounded using the round-half-even\n        algorithm.\n\n        >>> ExtendedContext.sqrt(Decimal('0'))\n        Decimal('0')\n        >>> ExtendedContext.sqrt(Decimal('-0'))\n        Decimal('-0')\n        >>> ExtendedContext.sqrt(Decimal('0.39'))\n        Decimal('0.624499800')\n        >>> ExtendedContext.sqrt(Decimal('100'))\n        Decimal('10')\n        >>> ExtendedContext.sqrt(Decimal('1'))\n        Decimal('1')\n        >>> ExtendedContext.sqrt(Decimal('1.0'))\n        Decimal('1.0')\n        >>> ExtendedContext.sqrt(Decimal('1.00'))\n        Decimal('1.0')\n        >>> ExtendedContext.sqrt(Decimal('7'))\n        Decimal('2.64575131')\n        >>> ExtendedContext.sqrt(Decimal('10'))\n        Decimal('3.16227766')\n        >>> ExtendedContext.sqrt(2)\n        Decimal('1.41421356')\n        >>> ExtendedContext.prec\n        9\n        "
        a = _convert_other(a, raiseit=True)
        return a.sqrt(context=self)

    def subtract(self, a, b):
        "Return the difference between the two operands.\n\n        >>> ExtendedContext.subtract(Decimal('1.3'), Decimal('1.07'))\n        Decimal('0.23')\n        >>> ExtendedContext.subtract(Decimal('1.3'), Decimal('1.30'))\n        Decimal('0.00')\n        >>> ExtendedContext.subtract(Decimal('1.3'), Decimal('2.07'))\n        Decimal('-0.77')\n        >>> ExtendedContext.subtract(8, 5)\n        Decimal('3')\n        >>> ExtendedContext.subtract(Decimal(8), 5)\n        Decimal('3')\n        >>> ExtendedContext.subtract(8, Decimal(5))\n        Decimal('3')\n        "
        a = _convert_other(a, raiseit=True)
        r = a.__sub__(b, context=self)
        if r is NotImplemented:
            raise TypeError(("Unable to convert %s to Decimal" % b))
        else:
            return r

    def to_eng_string(self, a):
        "Convert to a string, using engineering notation if an exponent is needed.\n\n        Engineering notation has an exponent which is a multiple of 3.  This\n        can leave up to 3 digits to the left of the decimal place and may\n        require the addition of either one or two trailing zeros.\n\n        The operation is not affected by the context.\n\n        >>> ExtendedContext.to_eng_string(Decimal('123E+1'))\n        '1.23E+3'\n        >>> ExtendedContext.to_eng_string(Decimal('123E+3'))\n        '123E+3'\n        >>> ExtendedContext.to_eng_string(Decimal('123E-10'))\n        '12.3E-9'\n        >>> ExtendedContext.to_eng_string(Decimal('-123E-12'))\n        '-123E-12'\n        >>> ExtendedContext.to_eng_string(Decimal('7E-7'))\n        '700E-9'\n        >>> ExtendedContext.to_eng_string(Decimal('7E+1'))\n        '70'\n        >>> ExtendedContext.to_eng_string(Decimal('0E+1'))\n        '0.00E+3'\n\n        "
        a = _convert_other(a, raiseit=True)
        return a.to_eng_string(context=self)

    def to_sci_string(self, a):
        "Converts a number to a string, using scientific notation.\n\n        The operation is not affected by the context.\n        "
        a = _convert_other(a, raiseit=True)
        return a.__str__(context=self)

    def to_integral_exact(self, a):
        "Rounds to an integer.\n\n        When the operand has a negative exponent, the result is the same\n        as using the quantize() operation using the given operand as the\n        left-hand-operand, 1E+0 as the right-hand-operand, and the precision\n        of the operand as the precision setting; Inexact and Rounded flags\n        are allowed in this operation.  The rounding mode is taken from the\n        context.\n\n        >>> ExtendedContext.to_integral_exact(Decimal('2.1'))\n        Decimal('2')\n        >>> ExtendedContext.to_integral_exact(Decimal('100'))\n        Decimal('100')\n        >>> ExtendedContext.to_integral_exact(Decimal('100.0'))\n        Decimal('100')\n        >>> ExtendedContext.to_integral_exact(Decimal('101.5'))\n        Decimal('102')\n        >>> ExtendedContext.to_integral_exact(Decimal('-101.5'))\n        Decimal('-102')\n        >>> ExtendedContext.to_integral_exact(Decimal('10E+5'))\n        Decimal('1.0E+6')\n        >>> ExtendedContext.to_integral_exact(Decimal('7.89E+77'))\n        Decimal('7.89E+77')\n        >>> ExtendedContext.to_integral_exact(Decimal('-Inf'))\n        Decimal('-Infinity')\n        "
        a = _convert_other(a, raiseit=True)
        return a.to_integral_exact(context=self)

    def to_integral_value(self, a):
        "Rounds to an integer.\n\n        When the operand has a negative exponent, the result is the same\n        as using the quantize() operation using the given operand as the\n        left-hand-operand, 1E+0 as the right-hand-operand, and the precision\n        of the operand as the precision setting, except that no flags will\n        be set.  The rounding mode is taken from the context.\n\n        >>> ExtendedContext.to_integral_value(Decimal('2.1'))\n        Decimal('2')\n        >>> ExtendedContext.to_integral_value(Decimal('100'))\n        Decimal('100')\n        >>> ExtendedContext.to_integral_value(Decimal('100.0'))\n        Decimal('100')\n        >>> ExtendedContext.to_integral_value(Decimal('101.5'))\n        Decimal('102')\n        >>> ExtendedContext.to_integral_value(Decimal('-101.5'))\n        Decimal('-102')\n        >>> ExtendedContext.to_integral_value(Decimal('10E+5'))\n        Decimal('1.0E+6')\n        >>> ExtendedContext.to_integral_value(Decimal('7.89E+77'))\n        Decimal('7.89E+77')\n        >>> ExtendedContext.to_integral_value(Decimal('-Inf'))\n        Decimal('-Infinity')\n        "
        a = _convert_other(a, raiseit=True)
        return a.to_integral_value(context=self)

    to_integral = to_integral_value


class _WorkRep(object):
    __slots__ = ("sign", "int", "exp")

    def __init__(self, value=None):
        if value is None:
            self.sign = None
            self.int = 0
            self.exp = None
        elif isinstance(value, Decimal):
            self.sign = value._sign
            self.int = int(value._int)
            self.exp = value._exp
        else:
            self.sign = value[0]
            self.int = value[1]
            self.exp = value[2]

    def __repr__(self):
        return "(%r, %r, %r)" % (self.sign, self.int, self.exp)


def _normalize(op1, op2, prec=0):
    "Normalizes op1, op2 to have the same exp and length of coefficient.\n\n    Done during addition.\n    "
    if op1.exp < op2.exp:
        tmp = op2
        other = op1
    else:
        tmp = op1
        other = op2
    tmp_len = len(str(tmp.int))
    other_len = len(str(other.int))
    exp = tmp.exp + min((-1), ((tmp_len - prec) - 2))
    if ((other_len + other.exp) - 1) < exp:
        other.int = 1
        other.exp = exp
    tmp.int *= 10 ** (tmp.exp - other.exp)
    tmp.exp = other.exp
    return (op1, op2)


_nbits = int.bit_length


def _decimal_lshift_exact(n, e):
    " Given integers n and e, return n * 10**e if it's an integer, else None.\n\n    The computation is designed to avoid computing large powers of 10\n    unnecessarily.\n\n    >>> _decimal_lshift_exact(3, 4)\n    30000\n    >>> _decimal_lshift_exact(300, -999999999)  # returns None\n\n    "
    if n == 0:
        return 0
    elif e >= 0:
        return n * (10 ** e)
    else:
        str_n = str(abs(n))
        val_n = len(str_n) - len(str_n.rstrip("0"))
        return None if (val_n < (-e)) else (n // (10 ** (-e)))


def _sqrt_nearest(n, a):
    "Closest integer to the square root of the positive integer n.  a is\n    an initial approximation to the square root.  Any positive integer\n    will do for a, but the closer a is to the square root of n the\n    faster convergence will be.\n\n    "
    if (n <= 0) or (a <= 0):
        raise ValueError("Both arguments to _sqrt_nearest should be positive.")
    b = 0
    while a != b:
        (b, a) = (a, ((a - ((-n) // a)) >> 1))
    return a


def _rshift_nearest(x, shift):
    "Given an integer x and a nonnegative integer shift, return closest\n    integer to x / 2**shift; use round-to-even in case of a tie.\n\n    "
    (b, q) = ((1 << shift), (x >> shift))
    return q + (((2 * (x & (b - 1))) + (q & 1)) > b)


def _div_nearest(a, b):
    "Closest integer to a/b, a and b positive integers; rounds to even\n    in the case of a tie.\n\n    "
    (q, r) = divmod(a, b)
    return q + (((2 * r) + (q & 1)) > b)


def _ilog(x, M, L=8):
    "Integer approximation to M*log(x/M), with absolute error boundable\n    in terms only of x/M.\n\n    Given positive integers x and M, return an integer approximation to\n    M * log(x/M).  For L = 8 and 0.1 <= x/M <= 10 the difference\n    between the approximation and the exact result is at most 22.  For\n    L = 8 and 1.0 <= x/M <= 10.0 the difference is at most 15.  In\n    both cases these are upper bounds on the error; it will usually be\n    much smaller."
    y = x - M
    R = 0
    while ((R <= L) and ((abs(y) << (L - R)) >= M)) or (
        (R > L) and ((abs(y) >> (R - L)) >= M)
    ):
        y = _div_nearest(
            ((M * y) << 1), (M + _sqrt_nearest((M * (M + _rshift_nearest(y, R))), M))
        )
        R += 1
    T = -int((((-10) * len(str(M))) // (3 * L)))
    yshift = _rshift_nearest(y, R)
    w = _div_nearest(M, T)
    for k in range((T - 1), 0, (-1)):
        w = _div_nearest(M, k) - _div_nearest((yshift * w), M)
    return _div_nearest((w * y), M)


def _dlog10(c, e, p):
    "Given integers c, e and p with c > 0, p >= 0, compute an integer\n    approximation to 10**p * log10(c*10**e), with an absolute error of\n    at most 1.  Assumes that c*10**e is not exactly 1."
    p += 2
    l = len(str(c))
    f = (e + l) - ((e + l) >= 1)
    if p > 0:
        M = 10 ** p
        k = (e + p) - f
        if k >= 0:
            c *= 10 ** k
        else:
            c = _div_nearest(c, (10 ** (-k)))
        log_d = _ilog(c, M)
        log_10 = _log10_digits(p)
        log_d = _div_nearest((log_d * M), log_10)
        log_tenpower = f * M
    else:
        log_d = 0
        log_tenpower = _div_nearest(f, (10 ** (-p)))
    return _div_nearest((log_tenpower + log_d), 100)


def _dlog(c, e, p):
    "Given integers c, e and p with c > 0, compute an integer\n    approximation to 10**p * log(c*10**e), with an absolute error of\n    at most 1.  Assumes that c*10**e is not exactly 1."
    p += 2
    l = len(str(c))
    f = (e + l) - ((e + l) >= 1)
    if p > 0:
        k = (e + p) - f
        if k >= 0:
            c *= 10 ** k
        else:
            c = _div_nearest(c, (10 ** (-k)))
        log_d = _ilog(c, (10 ** p))
    else:
        log_d = 0
    if f:
        extra = len(str(abs(f))) - 1
        if (p + extra) >= 0:
            f_log_ten = _div_nearest((f * _log10_digits((p + extra))), (10 ** extra))
        else:
            f_log_ten = 0
    else:
        f_log_ten = 0
    return _div_nearest((f_log_ten + log_d), 100)


class _Log10Memoize(object):
    "Class to compute, store, and allow retrieval of, digits of the\n    constant log(10) = 2.302585....  This constant is needed by\n    Decimal.ln, Decimal.log10, Decimal.exp and Decimal.__pow__."

    def __init__(self):
        self.digits = "23025850929940456840179914546843642076011014886"

    def getdigits(self, p):
        "Given an integer p >= 0, return floor(10**p)*log(10).\n\n        For example, self.getdigits(3) returns 2302.\n        "
        if p < 0:
            raise ValueError("p should be nonnegative")
        if p >= len(self.digits):
            extra = 3
            while True:
                M = 10 ** ((p + extra) + 2)
                digits = str(_div_nearest(_ilog((10 * M), M), 100))
                if digits[(-extra):] != ("0" * extra):
                    break
                extra += 3
            self.digits = digits.rstrip("0")[:(-1)]
        return int(self.digits[: (p + 1)])


_log10_digits = _Log10Memoize().getdigits


def _iexp(x, M, L=8):
    "Given integers x and M, M > 0, such that x/M is small in absolute\n    value, compute an integer approximation to M*exp(x/M).  For 0 <=\n    x/M <= 2.4, the absolute error in the result is bounded by 60 (and\n    is usually much smaller)."
    R = _nbits(((x << L) // M))
    T = -int((((-10) * len(str(M))) // (3 * L)))
    y = _div_nearest(x, T)
    Mshift = M << R
    for i in range((T - 1), 0, (-1)):
        y = _div_nearest((x * (Mshift + y)), (Mshift * i))
    for k in range((R - 1), (-1), (-1)):
        Mshift = M << (k + 2)
        y = _div_nearest((y * (y + Mshift)), Mshift)
    return M + y


def _dexp(c, e, p):
    "Compute an approximation to exp(c*10**e), with p decimal places of\n    precision.\n\n    Returns integers d, f such that:\n\n      10**(p-1) <= d <= 10**p, and\n      (d-1)*10**f < exp(c*10**e) < (d+1)*10**f\n\n    In other words, d*10**f is an approximation to exp(c*10**e) with p\n    digits of precision, and with an error in d of at most 1.  This is\n    almost, but not quite, the same as the error being < 1ulp: when d\n    = 10**(p-1) the error could be up to 10 ulp."
    p += 2
    extra = max(0, ((e + len(str(c))) - 1))
    q = p + extra
    shift = e + q
    if shift >= 0:
        cshift = c * (10 ** shift)
    else:
        cshift = c // (10 ** (-shift))
    (quot, rem) = divmod(cshift, _log10_digits(q))
    rem = _div_nearest(rem, (10 ** extra))
    return (_div_nearest(_iexp(rem, (10 ** p)), 1000), ((quot - p) + 3))


def _dpower(xc, xe, yc, ye, p):
    "Given integers xc, xe, yc and ye representing Decimals x = xc*10**xe and\n    y = yc*10**ye, compute x**y.  Returns a pair of integers (c, e) such that:\n\n      10**(p-1) <= c <= 10**p, and\n      (c-1)*10**e < x**y < (c+1)*10**e\n\n    in other words, c*10**e is an approximation to x**y with p digits\n    of precision, and with an error in c of at most 1.  (This is\n    almost, but not quite, the same as the error being < 1ulp: when c\n    == 10**(p-1) we can only guarantee error < 10ulp.)\n\n    We assume that: x is positive and not equal to 1, and y is nonzero.\n    "
    b = len(str(abs(yc))) + ye
    lxc = _dlog(xc, xe, ((p + b) + 1))
    shift = ye - b
    if shift >= 0:
        pc = (lxc * yc) * (10 ** shift)
    else:
        pc = _div_nearest((lxc * yc), (10 ** (-shift)))
    if pc == 0:
        if ((len(str(xc)) + xe) >= 1) == (yc > 0):
            (coeff, exp) = (((10 ** (p - 1)) + 1), (1 - p))
        else:
            (coeff, exp) = (((10 ** p) - 1), (-p))
    else:
        (coeff, exp) = _dexp(pc, (-(p + 1)), (p + 1))
        coeff = _div_nearest(coeff, 10)
        exp += 1
    return (coeff, exp)


def _log10_lb(
    c,
    correction={
        "1": 100,
        "2": 70,
        "3": 53,
        "4": 40,
        "5": 31,
        "6": 23,
        "7": 16,
        "8": 10,
        "9": 5,
    },
):
    "Compute a lower bound for 100*log10(c) for a positive integer c."
    if c <= 0:
        raise ValueError("The argument to _log10_lb should be nonnegative.")
    str_c = str(c)
    return (100 * len(str_c)) - correction[str_c[0]]


def _convert_other(other, raiseit=False, allow_float=False):
    "Convert other to Decimal.\n\n    Verifies that it's ok to use in an implicit construction.\n    If allow_float is true, allow conversion from float;  this\n    is used in the comparison methods (__eq__ and friends).\n\n    "
    if isinstance(other, Decimal):
        return other
    if isinstance(other, int):
        return Decimal(other)
    if allow_float and isinstance(other, float):
        return Decimal.from_float(other)
    if raiseit:
        raise TypeError(("Unable to convert %s to Decimal" % other))
    return NotImplemented


def _convert_for_comparison(self, other, equality_op=False):
    'Given a Decimal instance self and a Python object other, return\n    a pair (s, o) of Decimal instances such that "s op o" is\n    equivalent to "self op other" for any of the 6 comparison\n    operators "op".\n\n    '
    if isinstance(other, Decimal):
        return (self, other)
    if isinstance(other, _numbers.Rational):
        if not self._is_special:
            self = _dec_from_triple(
                self._sign, str((int(self._int) * other.denominator)), self._exp
            )
        return (self, Decimal(other.numerator))
    if equality_op and isinstance(other, _numbers.Complex) and (other.imag == 0):
        other = other.real
    if isinstance(other, float):
        context = getcontext()
        if equality_op:
            context.flags[FloatOperation] = 1
        else:
            context._raise_error(
                FloatOperation,
                "strict semantics for mixing floats and Decimals are enabled",
            )
        return (self, Decimal.from_float(other))
    return (NotImplemented, NotImplemented)


DefaultContext = Context(
    prec=28,
    rounding=ROUND_HALF_EVEN,
    traps=[DivisionByZero, Overflow, InvalidOperation],
    flags=[],
    Emax=999999,
    Emin=(-999999),
    capitals=1,
    clamp=0,
)
BasicContext = Context(
    prec=9,
    rounding=ROUND_HALF_UP,
    traps=[DivisionByZero, Overflow, InvalidOperation, Clamped, Underflow],
    flags=[],
)
ExtendedContext = Context(prec=9, rounding=ROUND_HALF_EVEN, traps=[], flags=[])
import re

_parser = re.compile(
    "        # A numeric string consists of:\n#    \\s*\n    (?P<sign>[-+])?              # an optional sign, followed by either...\n    (\n        (?=\\d|\\.\\d)              # ...a number (with at least one digit)\n        (?P<int>\\d*)             # having a (possibly empty) integer part\n        (\\.(?P<frac>\\d*))?       # followed by an optional fractional part\n        (E(?P<exp>[-+]?\\d+))?    # followed by an optional exponent, or...\n    |\n        Inf(inity)?              # ...an infinity, or...\n    |\n        (?P<signal>s)?           # ...an (optionally signaling)\n        NaN                      # NaN\n        (?P<diag>\\d*)            # with (possibly empty) diagnostic info.\n    )\n#    \\s*\n    \\Z\n",
    (re.VERBOSE | re.IGNORECASE),
).match
_all_zeros = re.compile("0*$").match
_exact_half = re.compile("50*$").match
_parse_format_specifier_regex = re.compile(
    "\\A\n(?:\n   (?P<fill>.)?\n   (?P<align>[<>=^])\n)?\n(?P<sign>[-+ ])?\n(?P<alt>\\#)?\n(?P<zeropad>0)?\n(?P<minimumwidth>(?!0)\\d+)?\n(?P<thousands_sep>,)?\n(?:\\.(?P<precision>0|(?!0)\\d+))?\n(?P<type>[eEfFgGn%])?\n\\Z\n",
    (re.VERBOSE | re.DOTALL),
)
del re
try:
    import locale as _locale
except ImportError:
    pass


def _parse_format_specifier(format_spec, _localeconv=None):
    "Parse and validate a format specifier.\n\n    Turns a standard numeric format specifier into a dict, with the\n    following entries:\n\n      fill: fill character to pad field to minimum width\n      align: alignment type, either '<', '>', '=' or '^'\n      sign: either '+', '-' or ' '\n      minimumwidth: nonnegative integer giving minimum width\n      zeropad: boolean, indicating whether to pad with zeros\n      thousands_sep: string to use as thousands separator, or ''\n      grouping: grouping for thousands separators, in format\n        used by localeconv\n      decimal_point: string to use for decimal point\n      precision: nonnegative integer giving precision, or None\n      type: one of the characters 'eEfFgG%', or None\n\n    "
    m = _parse_format_specifier_regex.match(format_spec)
    if m is None:
        raise ValueError(("Invalid format specifier: " + format_spec))
    format_dict = m.groupdict()
    fill = format_dict["fill"]
    align = format_dict["align"]
    format_dict["zeropad"] = format_dict["zeropad"] is not None
    if format_dict["zeropad"]:
        if fill is not None:
            raise ValueError(
                (
                    "Fill character conflicts with '0' in format specifier: "
                    + format_spec
                )
            )
        if align is not None:
            raise ValueError(
                ("Alignment conflicts with '0' in format specifier: " + format_spec)
            )
    format_dict["fill"] = fill or " "
    format_dict["align"] = align or ">"
    if format_dict["sign"] is None:
        format_dict["sign"] = "-"
    format_dict["minimumwidth"] = int((format_dict["minimumwidth"] or "0"))
    if format_dict["precision"] is not None:
        format_dict["precision"] = int(format_dict["precision"])
    if format_dict["precision"] == 0:
        if (format_dict["type"] is None) or (format_dict["type"] in "gGn"):
            format_dict["precision"] = 1
    if format_dict["type"] == "n":
        format_dict["type"] = "g"
        if _localeconv is None:
            _localeconv = _locale.localeconv()
        if format_dict["thousands_sep"] is not None:
            raise ValueError(
                (
                    "Explicit thousands separator conflicts with 'n' type in format specifier: "
                    + format_spec
                )
            )
        format_dict["thousands_sep"] = _localeconv["thousands_sep"]
        format_dict["grouping"] = _localeconv["grouping"]
        format_dict["decimal_point"] = _localeconv["decimal_point"]
    else:
        if format_dict["thousands_sep"] is None:
            format_dict["thousands_sep"] = ""
        format_dict["grouping"] = [3, 0]
        format_dict["decimal_point"] = "."
    return format_dict


def _format_align(sign, body, spec):
    "Given an unpadded, non-aligned numeric string 'body' and sign\n    string 'sign', add padding and alignment conforming to the given\n    format specifier dictionary 'spec' (as produced by\n    parse_format_specifier).\n\n    "
    minimumwidth = spec["minimumwidth"]
    fill = spec["fill"]
    padding = fill * ((minimumwidth - len(sign)) - len(body))
    align = spec["align"]
    if align == "<":
        result = (sign + body) + padding
    elif align == ">":
        result = (padding + sign) + body
    elif align == "=":
        result = (sign + padding) + body
    elif align == "^":
        half = len(padding) // 2
        result = ((padding[:half] + sign) + body) + padding[half:]
    else:
        raise ValueError("Unrecognised alignment field")
    return result


def _group_lengths(grouping):
    "Convert a localeconv-style grouping into a (possibly infinite)\n    iterable of integers representing group lengths.\n\n    "
    from itertools import chain, repeat

    if not grouping:
        return []
    elif (grouping[(-1)] == 0) and (len(grouping) >= 2):
        return chain(grouping[:(-1)], repeat(grouping[(-2)]))
    elif grouping[(-1)] == _locale.CHAR_MAX:
        return grouping[:(-1)]
    else:
        raise ValueError("unrecognised format for grouping")


def _insert_thousands_sep(digits, spec, min_width=1):
    "Insert thousands separators into a digit string.\n\n    spec is a dictionary whose keys should include 'thousands_sep' and\n    'grouping'; typically it's the result of parsing the format\n    specifier using _parse_format_specifier.\n\n    The min_width keyword argument gives the minimum length of the\n    result, which will be padded on the left with zeros if necessary.\n\n    If necessary, the zero padding adds an extra '0' on the left to\n    avoid a leading thousands separator.  For example, inserting\n    commas every three digits in '123456', with min_width=8, gives\n    '0,123,456', even though that has length 9.\n\n    "
    sep = spec["thousands_sep"]
    grouping = spec["grouping"]
    groups = []
    for l in _group_lengths(grouping):
        if l <= 0:
            raise ValueError("group length should be positive")
        l = min(max(len(digits), min_width, 1), l)
        groups.append((("0" * (l - len(digits))) + digits[(-l):]))
        digits = digits[:(-l)]
        min_width -= l
        if (not digits) and (min_width <= 0):
            break
        min_width -= len(sep)
    else:
        l = max(len(digits), min_width, 1)
        groups.append((("0" * (l - len(digits))) + digits[(-l):]))
    return sep.join(reversed(groups))


def _format_sign(is_negative, spec):
    "Determine sign character."
    if is_negative:
        return "-"
    elif spec["sign"] in " +":
        return spec["sign"]
    else:
        return ""


def _format_number(is_negative, intpart, fracpart, exp, spec):
    "Format a number, given the following data:\n\n    is_negative: true if the number is negative, else false\n    intpart: string of digits that must appear before the decimal point\n    fracpart: string of digits that must come after the point\n    exp: exponent, as an integer\n    spec: dictionary resulting from parsing the format specifier\n\n    This function uses the information in spec to:\n      insert separators (decimal separator and thousands separators)\n      format the sign\n      format the exponent\n      add trailing '%' for the '%' type\n      zero-pad if necessary\n      fill and align if necessary\n    "
    sign = _format_sign(is_negative, spec)
    if fracpart or spec["alt"]:
        fracpart = spec["decimal_point"] + fracpart
    if (exp != 0) or (spec["type"] in "eE"):
        echar = {"E": "E", "e": "e", "G": "E", "g": "e"}[spec["type"]]
        fracpart += "{0}{1:+}".format(echar, exp)
    if spec["type"] == "%":
        fracpart += "%"
    if spec["zeropad"]:
        min_width = (spec["minimumwidth"] - len(fracpart)) - len(sign)
    else:
        min_width = 0
    intpart = _insert_thousands_sep(intpart, spec, min_width)
    return _format_align(sign, (intpart + fracpart), spec)


_Infinity = Decimal("Inf")
_NegativeInfinity = Decimal("-Inf")
_NaN = Decimal("NaN")
_Zero = Decimal(0)
_One = Decimal(1)
_NegativeOne = Decimal((-1))
_SignedInfinity = (_Infinity, _NegativeInfinity)
_PyHASH_MODULUS = sys.hash_info.modulus
_PyHASH_INF = sys.hash_info.inf
_PyHASH_NAN = sys.hash_info.nan
_PyHASH_10INV = pow(10, (_PyHASH_MODULUS - 2), _PyHASH_MODULUS)
del sys
