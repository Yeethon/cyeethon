import random
import time

RANDSEED = int(time.time())
random.seed(RANDSEED)
import sys
import os
from copy import copy
from collections import defaultdict
import argparse
import subprocess
from subprocess import PIPE, STDOUT
from queue import Queue, Empty
from threading import Thread, Event, Lock
from test.support import import_fresh_module
from randdec import randfloat, all_unary, all_binary, all_ternary
from randdec import unary_optarg, binary_optarg, ternary_optarg
from formathelper import rand_format, rand_locale
from _pydecimal import _dec_from_triple

C = import_fresh_module("decimal", fresh=["_decimal"])
P = import_fresh_module("decimal", blocked=["_decimal"])
EXIT_STATUS = 0
Functions = {
    "unary": (
        "__abs__",
        "__bool__",
        "__ceil__",
        "__complex__",
        "__copy__",
        "__floor__",
        "__float__",
        "__hash__",
        "__int__",
        "__neg__",
        "__pos__",
        "__reduce__",
        "__repr__",
        "__str__",
        "__trunc__",
        "adjusted",
        "as_integer_ratio",
        "as_tuple",
        "canonical",
        "conjugate",
        "copy_abs",
        "copy_negate",
        "is_canonical",
        "is_finite",
        "is_infinite",
        "is_nan",
        "is_qnan",
        "is_signed",
        "is_snan",
        "is_zero",
        "radix",
    ),
    "unary_ctx": (
        "exp",
        "is_normal",
        "is_subnormal",
        "ln",
        "log10",
        "logb",
        "logical_invert",
        "next_minus",
        "next_plus",
        "normalize",
        "number_class",
        "sqrt",
        "to_eng_string",
    ),
    "unary_rnd_ctx": ("to_integral", "to_integral_exact", "to_integral_value"),
    "binary": (
        "__add__",
        "__divmod__",
        "__eq__",
        "__floordiv__",
        "__ge__",
        "__gt__",
        "__le__",
        "__lt__",
        "__mod__",
        "__mul__",
        "__ne__",
        "__pow__",
        "__radd__",
        "__rdivmod__",
        "__rfloordiv__",
        "__rmod__",
        "__rmul__",
        "__rpow__",
        "__rsub__",
        "__rtruediv__",
        "__sub__",
        "__truediv__",
        "compare_total",
        "compare_total_mag",
        "copy_sign",
        "quantize",
        "same_quantum",
    ),
    "binary_ctx": (
        "compare",
        "compare_signal",
        "logical_and",
        "logical_or",
        "logical_xor",
        "max",
        "max_mag",
        "min",
        "min_mag",
        "next_toward",
        "remainder_near",
        "rotate",
        "scaleb",
        "shift",
    ),
    "ternary": ("__pow__",),
    "ternary_ctx": ("fma",),
    "special": ("__format__", "__reduce_ex__", "__round__", "from_float", "quantize"),
    "property": ("real", "imag"),
}
ContextFunctions = {
    "nullary": ("context.__hash__", "context.__reduce__", "context.radix"),
    "unary": (
        "context.abs",
        "context.canonical",
        "context.copy_abs",
        "context.copy_decimal",
        "context.copy_negate",
        "context.create_decimal",
        "context.exp",
        "context.is_canonical",
        "context.is_finite",
        "context.is_infinite",
        "context.is_nan",
        "context.is_normal",
        "context.is_qnan",
        "context.is_signed",
        "context.is_snan",
        "context.is_subnormal",
        "context.is_zero",
        "context.ln",
        "context.log10",
        "context.logb",
        "context.logical_invert",
        "context.minus",
        "context.next_minus",
        "context.next_plus",
        "context.normalize",
        "context.number_class",
        "context.plus",
        "context.sqrt",
        "context.to_eng_string",
        "context.to_integral",
        "context.to_integral_exact",
        "context.to_integral_value",
        "context.to_sci_string",
    ),
    "binary": (
        "context.add",
        "context.compare",
        "context.compare_signal",
        "context.compare_total",
        "context.compare_total_mag",
        "context.copy_sign",
        "context.divide",
        "context.divide_int",
        "context.divmod",
        "context.logical_and",
        "context.logical_or",
        "context.logical_xor",
        "context.max",
        "context.max_mag",
        "context.min",
        "context.min_mag",
        "context.multiply",
        "context.next_toward",
        "context.power",
        "context.quantize",
        "context.remainder",
        "context.remainder_near",
        "context.rotate",
        "context.same_quantum",
        "context.scaleb",
        "context.shift",
        "context.subtract",
    ),
    "ternary": ("context.fma", "context.power"),
    "special": ("context.__reduce_ex__", "context.create_decimal_from_float"),
}
MaxContextSkip = [
    "is_normal",
    "is_subnormal",
    "logical_invert",
    "next_minus",
    "next_plus",
    "number_class",
    "logical_and",
    "logical_or",
    "logical_xor",
    "next_toward",
    "rotate",
    "shift",
]
UnaryRestricted = [
    "__ceil__",
    "__floor__",
    "__int__",
    "__trunc__",
    "as_integer_ratio",
    "to_integral",
    "to_integral_value",
]
BinaryRestricted = ["__round__"]
TernaryRestricted = ["__pow__", "context.power"]
CondMap = {
    C.Clamped: P.Clamped,
    C.ConversionSyntax: P.ConversionSyntax,
    C.DivisionByZero: P.DivisionByZero,
    C.DivisionImpossible: P.InvalidOperation,
    C.DivisionUndefined: P.DivisionUndefined,
    C.Inexact: P.Inexact,
    C.InvalidContext: P.InvalidContext,
    C.InvalidOperation: P.InvalidOperation,
    C.Overflow: P.Overflow,
    C.Rounded: P.Rounded,
    C.Subnormal: P.Subnormal,
    C.Underflow: P.Underflow,
    C.FloatOperation: P.FloatOperation,
}
RoundModes = [
    C.ROUND_UP,
    C.ROUND_DOWN,
    C.ROUND_CEILING,
    C.ROUND_FLOOR,
    C.ROUND_HALF_UP,
    C.ROUND_HALF_DOWN,
    C.ROUND_HALF_EVEN,
    C.ROUND_05UP,
]


