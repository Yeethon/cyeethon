"Random variable generators.\n\n    bytes\n    -----\n           uniform bytes (values between 0 and 255)\n\n    integers\n    --------\n           uniform within range\n\n    sequences\n    ---------\n           pick random element\n           pick random sample\n           pick weighted random sample\n           generate random permutation\n\n    distributions on the real line:\n    ------------------------------\n           uniform\n           triangular\n           normal (Gaussian)\n           lognormal\n           negative exponential\n           gamma\n           beta\n           pareto\n           Weibull\n\n    distributions on the circle (angles 0 to 2pi)\n    ---------------------------------------------\n           circular uniform\n           von Mises\n\nGeneral notes on the underlying Mersenne Twister core generator:\n\n* The period is 2**19937-1.\n* It is one of the most extensively tested generators in existence.\n* The random() method is implemented in C, executes in a single Python step,\n  and is, therefore, threadsafe.\n\n"
from warnings import warn as _warn
from math import log as _log, exp as _exp, pi as _pi, e as _e, ceil as _ceil
from math import sqrt as _sqrt, acos as _acos, cos as _cos, sin as _sin
from math import tau as TWOPI, floor as _floor, isfinite as _isfinite
from os import urandom as _urandom
from _collections_abc import Set as _Set, Sequence as _Sequence
from operator import index as _index
from itertools import accumulate as _accumulate, repeat as _repeat
from bisect import bisect as _bisect
import os as _os
import _random

try:
    from _sha512 import sha512 as _sha512
except ImportError:
    from hashlib import sha512 as _sha512
__all__ = [
    "Random",
    "SystemRandom",
    "betavariate",
    "choice",
    "choices",
    "expovariate",
    "gammavariate",
    "gauss",
    "getrandbits",
    "getstate",
    "lognormvariate",
    "normalvariate",
    "paretovariate",
    "randbytes",
    "randint",
    "random",
    "randrange",
    "sample",
    "seed",
    "setstate",
    "shuffle",
    "triangular",
    "uniform",
    "vonmisesvariate",
    "weibullvariate",
]
NV_MAGICCONST = (4 * _exp((-0.5))) / _sqrt(2.0)
LOG4 = _log(4.0)
SG_MAGICCONST = 1.0 + _log(4.5)
BPF = 53
RECIP_BPF = 2 ** (-BPF)
_ONE = 1