class Context(object):
    "Provides a convenient way of syncing the C and P contexts"
    __slots__ = ["c", "p"]

    def __init__(self, c_ctx=None, p_ctx=None):
        "Initialization is from the C context"
        self.c = C.getcontext() if (c_ctx is None) else c_ctx
        self.p = P.getcontext() if (p_ctx is None) else p_ctx
        self.p.prec = self.c.prec
        self.p.Emin = self.c.Emin
        self.p.Emax = self.c.Emax
        self.p.rounding = self.c.rounding
        self.p.capitals = self.c.capitals
        self.settraps([sig for sig in self.c.traps if self.c.traps[sig]])
        self.setstatus([sig for sig in self.c.flags if self.c.flags[sig]])
        self.p.clamp = self.c.clamp

    def __str__(self):
        return (str(self.c) + "\n") + str(self.p)

    def getprec(self):
        assert self.c.prec == self.p.prec
        return self.c.prec

    def setprec(self, val):
        self.c.prec = val
        self.p.prec = val

    def getemin(self):
        assert self.c.Emin == self.p.Emin
        return self.c.Emin

    def setemin(self, val):
        self.c.Emin = val
        self.p.Emin = val

    def getemax(self):
        assert self.c.Emax == self.p.Emax
        return self.c.Emax

    def setemax(self, val):
        self.c.Emax = val
        self.p.Emax = val

    def getround(self):
        assert self.c.rounding == self.p.rounding
        return self.c.rounding

    def setround(self, val):
        self.c.rounding = val
        self.p.rounding = val

    def getcapitals(self):
        assert self.c.capitals == self.p.capitals
        return self.c.capitals

    def setcapitals(self, val):
        self.c.capitals = val
        self.p.capitals = val

    def getclamp(self):
        assert self.c.clamp == self.p.clamp
        return self.c.clamp

    def setclamp(self, val):
        self.c.clamp = val
        self.p.clamp = val

    prec = property(getprec, setprec)
    Emin = property(getemin, setemin)
    Emax = property(getemax, setemax)
    rounding = property(getround, setround)
    clamp = property(getclamp, setclamp)
    capitals = property(getcapitals, setcapitals)

    def clear_traps(self):
        self.c.clear_traps()
        for trap in self.p.traps:
            self.p.traps[trap] = False

    def clear_status(self):
        self.c.clear_flags()
        self.p.clear_flags()

    def settraps(self, lst):
        "lst: C signal list"
        self.clear_traps()
        for signal in lst:
            self.c.traps[signal] = True
            self.p.traps[CondMap[signal]] = True

    def setstatus(self, lst):
        "lst: C signal list"
        self.clear_status()
        for signal in lst:
            self.c.flags[signal] = True
            self.p.flags[CondMap[signal]] = True

    def assert_eq_status(self):
        "assert equality of C and P status"
        for signal in self.c.flags:
            if self.c.flags[signal] == (not self.p.flags[CondMap[signal]]):
                return False
        return True


context = Context()
context.Emin = C.MIN_EMIN
context.Emax = C.MAX_EMAX
context.clear_traps()
maxcontext = P.Context(
    prec=C.MAX_PREC,
    Emin=C.MIN_EMIN,
    Emax=C.MAX_EMAX,
    rounding=P.ROUND_HALF_UP,
    capitals=1,
)
maxcontext.clamp = 0


def RestrictedDecimal(value):
    maxcontext.traps = copy(context.p.traps)
    maxcontext.clear_flags()
    if isinstance(value, str):
        value = value.strip()
    dec = maxcontext.create_decimal(value)
    if (
        maxcontext.flags[P.Inexact]
        or maxcontext.flags[P.Rounded]
        or maxcontext.flags[P.Clamped]
        or maxcontext.flags[P.InvalidOperation]
    ):
        return context.p._raise_error(P.InvalidOperation)
    if maxcontext.flags[P.FloatOperation]:
        context.p.flags[P.FloatOperation] = True
    return dec


class RestrictedList(list):
    "List that can only be modified by appending items."

    def __getattribute__(self, name):
        if name != "append":
            raise AttributeError("unsupported operation")
        return list.__getattribute__(self, name)

    def unsupported(self, *_):
        raise AttributeError("unsupported operation")

    __add__ = __delattr__ = __delitem__ = __iadd__ = __imul__ = unsupported
    __mul__ = __reversed__ = __rmul__ = __setattr__ = __setitem__ = unsupported


class TestSet(object):
    "A TestSet contains the original input operands, converted operands,\n       Python exceptions that occurred either during conversion or during\n       execution of the actual function, and the final results.\n\n       For safety, most attributes are lists that only support the append\n       operation.\n\n       If a function name is prefixed with 'context.', the corresponding\n       context method is called.\n    "

    def __init__(self, funcname, operands):
        if funcname.startswith("context."):
            self.funcname = funcname.replace("context.", "")
            self.contextfunc = True
        else:
            self.funcname = funcname
            self.contextfunc = False
        self.op = operands
        self.context = context
        self.cop = RestrictedList()
        self.cex = RestrictedList()
        self.cresults = RestrictedList()
        self.pop = RestrictedList()
        self.pex = RestrictedList()
        self.presults = RestrictedList()
        self.with_maxcontext = False
        self.maxcontext = context.c.copy()
        self.maxcontext.prec = C.MAX_PREC
        self.maxcontext.Emax = C.MAX_EMAX
        self.maxcontext.Emin = C.MIN_EMIN
        self.maxcontext.clear_flags()
        self.maxop = RestrictedList()
        self.maxex = RestrictedList()
        self.maxresults = RestrictedList()


class SkipHandler:
    "Handle known discrepancies between decimal.py and _decimal.so.\n       These are either ULP differences in the power function or\n       extremely minor issues."

    def __init__(self):
        self.ulpdiff = 0
        self.powmod_zeros = 0
        self.maxctx = P.Context(Emax=(10 ** 18), Emin=(-(10 ** 18)))

    def default(self, t):
        return False

    __ge__ = __gt__ = __le__ = __lt__ = __ne__ = __eq__ = default
    __reduce__ = __format__ = __repr__ = __str__ = default

    def harrison_ulp(self, dec):
        "ftp://ftp.inria.fr/INRIA/publication/publi-pdf/RR/RR-5504.pdf"
        a = dec.next_plus()
        b = dec.next_minus()
        return abs((a - b))

    def standard_ulp(self, dec, prec):
        return _dec_from_triple(0, "1", ((dec._exp + len(dec._int)) - prec))

    def rounding_direction(self, x, mode):
        "Determine the effective direction of the rounding when\n           the exact result x is rounded according to mode.\n           Return -1 for downwards, 0 for undirected, 1 for upwards,\n           2 for ROUND_05UP."
        cmp = 1 if (x.compare_total(P.Decimal("+0")) >= 0) else (-1)
        if mode in (P.ROUND_HALF_EVEN, P.ROUND_HALF_UP, P.ROUND_HALF_DOWN):
            return 0
        elif mode == P.ROUND_CEILING:
            return 1
        elif mode == P.ROUND_FLOOR:
            return -1
        elif mode == P.ROUND_UP:
            return cmp
        elif mode == P.ROUND_DOWN:
            return -cmp
        elif mode == P.ROUND_05UP:
            return 2
        else:
            raise ValueError(("Unexpected rounding mode: %s" % mode))

    def check_ulpdiff(self, exact, rounded):
        p = context.p.prec
        x = exact
        if exact.is_infinite():
            x = _dec_from_triple(exact._sign, "10", context.p.Emax)
        y = rounded
        if rounded.is_infinite():
            y = _dec_from_triple(rounded._sign, "10", context.p.Emax)
        self.maxctx.prec = p * 2
        t = self.maxctx.subtract(y, x)
        if context.c.flags[C.Clamped] or context.c.flags[C.Underflow]:
            ulp = self.harrison_ulp(y)
        else:
            ulp = self.standard_ulp(y, p)
        err = self.maxctx.divide(t, ulp)
        dir = self.rounding_direction(x, context.p.rounding)
        if dir == 0:
            if P.Decimal("-0.6") < err < P.Decimal("0.6"):
                return True
        elif dir == 1:
            if P.Decimal("-0.1") < err < P.Decimal("1.1"):
                return True
        elif dir == (-1):
            if P.Decimal("-1.1") < err < P.Decimal("0.1"):
                return True
        elif P.Decimal("-1.1") < err < P.Decimal("1.1"):
            return True
        print(
            (
                "ulp: %s  error: %s  exact: %s  c_rounded: %s"
                % (ulp, err, exact, rounded)
            )
        )
        return False

    def bin_resolve_ulp(self, t):
        "Check if results of _decimal's power function are within the\n           allowed ulp ranges."
        if t.rc.is_nan() or t.rp.is_nan():
            return False
        self.maxctx.prec = context.p.prec * 2
        (op1, op2) = (t.pop[0], t.pop[1])
        if t.contextfunc:
            exact = getattr(self.maxctx, t.funcname)(op1, op2)
        else:
            exact = getattr(op1, t.funcname)(op2, context=self.maxctx)
        rounded = P.Decimal(t.cresults[0])
        self.ulpdiff += 1
        return self.check_ulpdiff(exact, rounded)

    def resolve_underflow(self, t):
        'In extremely rare cases where the infinite precision result is just\n           below etiny, cdecimal does not set Subnormal/Underflow. Example:\n\n           setcontext(Context(prec=21, rounding=ROUND_UP, Emin=-55, Emax=85))\n           Decimal("1.00000000000000000000000000000000000000000000000"\n                   "0000000100000000000000000000000000000000000000000"\n                   "0000000000000025").ln()\n        '
        if t.cresults != t.presults:
            return False
        if (
            context.c.flags[C.Rounded]
            and context.c.flags[C.Inexact]
            and context.p.flags[P.Rounded]
            and context.p.flags[P.Inexact]
        ):
            return True
        return False

    def exp(self, t):
        "Resolve Underflow or ULP difference."
        return self.resolve_underflow(t)

    def log10(self, t):
        "Resolve Underflow or ULP difference."
        return self.resolve_underflow(t)

    def ln(self, t):
        "Resolve Underflow or ULP difference."
        return self.resolve_underflow(t)

    def __pow__(self, t):
        "Always calls the resolve function. C.Decimal does not have correct\n           rounding for the power function."
        if (
            context.c.flags[C.Rounded]
            and context.c.flags[C.Inexact]
            and context.p.flags[P.Rounded]
            and context.p.flags[P.Inexact]
        ):
            return self.bin_resolve_ulp(t)
        else:
            return False

    power = __rpow__ = __pow__

    def __float__(self, t):
        "NaN comparison in the verify() function obviously gives an\n           incorrect answer:  nan == nan -> False"
        if t.cop[0].is_nan() and t.pop[0].is_nan():
            return True
        return False

    __complex__ = __float__

    def __radd__(self, t):
        "decimal.py gives precedence to the first NaN; this is\n           not important, as __radd__ will not be called for\n           two decimal arguments."
        if t.rc.is_nan() and t.rp.is_nan():
            return True
        return False

    __rmul__ = __radd__

    def __round__(self, t):
        "Exception: Decimal('1').__round__(-100000000000000000000000000)\n           Should it really be InvalidOperation?"
        if (t.rc is None) and t.rp.is_nan():
            return True
        return False