class Random(_random.Random):
    "Random number generator base class used by bound module functions.\n\n    Used to instantiate instances of Random to get generators that don't\n    share state.\n\n    Class Random can also be subclassed if you want to use a different basic\n    generator of your own devising: in that case, override the following\n    methods:  random(), seed(), getstate(), and setstate().\n    Optionally, implement a getrandbits() method so that randrange()\n    can cover arbitrarily large ranges.\n\n    "
    VERSION = 3

    def __init__(self, x=None):
        "Initialize an instance.\n\n        Optional argument x controls seeding, as for Random.seed().\n        "
        self.seed(x)
        self.gauss_next = None

    def seed(self, a=None, version=2):
        "Initialize internal state from a seed.\n\n        The only supported seed types are None, int, float,\n        str, bytes, and bytearray.\n\n        None or no argument seeds from current time or from an operating\n        system specific randomness source if available.\n\n        If *a* is an int, all bits are used.\n\n        For version 2 (the default), all of the bits are used if *a* is a str,\n        bytes, or bytearray.  For version 1 (provided for reproducing random\n        sequences from older versions of Python), the algorithm for str and\n        bytes generates a narrower range of seeds.\n\n        "
        if (version == 1) and isinstance(a, (str, bytes)):
            a = a.decode("latin-1") if isinstance(a, bytes) else a
            x = (ord(a[0]) << 7) if a else 0
            for c in map(ord, a):
                x = ((1000003 * x) ^ c) & 18446744073709551615
            x ^= len(a)
            a = (-2) if (x == (-1)) else x
        elif (version == 2) and isinstance(a, (str, bytes, bytearray)):
            if isinstance(a, str):
                a = a.encode()
            a += _sha512(a).digest()
            a = int.from_bytes(a, "big")
        elif not isinstance(a, (type(None), int, float, str, bytes, bytearray)):
            _warn(
                "Seeding based on hashing is deprecated\nsince Python 3.9 and will be removed in a subsequent version. The only \nsupported seed types are: None, int, float, str, bytes, and bytearray.",
                DeprecationWarning,
                2,
            )
        super().seed(a)
        self.gauss_next = None

    def getstate(self):
        "Return internal state; can be passed to setstate() later."
        return (self.VERSION, super().getstate(), self.gauss_next)

    def setstate(self, state):
        "Restore internal state from object returned by getstate()."
        version = state[0]
        if version == 3:
            (version, internalstate, self.gauss_next) = state
            super().setstate(internalstate)
        elif version == 2:
            (version, internalstate, self.gauss_next) = state
            try:
                internalstate = tuple(((x % (2 ** 32)) for x in internalstate))
            except ValueError as e:
                raise TypeError from e
            super().setstate(internalstate)
        else:
            raise ValueError(
                (
                    "state with version %s passed to Random.setstate() of version %s"
                    % (version, self.VERSION)
                )
            )

    def __getstate__(self):
        return self.getstate()

    def __setstate__(self, state):
        self.setstate(state)

    def __reduce__(self):
        return (self.__class__, (), self.getstate())

    def __init_subclass__(cls, /, **kwargs):
        "Control how subclasses generate random integers.\n\n        The algorithm a subclass can use depends on the random() and/or\n        getrandbits() implementation available to it and determines\n        whether it can generate random integers from arbitrarily large\n        ranges.\n        "
        for c in cls.__mro__:
            if "_randbelow" in c.__dict__:
                break
            if "getrandbits" in c.__dict__:
                cls._randbelow = cls._randbelow_with_getrandbits
                break
            if "random" in c.__dict__:
                cls._randbelow = cls._randbelow_without_getrandbits
                break

    def _randbelow_with_getrandbits(self, n):
        "Return a random int in the range [0,n).  Returns 0 if n==0."
        if not n:
            return 0
        getrandbits = self.getrandbits
        k = n.bit_length()
        r = getrandbits(k)
        while r >= n:
            r = getrandbits(k)
        return r

    def _randbelow_without_getrandbits(self, n, maxsize=(1 << BPF)):
        "Return a random int in the range [0,n).  Returns 0 if n==0.\n\n        The implementation does not use getrandbits, but only random.\n        "
        random = self.random
        if n >= maxsize:
            _warn(
                "Underlying random() generator does not supply \nenough bits to choose from a population range this large.\nTo remove the range limitation, add a getrandbits() method."
            )
            return _floor((random() * n))
        if n == 0:
            return 0
        rem = maxsize % n
        limit = (maxsize - rem) / maxsize
        r = random()
        while r >= limit:
            r = random()
        return _floor((r * maxsize)) % n

    _randbelow = _randbelow_with_getrandbits

    def randbytes(self, n):
        "Generate n random bytes."
        return self.getrandbits((n * 8)).to_bytes(n, "little")

    def randrange(self, start, stop=None, step=_ONE):
        "Choose a random item from range(start, stop[, step]).\n\n        This fixes the problem with randint() which includes the\n        endpoint; in Python this is usually not what you want.\n\n        "
        try:
            istart = _index(start)
        except TypeError:
            istart = int(start)
            if istart != start:
                _warn(
                    "randrange() will raise TypeError in the future",
                    DeprecationWarning,
                    2,
                )
                raise ValueError("non-integer arg 1 for randrange()")
            _warn(
                "non-integer arguments to randrange() have been deprecated since Python 3.10 and will be removed in a subsequent version",
                DeprecationWarning,
                2,
            )
        if stop is None:
            if step is not _ONE:
                raise TypeError("Missing a non-None stop argument")
            if istart > 0:
                return self._randbelow(istart)
            raise ValueError("empty range for randrange()")
        try:
            istop = _index(stop)
        except TypeError:
            istop = int(stop)
            if istop != stop:
                _warn(
                    "randrange() will raise TypeError in the future",
                    DeprecationWarning,
                    2,
                )
                raise ValueError("non-integer stop for randrange()")
            _warn(
                "non-integer arguments to randrange() have been deprecated since Python 3.10 and will be removed in a subsequent version",
                DeprecationWarning,
                2,
            )
        width = istop - istart
        try:
            istep = _index(step)
        except TypeError:
            istep = int(step)
            if istep != step:
                _warn(
                    "randrange() will raise TypeError in the future",
                    DeprecationWarning,
                    2,
                )
                raise ValueError("non-integer step for randrange()")
            _warn(
                "non-integer arguments to randrange() have been deprecated since Python 3.10 and will be removed in a subsequent version",
                DeprecationWarning,
                2,
            )
        if istep == 1:
            if width > 0:
                return istart + self._randbelow(width)
            raise ValueError(
                ("empty range for randrange() (%d, %d, %d)" % (istart, istop, width))
            )
        if istep > 0:
            n = ((width + istep) - 1) // istep
        elif istep < 0:
            n = ((width + istep) + 1) // istep
        else:
            raise ValueError("zero step for randrange()")
        if n <= 0:
            raise ValueError("empty range for randrange()")
        return istart + (istep * self._randbelow(n))

    def randint(self, a, b):
        "Return random integer in range [a, b], including both end points.\n        "
        return self.randrange(a, (b + 1))

    def choice(self, seq):
        "Choose a random element from a non-empty sequence."
        return seq[self._randbelow(len(seq))]

    def shuffle(self, x, random=None):
        "Shuffle list x in place, and return None.\n\n        Optional argument random is a 0-argument function returning a\n        random float in [0.0, 1.0); if it is the default None, the\n        standard random.random will be used.\n\n        "
        if random is None:
            randbelow = self._randbelow
            for i in reversed(range(1, len(x))):
                j = randbelow((i + 1))
                (x[i], x[j]) = (x[j], x[i])
        else:
            _warn(
                "The *random* parameter to shuffle() has been deprecated\nsince Python 3.9 and will be removed in a subsequent version.",
                DeprecationWarning,
                2,
            )
            floor = _floor
            for i in reversed(range(1, len(x))):
                j = floor((random() * (i + 1)))
                (x[i], x[j]) = (x[j], x[i])

    def sample(self, population, k, *, counts=None):
        "Chooses k unique random elements from a population sequence or set.\n\n        Returns a new list containing elements from the population while\n        leaving the original population unchanged.  The resulting list is\n        in selection order so that all sub-slices will also be valid random\n        samples.  This allows raffle winners (the sample) to be partitioned\n        into grand prize and second place winners (the subslices).\n\n        Members of the population need not be hashable or unique.  If the\n        population contains repeats, then each occurrence is a possible\n        selection in the sample.\n\n        Repeated elements can be specified one at a time or with the optional\n        counts parameter.  For example:\n\n            sample(['red', 'blue'], counts=[4, 2], k=5)\n\n        is equivalent to:\n\n            sample(['red', 'red', 'red', 'red', 'blue', 'blue'], k=5)\n\n        To choose a sample from a range of integers, use range() for the\n        population argument.  This is especially fast and space efficient\n        for sampling from a large population:\n\n            sample(range(10000000), 60)\n\n        "
        if not isinstance(population, _Sequence):
            if isinstance(population, _Set):
                _warn(
                    "Sampling from a set deprecated\nsince Python 3.9 and will be removed in a subsequent version.",
                    DeprecationWarning,
                    2,
                )
                population = tuple(population)
            else:
                raise TypeError(
                    "Population must be a sequence.  For dicts or sets, use sorted(d)."
                )
        n = len(population)
        if counts is not None:
            cum_counts = list(_accumulate(counts))
            if len(cum_counts) != n:
                raise ValueError("The number of counts does not match the population")
            total = cum_counts.pop()
            if not isinstance(total, int):
                raise TypeError("Counts must be integers")
            if total <= 0:
                raise ValueError("Total of counts must be greater than zero")
            selections = self.sample(range(total), k=k)
            bisect = _bisect
            return [population[bisect(cum_counts, s)] for s in selections]
        randbelow = self._randbelow
        if not (0 <= k <= n):
            raise ValueError("Sample larger than population or is negative")
        result = [None] * k
        setsize = 21
        if k > 5:
            setsize += 4 ** _ceil(_log((k * 3), 4))
        if n <= setsize:
            pool = list(population)
            for i in range(k):
                j = randbelow((n - i))
                result[i] = pool[j]
                pool[j] = pool[((n - i) - 1)]
        else:
            selected = set()
            selected_add = selected.add
            for i in range(k):
                j = randbelow(n)
                while j in selected:
                    j = randbelow(n)
                selected_add(j)
                result[i] = population[j]
        return result

    def choices(self, population, weights=None, *, cum_weights=None, k=1):
        "Return a k sized list of population elements chosen with replacement.\n\n        If the relative weights or cumulative weights are not specified,\n        the selections are made with equal probability.\n\n        "
        random = self.random
        n = len(population)
        if cum_weights is None:
            if weights is None:
                floor = _floor
                n += 0.0
                return [population[floor((random() * n))] for i in _repeat(None, k)]
            try:
                cum_weights = list(_accumulate(weights))
            except TypeError:
                if not isinstance(weights, int):
                    raise
                k = weights
                raise TypeError(
                    f"The number of choices must be a keyword argument: k={k!r}"
                ) from None
        elif weights is not None:
            raise TypeError("Cannot specify both weights and cumulative weights")
        if len(cum_weights) != n:
            raise ValueError("The number of weights does not match the population")
        total = cum_weights[(-1)] + 0.0
        if total <= 0.0:
            raise ValueError("Total of weights must be greater than zero")
        if not _isfinite(total):
            raise ValueError("Total of weights must be finite")
        bisect = _bisect
        hi = n - 1
        return [
            population[bisect(cum_weights, (random() * total), 0, hi)]
            for i in _repeat(None, k)
        ]

    def uniform(self, a, b):
        "Get a random number in the range [a, b) or [a, b] depending on rounding."
        return a + ((b - a) * self.random())

    def triangular(self, low=0.0, high=1.0, mode=None):
        "Triangular distribution.\n\n        Continuous distribution bounded by given lower and upper limits,\n        and having a given mode value in-between.\n\n        http://en.wikipedia.org/wiki/Triangular_distribution\n\n        "
        u = self.random()
        try:
            c = 0.5 if (mode is None) else ((mode - low) / (high - low))
        except ZeroDivisionError:
            return low
        if u > c:
            u = 1.0 - u
            c = 1.0 - c
            (low, high) = (high, low)
        return low + ((high - low) * _sqrt((u * c)))

    def normalvariate(self, mu, sigma):
        "Normal distribution.\n\n        mu is the mean, and sigma is the standard deviation.\n\n        "
        random = self.random
        while True:
            u1 = random()
            u2 = 1.0 - random()
            z = (NV_MAGICCONST * (u1 - 0.5)) / u2
            zz = (z * z) / 4.0
            if zz <= (-_log(u2)):
                break
        return mu + (z * sigma)

    def gauss(self, mu, sigma):
        "Gaussian distribution.\n\n        mu is the mean, and sigma is the standard deviation.  This is\n        slightly faster than the normalvariate() function.\n\n        Not thread-safe without a lock around calls.\n\n        "
        random = self.random
        z = self.gauss_next
        self.gauss_next = None
        if z is None:
            x2pi = random() * TWOPI
            g2rad = _sqrt(((-2.0) * _log((1.0 - random()))))
            z = _cos(x2pi) * g2rad
            self.gauss_next = _sin(x2pi) * g2rad
        return mu + (z * sigma)

    def lognormvariate(self, mu, sigma):
        "Log normal distribution.\n\n        If you take the natural logarithm of this distribution, you'll get a\n        normal distribution with mean mu and standard deviation sigma.\n        mu can have any value, and sigma must be greater than zero.\n\n        "
        return _exp(self.normalvariate(mu, sigma))

    def expovariate(self, lambd):
        'Exponential distribution.\n\n        lambd is 1.0 divided by the desired mean.  It should be\n        nonzero.  (The parameter would be called "lambda", but that is\n        a reserved word in Python.)  Returned values range from 0 to\n        positive infinity if lambd is positive, and from negative\n        infinity to 0 if lambd is negative.\n\n        '
        return (-_log((1.0 - self.random()))) / lambd

    def vonmisesvariate(self, mu, kappa):
        "Circular data distribution.\n\n        mu is the mean angle, expressed in radians between 0 and 2*pi, and\n        kappa is the concentration parameter, which must be greater than or\n        equal to zero.  If kappa is equal to zero, this distribution reduces\n        to a uniform random angle over the range 0 to 2*pi.\n\n        "
        random = self.random
        if kappa <= 1e-06:
            return TWOPI * random()
        s = 0.5 / kappa
        r = s + _sqrt((1.0 + (s * s)))
        while True:
            u1 = random()
            z = _cos((_pi * u1))
            d = z / (r + z)
            u2 = random()
            if (u2 < (1.0 - (d * d))) or (u2 <= ((1.0 - d) * _exp(d))):
                break
        q = 1.0 / r
        f = (q + z) / (1.0 + (q * z))
        u3 = random()
        if u3 > 0.5:
            theta = (mu + _acos(f)) % TWOPI
        else:
            theta = (mu - _acos(f)) % TWOPI
        return theta

    def gammavariate(self, alpha, beta):
        "Gamma distribution.  Not the gamma function!\n\n        Conditions on the parameters are alpha > 0 and beta > 0.\n\n        The probability distribution function is:\n\n                    x ** (alpha - 1) * math.exp(-x / beta)\n          pdf(x) =  --------------------------------------\n                      math.gamma(alpha) * beta ** alpha\n\n        "
        if (alpha <= 0.0) or (beta <= 0.0):
            raise ValueError("gammavariate: alpha and beta must be > 0.0")
        random = self.random
        if alpha > 1.0:
            ainv = _sqrt(((2.0 * alpha) - 1.0))
            bbb = alpha - LOG4
            ccc = alpha + ainv
            while True:
                u1 = random()
                if not (1e-07 < u1 < 0.9999999):
                    continue
                u2 = 1.0 - random()
                v = _log((u1 / (1.0 - u1))) / ainv
                x = alpha * _exp(v)
                z = (u1 * u1) * u2
                r = (bbb + (ccc * v)) - x
                if (((r + SG_MAGICCONST) - (4.5 * z)) >= 0.0) or (r >= _log(z)):
                    return x * beta
        elif alpha == 1.0:
            return (-_log((1.0 - random()))) * beta
        else:
            while True:
                u = random()
                b = (_e + alpha) / _e
                p = b * u
                if p <= 1.0:
                    x = p ** (1.0 / alpha)
                else:
                    x = -_log(((b - p) / alpha))
                u1 = random()
                if p > 1.0:
                    if u1 <= (x ** (alpha - 1.0)):
                        break
                elif u1 <= _exp((-x)):
                    break
            return x * beta

    def betavariate(self, alpha, beta):
        "Beta distribution.\n\n        Conditions on the parameters are alpha > 0 and beta > 0.\n        Returned values range between 0 and 1.\n\n        "
        y = self.gammavariate(alpha, 1.0)
        if y:
            return y / (y + self.gammavariate(beta, 1.0))
        return 0.0

    def paretovariate(self, alpha):
        "Pareto distribution.  alpha is the shape parameter."
        u = 1.0 - self.random()
        return u ** ((-1.0) / alpha)

    def weibullvariate(self, alpha, beta):
        "Weibull distribution.\n\n        alpha is the scale parameter and beta is the shape parameter.\n\n        "
        u = 1.0 - self.random()
        return alpha * ((-_log(u)) ** (1.0 / beta))