shandler = SkipHandler()


def skip_error(t):
    return getattr(shandler, t.funcname, shandler.default)(t)


class VerifyError(Exception):
    "Verification failed."
    pass


def function_as_string(t):
    if t.contextfunc:
        cargs = t.cop
        pargs = t.pop
        maxargs = t.maxop
        cfunc = "c_func: %s(" % t.funcname
        pfunc = "p_func: %s(" % t.funcname
        maxfunc = "max_func: %s(" % t.funcname
    else:
        (cself, cargs) = (t.cop[0], t.cop[1:])
        (pself, pargs) = (t.pop[0], t.pop[1:])
        (maxself, maxargs) = (t.maxop[0], t.maxop[1:])
        cfunc = "c_func: %s.%s(" % (repr(cself), t.funcname)
        pfunc = "p_func: %s.%s(" % (repr(pself), t.funcname)
        maxfunc = "max_func: %s.%s(" % (repr(maxself), t.funcname)
    err = cfunc
    for arg in cargs:
        err += "%s, " % repr(arg)
    err = err.rstrip(", ")
    err += ")\n"
    err += pfunc
    for arg in pargs:
        err += "%s, " % repr(arg)
    err = err.rstrip(", ")
    err += ")"
    if t.with_maxcontext:
        err += "\n"
        err += maxfunc
        for arg in maxargs:
            err += "%s, " % repr(arg)
        err = err.rstrip(", ")
        err += ")"
    return err


def raise_error(t):
    global EXIT_STATUS
    if skip_error(t):
        return
    EXIT_STATUS = 1
    err = "Error in %s:\n\n" % t.funcname
    err += "input operands: %s\n\n" % (t.op,)
    err += function_as_string(t)
    err += "\n\nc_result: %s\np_result: %s\n" % (t.cresults, t.presults)
    if t.with_maxcontext:
        err += "max_result: %s\n\n" % t.maxresults
    else:
        err += "\n"
    err += "c_exceptions: %s\np_exceptions: %s\n" % (t.cex, t.pex)
    if t.with_maxcontext:
        err += "max_exceptions: %s\n\n" % t.maxex
    else:
        err += "\n"
    err += "%s\n" % str(t.context)
    if t.with_maxcontext:
        err += "%s\n" % str(t.maxcontext)
    else:
        err += "\n"
    raise VerifyError(err)