class SystemRandom(Random):
    "Alternate random number generator using sources provided\n    by the operating system (such as /dev/urandom on Unix or\n    CryptGenRandom on Windows).\n\n     Not available on all systems (see os.urandom() for details).\n\n    "

    def random(self):
        "Get the next random number in the range [0.0, 1.0)."
        return (int.from_bytes(_urandom(7), "big") >> 3) * RECIP_BPF

    def getrandbits(self, k):
        "getrandbits(k) -> x.  Generates an int with k random bits."
        if k < 0:
            raise ValueError("number of bits must be non-negative")
        numbytes = (k + 7) // 8
        x = int.from_bytes(_urandom(numbytes), "big")
        return x >> ((numbytes * 8) - k)

    def randbytes(self, n):
        "Generate n random bytes."
        return _urandom(n)

    def seed(self, *args, **kwds):
        "Stub method.  Not used for a system random number generator."
        return None

    def _notimplemented(self, *args, **kwds):
        "Method should not be called for a system random number generator."
        raise NotImplementedError("System entropy source does not have state.")

    getstate = setstate = _notimplemented


_inst = Random()
seed = _inst.seed
random = _inst.random
uniform = _inst.uniform
triangular = _inst.triangular
randint = _inst.randint
choice = _inst.choice
randrange = _inst.randrange
sample = _inst.sample
shuffle = _inst.shuffle
choices = _inst.choices
normalvariate = _inst.normalvariate
lognormvariate = _inst.lognormvariate
expovariate = _inst.expovariate
vonmisesvariate = _inst.vonmisesvariate
gammavariate = _inst.gammavariate
gauss = _inst.gauss
betavariate = _inst.betavariate
paretovariate = _inst.paretovariate
weibullvariate = _inst.weibullvariate
getstate = _inst.getstate
setstate = _inst.setstate
getrandbits = _inst.getrandbits
randbytes = _inst.randbytes