def all_nan(a):
    if isinstance(a, C.Decimal):
        return a.is_nan()
    elif isinstance(a, tuple):
        return all((all_nan(v) for v in a))
    return False


def convert(t, convstr=True):
    " t is the testset. At this stage the testset contains a tuple of\n        operands t.op of various types. For decimal methods the first\n        operand (self) is always converted to Decimal. If 'convstr' is\n        true, string operands are converted as well.\n\n        Context operands are of type deccheck.Context, rounding mode\n        operands are given as a tuple (C.rounding, P.rounding).\n\n        Other types (float, int, etc.) are left unchanged.\n    "
    for (i, op) in enumerate(t.op):
        context.clear_status()
        t.maxcontext.clear_flags()
        if op in RoundModes:
            t.cop.append(op)
            t.pop.append(op)
            t.maxop.append(op)
        elif ((not t.contextfunc) and (i == 0)) or (convstr and isinstance(op, str)):
            try:
                c = C.Decimal(op)
                cex = None
            except (TypeError, ValueError, OverflowError) as e:
                c = None
                cex = e.__class__
            try:
                p = RestrictedDecimal(op)
                pex = None
            except (TypeError, ValueError, OverflowError) as e:
                p = None
                pex = e.__class__
            try:
                C.setcontext(t.maxcontext)
                maxop = C.Decimal(op)
                maxex = None
            except (TypeError, ValueError, OverflowError) as e:
                maxop = None
                maxex = e.__class__
            finally:
                C.setcontext(context.c)
            t.cop.append(c)
            t.cex.append(cex)
            t.pop.append(p)
            t.pex.append(pex)
            t.maxop.append(maxop)
            t.maxex.append(maxex)
            if cex is pex:
                if (str(c) != str(p)) or (not context.assert_eq_status()):
                    raise_error(t)
                if cex and pex:
                    return 0
            else:
                raise_error(t)
            if (maxex is not None) and (cex is not maxex):
                raise_error(t)
        elif isinstance(op, Context):
            t.context = op
            t.cop.append(op.c)
            t.pop.append(op.p)
            t.maxop.append(t.maxcontext)
        else:
            t.cop.append(op)
            t.pop.append(op)
            t.maxop.append(op)
    return 1


def callfuncs(t):
    " t is the testset. At this stage the testset contains operand lists\n        t.cop and t.pop for the C and Python versions of decimal.\n        For Decimal methods, the first operands are of type C.Decimal and\n        P.Decimal respectively. The remaining operands can have various types.\n        For Context methods, all operands can have any type.\n\n        t.rc and t.rp are the results of the operation.\n    "
    context.clear_status()
    t.maxcontext.clear_flags()
    try:
        if t.contextfunc:
            cargs = t.cop
            t.rc = getattr(context.c, t.funcname)(*cargs)
        else:
            cself = t.cop[0]
            cargs = t.cop[1:]
            t.rc = getattr(cself, t.funcname)(*cargs)
        t.cex.append(None)
    except (TypeError, ValueError, OverflowError, MemoryError) as e:
        t.rc = None
        t.cex.append(e.__class__)
    try:
        if t.contextfunc:
            pargs = t.pop
            t.rp = getattr(context.p, t.funcname)(*pargs)
        else:
            pself = t.pop[0]
            pargs = t.pop[1:]
            t.rp = getattr(pself, t.funcname)(*pargs)
        t.pex.append(None)
    except (TypeError, ValueError, OverflowError, MemoryError) as e:
        t.rp = None
        t.pex.append(e.__class__)
    if (
        (t.funcname not in MaxContextSkip)
        and (not context.c.flags[C.InvalidOperation])
        and (not context.c.flags[C.Inexact])
        and (not context.c.flags[C.Rounded])
        and (not context.c.flags[C.Subnormal])
        and (not context.c.flags[C.Clamped])
        and (not context.clamp)
        and (not any((isinstance(v, C.Context) for v in t.cop)))
    ):
        t.with_maxcontext = True
        try:
            if t.contextfunc:
                maxargs = t.maxop
                t.rmax = getattr(t.maxcontext, t.funcname)(*maxargs)
            else:
                maxself = t.maxop[0]
                maxargs = t.maxop[1:]
                try:
                    C.setcontext(t.maxcontext)
                    t.rmax = getattr(maxself, t.funcname)(*maxargs)
                finally:
                    C.setcontext(context.c)
            t.maxex.append(None)
        except (TypeError, ValueError, OverflowError, MemoryError) as e:
            t.rmax = None
            t.maxex.append(e.__class__)


def verify(t, stat):
    " t is the testset. At this stage the testset contains the following\n        tuples:\n\n            t.op: original operands\n            t.cop: C.Decimal operands (see convert for details)\n            t.pop: P.Decimal operands (see convert for details)\n            t.rc: C result\n            t.rp: Python result\n\n        t.rc and t.rp can have various types.\n    "
    t.cresults.append(str(t.rc))
    t.presults.append(str(t.rp))
    if t.with_maxcontext:
        t.maxresults.append(str(t.rmax))
    if isinstance(t.rc, C.Decimal) and isinstance(t.rp, P.Decimal):
        t.cresults.append(t.rc.to_eng_string())
        t.cresults.append(t.rc.as_tuple())
        t.cresults.append(str(t.rc.imag))
        t.cresults.append(str(t.rc.real))
        t.presults.append(t.rp.to_eng_string())
        t.presults.append(t.rp.as_tuple())
        t.presults.append(str(t.rp.imag))
        t.presults.append(str(t.rp.real))
        if t.with_maxcontext and isinstance(t.rmax, C.Decimal):
            t.maxresults.append(t.rmax.to_eng_string())
            t.maxresults.append(t.rmax.as_tuple())
            t.maxresults.append(str(t.rmax.imag))
            t.maxresults.append(str(t.rmax.real))
        nc = t.rc.number_class().lstrip("+-s")
        stat[nc] += 1
    else:
        if (not isinstance(t.rc, tuple)) and (not isinstance(t.rp, tuple)):
            if t.rc != t.rp:
                raise_error(t)
            if t.with_maxcontext and (not isinstance(t.rmax, tuple)):
                if t.rmax != t.rc:
                    raise_error(t)
        stat[type(t.rc).__name__] += 1
    if t.cresults != t.presults:
        raise_error(t)
    if t.cex != t.pex:
        raise_error(t)
    if not t.context.assert_eq_status():
        raise_error(t)
    if t.with_maxcontext:
        if all_nan(t.rc) and all_nan(t.rmax):
            return
        if t.maxresults != t.cresults:
            raise_error(t)
        if t.maxex != t.cex:
            raise_error(t)
        if t.maxcontext.flags != t.context.c.flags:
            raise_error(t)


def log(fmt, args=None):
    if args:
        sys.stdout.write(("".join((fmt, "\n")) % args))
    else:
        sys.stdout.write("".join((str(fmt), "\n")))
    sys.stdout.flush()


def test_method(method, testspecs, testfunc):
    "Iterate a test function through many context settings."
    log("testing %s ...", method)
    stat = defaultdict(int)
    for spec in testspecs:
        if "samples" in spec:
            spec["prec"] = sorted(random.sample(range(1, 101), spec["samples"]))
        for prec in spec["prec"]:
            context.prec = prec
            for expts in spec["expts"]:
                (emin, emax) = expts
                if emin == "rand":
                    context.Emin = random.randrange((-1000), 0)
                    context.Emax = random.randrange(prec, 1000)
                else:
                    (context.Emin, context.Emax) = (emin, emax)
                if prec > context.Emax:
                    continue
                log(
                    "    prec: %d  emin: %d  emax: %d",
                    (context.prec, context.Emin, context.Emax),
                )
                restr_range = 9999 if (context.Emax > 9999) else (context.Emax + 99)
                for rounding in RoundModes:
                    context.rounding = rounding
                    context.capitals = random.randrange(2)
                    if spec["clamp"] == "rand":
                        context.clamp = random.randrange(2)
                    else:
                        context.clamp = spec["clamp"]
                    exprange = context.c.Emax
                    testfunc(method, prec, exprange, restr_range, spec["iter"], stat)
    log(("    result types: %s" % sorted([t for t in stat.items()])))


def test_unary(method, prec, exp_range, restricted_range, itr, stat):
    "Iterate a unary function through many test cases."
    if method in UnaryRestricted:
        exp_range = restricted_range
    for op in all_unary(prec, exp_range, itr):
        t = TestSet(method, op)
        try:
            if not convert(t):
                continue
            callfuncs(t)
            verify(t, stat)
        except VerifyError as err:
            log(err)
    if not method.startswith("__"):
        for op in unary_optarg(prec, exp_range, itr):
            t = TestSet(method, op)
            try:
                if not convert(t):
                    continue
                callfuncs(t)
                verify(t, stat)
            except VerifyError as err:
                log(err)


def test_binary(method, prec, exp_range, restricted_range, itr, stat):
    "Iterate a binary function through many test cases."
    if method in BinaryRestricted:
        exp_range = restricted_range
    for op in all_binary(prec, exp_range, itr):
        t = TestSet(method, op)
        try:
            if not convert(t):
                continue
            callfuncs(t)
            verify(t, stat)
        except VerifyError as err:
            log(err)
    if not method.startswith("__"):
        for op in binary_optarg(prec, exp_range, itr):
            t = TestSet(method, op)
            try:
                if not convert(t):
                    continue
                callfuncs(t)
                verify(t, stat)
            except VerifyError as err:
                log(err)