def _test_generator(n, func, args):
    from statistics import stdev, fmean as mean
    from time import perf_counter

    t0 = perf_counter()
    data = [func(*args) for i in _repeat(None, n)]
    t1 = perf_counter()
    xbar = mean(data)
    sigma = stdev(data, xbar)
    low = min(data)
    high = max(data)
    print(f"{(t1 - t0):.3f} sec, {n} times {func.__name__}")
    print(("avg %g, stddev %g, min %g, max %g\n" % (xbar, sigma, low, high)))


def _test(N=2000):
    _test_generator(N, random, ())
    _test_generator(N, normalvariate, (0.0, 1.0))
    _test_generator(N, lognormvariate, (0.0, 1.0))
    _test_generator(N, vonmisesvariate, (0.0, 1.0))
    _test_generator(N, gammavariate, (0.01, 1.0))
    _test_generator(N, gammavariate, (0.1, 1.0))
    _test_generator(N, gammavariate, (0.1, 2.0))
    _test_generator(N, gammavariate, (0.5, 1.0))
    _test_generator(N, gammavariate, (0.9, 1.0))
    _test_generator(N, gammavariate, (1.0, 1.0))
    _test_generator(N, gammavariate, (2.0, 1.0))
    _test_generator(N, gammavariate, (20.0, 1.0))
    _test_generator(N, gammavariate, (200.0, 1.0))
    _test_generator(N, gauss, (0.0, 1.0))
    _test_generator(N, betavariate, (3.0, 3.0))
    _test_generator(N, triangular, (0.0, 1.0, (1.0 / 3.0)))


if hasattr(_os, "fork"):
    _os.register_at_fork(after_in_child=_inst.seed)
if __name__ == "__main__":
    _test()