def test_ternary(method, prec, exp_range, restricted_range, itr, stat):
    "Iterate a ternary function through many test cases."
    if method in TernaryRestricted:
        exp_range = restricted_range
    for op in all_ternary(prec, exp_range, itr):
        t = TestSet(method, op)
        try:
            if not convert(t):
                continue
            callfuncs(t)
            verify(t, stat)
        except VerifyError as err:
            log(err)
    if not method.startswith("__"):
        for op in ternary_optarg(prec, exp_range, itr):
            t = TestSet(method, op)
            try:
                if not convert(t):
                    continue
                callfuncs(t)
                verify(t, stat)
            except VerifyError as err:
                log(err)


def test_format(method, prec, exp_range, restricted_range, itr, stat):
    "Iterate the __format__ method through many test cases."
    for op in all_unary(prec, exp_range, itr):
        fmt1 = rand_format(chr(random.randrange(0, 128)), "EeGgn")
        fmt2 = rand_locale()
        for fmt in (fmt1, fmt2):
            fmtop = (op[0], fmt)
            t = TestSet(method, fmtop)
            try:
                if not convert(t, convstr=False):
                    continue
                callfuncs(t)
                verify(t, stat)
            except VerifyError as err:
                log(err)
    for op in all_unary(prec, 9999, itr):
        fmt1 = rand_format(chr(random.randrange(0, 128)), "Ff%")
        fmt2 = rand_locale()
        for fmt in (fmt1, fmt2):
            fmtop = (op[0], fmt)
            t = TestSet(method, fmtop)
            try:
                if not convert(t, convstr=False):
                    continue
                callfuncs(t)
                verify(t, stat)
            except VerifyError as err:
                log(err)


def test_round(method, prec, exprange, restricted_range, itr, stat):
    "Iterate the __round__ method through many test cases."
    for op in all_unary(prec, 9999, itr):
        n = random.randrange(10)
        roundop = (op[0], n)
        t = TestSet(method, roundop)
        try:
            if not convert(t):
                continue
            callfuncs(t)
            verify(t, stat)
        except VerifyError as err:
            log(err)


def test_from_float(method, prec, exprange, restricted_range, itr, stat):
    "Iterate the __float__ method through many test cases."
    for rounding in RoundModes:
        context.rounding = rounding
        for i in range(1000):
            f = randfloat()
            op = (f,) if method.startswith("context.") else ("sNaN", f)
            t = TestSet(method, op)
            try:
                if not convert(t):
                    continue
                callfuncs(t)
                verify(t, stat)
            except VerifyError as err:
                log(err)


def randcontext(exprange):
    c = Context(C.Context(), P.Context())
    c.Emax = random.randrange(1, (exprange + 1))
    c.Emin = random.randrange((-exprange), 0)
    maxprec = 100 if (c.Emax >= 100) else c.Emax
    c.prec = random.randrange(1, (maxprec + 1))
    c.clamp = random.randrange(2)
    c.clear_traps()
    return c


def test_quantize_api(method, prec, exprange, restricted_range, itr, stat):
    "Iterate the 'quantize' method through many test cases, using\n       the optional arguments."
    for op in all_binary(prec, restricted_range, itr):
        for rounding in RoundModes:
            c = randcontext(exprange)
            quantizeop = (op[0], op[1], rounding, c)
            t = TestSet(method, quantizeop)
            try:
                if not convert(t):
                    continue
                callfuncs(t)
                verify(t, stat)
            except VerifyError as err:
                log(err)


def check_untested(funcdict, c_cls, p_cls):
    "Determine untested, C-only and Python-only attributes.\n       Uncomment print lines for debugging."
    c_attr = set(dir(c_cls))
    p_attr = set(dir(p_cls))
    intersect = c_attr & p_attr
    funcdict["c_only"] = tuple(sorted((c_attr - intersect)))
    funcdict["p_only"] = tuple(sorted((p_attr - intersect)))
    tested = set()
    for lst in funcdict.values():
        for v in lst:
            v = v.replace("context.", "") if (c_cls == C.Context) else v
            tested.add(v)
    funcdict["untested"] = tuple(sorted((intersect - tested)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="deccheck.py")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--short",
        dest="time",
        action="store_const",
        const="short",
        default="short",
        help="short test (default)",
    )
    group.add_argument(
        "--medium",
        dest="time",
        action="store_const",
        const="medium",
        default="short",
        help="medium test (reasonable run time)",
    )
    group.add_argument(
        "--long",
        dest="time",
        action="store_const",
        const="long",
        default="short",
        help="long test (long run time)",
    )
    group.add_argument(
        "--all",
        dest="time",
        action="store_const",
        const="all",
        default="short",
        help="all tests (excessive run time)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--single",
        dest="single",
        nargs=1,
        default=False,
        metavar="TEST",
        help="run a single test",
    )
    group.add_argument(
        "--multicore",
        dest="multicore",
        action="store_true",
        default=False,
        help="use all available cores",
    )
    args = parser.parse_args()
    assert (args.single is False) or (args.multicore is False)
    if args.single:
        args.single = args.single[0]
    base_expts = [(C.MIN_EMIN, C.MAX_EMAX)]
    if C.MAX_EMAX == 999999999999999999:
        base_expts.append(((-999999999), 999999999))
    base = {
        "expts": base_expts,
        "prec": [],
        "clamp": "rand",
        "iter": None,
        "samples": None,
    }
    small = {
        "prec": [1, 2, 3, 4, 5],
        "expts": [((-1), 1), ((-2), 2), ((-3), 3), ((-4), 4), ((-5), 5)],
        "clamp": "rand",
        "iter": None,
    }
    ieee = [
        {"prec": [7], "expts": [((-95), 96)], "clamp": 1, "iter": None},
        {"prec": [16], "expts": [((-383), 384)], "clamp": 1, "iter": None},
        {"prec": [34], "expts": [((-6143), 6144)], "clamp": 1, "iter": None},
    ]
    if args.time == "medium":
        base["expts"].append(("rand", "rand"))
        base["samples"] = 5
        testspecs = ([small] + ieee) + [base]
    elif args.time == "long":
        base["expts"].append(("rand", "rand"))
        base["samples"] = 10
        testspecs = ([small] + ieee) + [base]
    elif args.time == "all":
        base["expts"].append(("rand", "rand"))
        base["samples"] = 100
        testspecs = ([small] + ieee) + [base]
    else:
        rand_ieee = random.choice(ieee)
        base["iter"] = small["iter"] = rand_ieee["iter"] = 1
        base["samples"] = 1
        base["expts"] = [random.choice(base_expts)]
        prec = random.randrange(1, 6)
        small["prec"] = [prec]
        small["expts"] = [((-prec), prec)]
        testspecs = [small, rand_ieee, base]
    check_untested(Functions, C.Decimal, P.Decimal)
    check_untested(ContextFunctions, C.Context, P.Context)
    if args.multicore:
        q = Queue()
    elif args.single:
        log("Random seed: %d", RANDSEED)
    else:
        log("\n\nRandom seed: %d\n\n", RANDSEED)
    FOUND_METHOD = False

    def do_single(method, f):
        global FOUND_METHOD
        if args.multicore:
            q.put(method)
        elif (not args.single) or (args.single == method):
            FOUND_METHOD = True
            f()

    for method in (Functions["unary"] + Functions["unary_ctx"]) + Functions[
        "unary_rnd_ctx"
    ]:
        do_single(method, (lambda: test_method(method, testspecs, test_unary)))
    for method in Functions["binary"] + Functions["binary_ctx"]:
        do_single(method, (lambda: test_method(method, testspecs, test_binary)))
    for method in Functions["ternary"] + Functions["ternary_ctx"]:
        name = "__powmod__" if (method == "__pow__") else method
        do_single(name, (lambda: test_method(method, testspecs, test_ternary)))
    do_single("__format__", (lambda: test_method("__format__", testspecs, test_format)))
    do_single("__round__", (lambda: test_method("__round__", testspecs, test_round)))
    do_single(
        "from_float", (lambda: test_method("from_float", testspecs, test_from_float))
    )
    do_single(
        "quantize_api", (lambda: test_method("quantize", testspecs, test_quantize_api))
    )
    for method in ContextFunctions["unary"]:
        do_single(method, (lambda: test_method(method, testspecs, test_unary)))
    for method in ContextFunctions["binary"]:
        do_single(method, (lambda: test_method(method, testspecs, test_binary)))
    for method in ContextFunctions["ternary"]:
        name = "context.powmod" if (method == "context.power") else method
        do_single(name, (lambda: test_method(method, testspecs, test_ternary)))
    do_single(
        "context.create_decimal_from_float",
        (
            lambda: test_method(
                "context.create_decimal_from_float", testspecs, test_from_float
            )
        ),
    )
    if args.multicore:
        error = Event()
        write_lock = Lock()

        def write_output(out, returncode):
            if returncode != 0:
                error.set()
            with write_lock:
                sys.stdout.buffer.write((out + b"\n"))
                sys.stdout.buffer.flush()

        def tfunc():
            while not error.is_set():
                try:
                    test = q.get(block=False, timeout=(-1))
                except Empty:
                    return
                cmd = [
                    sys.executable,
                    "deccheck.py",
                    ("--%s" % args.time),
                    "--single",
                    test,
                ]
                p = subprocess.Popen(cmd, stdout=PIPE, stderr=STDOUT)
                (out, _) = p.communicate()
                write_output(out, p.returncode)

        N = os.cpu_count()
        t = N * [None]
        for i in range(N):
            t[i] = Thread(target=tfunc)
            t[i].start()
        for i in range(N):
            t[i].join()
        sys.exit((1 if error.is_set() else 0))
    elif args.single:
        if not FOUND_METHOD:
            log(('\nerror: cannot find method "%s"' % args.single))
            EXIT_STATUS = 1
        sys.exit(EXIT_STATUS)
    else:
        sys.exit(EXIT_STATUS)
