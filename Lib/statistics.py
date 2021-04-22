'\nBasic statistics module.\n\nThis module provides functions for calculating statistics of data, including\naverages, variance, and standard deviation.\n\nCalculating averages\n--------------------\n\n==================  ==================================================\nFunction            Description\n==================  ==================================================\nmean                Arithmetic mean (average) of data.\nfmean               Fast, floating point arithmetic mean.\ngeometric_mean      Geometric mean of data.\nharmonic_mean       Harmonic mean of data.\nmedian              Median (middle value) of data.\nmedian_low          Low median of data.\nmedian_high         High median of data.\nmedian_grouped      Median, or 50th percentile, of grouped data.\nmode                Mode (most common value) of data.\nmultimode           List of modes (most common values of data).\nquantiles           Divide data into intervals with equal probability.\n==================  ==================================================\n\nCalculate the arithmetic mean ("the average") of data:\n\n>>> mean([-1.0, 2.5, 3.25, 5.75])\n2.625\n\n\nCalculate the standard median of discrete data:\n\n>>> median([2, 3, 4, 5])\n3.5\n\n\nCalculate the median, or 50th percentile, of data grouped into class intervals\ncentred on the data values provided. E.g. if your data points are rounded to\nthe nearest whole number:\n\n>>> median_grouped([2, 2, 3, 3, 3, 4])  #doctest: +ELLIPSIS\n2.8333333333...\n\nThis should be interpreted in this way: you have two data points in the class\ninterval 1.5-2.5, three data points in the class interval 2.5-3.5, and one in\nthe class interval 3.5-4.5. The median of these data points is 2.8333...\n\n\nCalculating variability or spread\n---------------------------------\n\n==================  =============================================\nFunction            Description\n==================  =============================================\npvariance           Population variance of data.\nvariance            Sample variance of data.\npstdev              Population standard deviation of data.\nstdev               Sample standard deviation of data.\n==================  =============================================\n\nCalculate the standard deviation of sample data:\n\n>>> stdev([2.5, 3.25, 5.5, 11.25, 11.75])  #doctest: +ELLIPSIS\n4.38961843444...\n\nIf you have previously calculated the mean, you can pass it as the optional\nsecond argument to the four "spread" functions to avoid recalculating it:\n\n>>> data = [1, 2, 2, 4, 4, 4, 5, 6]\n>>> mu = mean(data)\n>>> pvariance(data, mu)\n2.5\n\n\nExceptions\n----------\n\nA single exception is defined: StatisticsError is a subclass of ValueError.\n\n'
__all__ = [
    "NormalDist",
    "StatisticsError",
    "fmean",
    "geometric_mean",
    "harmonic_mean",
    "mean",
    "median",
    "median_grouped",
    "median_high",
    "median_low",
    "mode",
    "multimode",
    "pstdev",
    "pvariance",
    "quantiles",
    "stdev",
    "variance",
]
import math
import numbers
import random
from fractions import Fraction
from decimal import Decimal
from itertools import groupby, repeat
from bisect import bisect_left, bisect_right
from math import hypot, sqrt, fabs, exp, erf, tau, log, fsum
from operator import itemgetter
from collections import Counter


class StatisticsError(ValueError):
    pass


def _sum(data, start=0):
    "_sum(data [, start]) -> (type, sum, count)\n\n    Return a high-precision sum of the given numeric data as a fraction,\n    together with the type to be converted to and the count of items.\n\n    If optional argument ``start`` is given, it is added to the total.\n    If ``data`` is empty, ``start`` (defaulting to 0) is returned.\n\n\n    Examples\n    --------\n\n    >>> _sum([3, 2.25, 4.5, -0.5, 1.0], 0.75)\n    (<class 'float'>, Fraction(11, 1), 5)\n\n    Some sources of round-off error will be avoided:\n\n    # Built-in sum returns zero.\n    >>> _sum([1e50, 1, -1e50] * 1000)\n    (<class 'float'>, Fraction(1000, 1), 3000)\n\n    Fractions and Decimals are also supported:\n\n    >>> from fractions import Fraction as F\n    >>> _sum([F(2, 3), F(7, 5), F(1, 4), F(5, 6)])\n    (<class 'fractions.Fraction'>, Fraction(63, 20), 4)\n\n    >>> from decimal import Decimal as D\n    >>> data = [D(\"0.1375\"), D(\"0.2108\"), D(\"0.3061\"), D(\"0.0419\")]\n    >>> _sum(data)\n    (<class 'decimal.Decimal'>, Fraction(6963, 10000), 4)\n\n    Mixed types are currently treated as an error, except that int is\n    allowed.\n    "
    count = 0
    (n, d) = _exact_ratio(start)
    partials = {d: n}
    partials_get = partials.get
    T = _coerce(int, type(start))
    for (typ, values) in groupby(data, type):
        T = _coerce(T, typ)
        for (n, d) in map(_exact_ratio, values):
            count += 1
            partials[d] = partials_get(d, 0) + n
    if None in partials:
        total = partials[None]
        assert not _isfinite(total)
    else:
        total = sum((Fraction(n, d) for (d, n) in sorted(partials.items())))
    return (T, total, count)


def _isfinite(x):
    try:
        return x.is_finite()
    except AttributeError:
        return math.isfinite(x)


def _coerce(T, S):
    "Coerce types T and S to a common type, or raise TypeError.\n\n    Coercion rules are currently an implementation detail. See the CoerceTest\n    test class in test_statistics for details.\n    "
    assert T is not bool, "initial type T is bool"
    if T is S:
        return T
    if (S is int) or (S is bool):
        return T
    if T is int:
        return S
    if issubclass(S, T):
        return S
    if issubclass(T, S):
        return T
    if issubclass(T, int):
        return S
    if issubclass(S, int):
        return T
    if issubclass(T, Fraction) and issubclass(S, float):
        return S
    if issubclass(T, float) and issubclass(S, Fraction):
        return T
    msg = "don't know how to coerce %s and %s"
    raise TypeError((msg % (T.__name__, S.__name__)))


def _exact_ratio(x):
    "Return Real number x to exact (numerator, denominator) pair.\n\n    >>> _exact_ratio(0.25)\n    (1, 4)\n\n    x is expected to be an int, Fraction, Decimal or float.\n    "
    try:
        if (type(x) is float) or (type(x) is Decimal):
            return x.as_integer_ratio()
        try:
            return (x.numerator, x.denominator)
        except AttributeError:
            try:
                return x.as_integer_ratio()
            except AttributeError:
                pass
    except (OverflowError, ValueError):
        assert not _isfinite(x)
        return (x, None)
    msg = "can't convert type '{}' to numerator/denominator"
    raise TypeError(msg.format(type(x).__name__))


def _convert(value, T):
    "Convert value to given numeric type T."
    if type(value) is T:
        return value
    if issubclass(T, int) and (value.denominator != 1):
        T = float
    try:
        return T(value)
    except TypeError:
        if issubclass(T, Decimal):
            return T(value.numerator) / T(value.denominator)
        else:
            raise


def _find_lteq(a, x):
    "Locate the leftmost value exactly equal to x"
    i = bisect_left(a, x)
    if (i != len(a)) and (a[i] == x):
        return i
    raise ValueError


def _find_rteq(a, l, x):
    "Locate the rightmost value exactly equal to x"
    i = bisect_right(a, x, lo=l)
    if (i != (len(a) + 1)) and (a[(i - 1)] == x):
        return i - 1
    raise ValueError


def _fail_neg(values, errmsg="negative value"):
    "Iterate over values, failing if any are less than zero."
    for x in values:
        if x < 0:
            raise StatisticsError(errmsg)
        (yield x)


def mean(data):
    'Return the sample arithmetic mean of data.\n\n    >>> mean([1, 2, 3, 4, 4])\n    2.8\n\n    >>> from fractions import Fraction as F\n    >>> mean([F(3, 7), F(1, 21), F(5, 3), F(1, 3)])\n    Fraction(13, 21)\n\n    >>> from decimal import Decimal as D\n    >>> mean([D("0.5"), D("0.75"), D("0.625"), D("0.375")])\n    Decimal(\'0.5625\')\n\n    If ``data`` is empty, StatisticsError will be raised.\n    '
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if n < 1:
        raise StatisticsError("mean requires at least one data point")
    (T, total, count) = _sum(data)
    assert count == n
    return _convert((total / n), T)


def fmean(data):
    "Convert data to floats and compute the arithmetic mean.\n\n    This runs faster than the mean() function and it always returns a float.\n    If the input dataset is empty, it raises a StatisticsError.\n\n    >>> fmean([3.5, 4.0, 5.25])\n    4.25\n    "
    try:
        n = len(data)
    except TypeError:
        n = 0

        def count(iterable):
            nonlocal n
            for (n, x) in enumerate(iterable, start=1):
                (yield x)

        total = fsum(count(data))
    else:
        total = fsum(data)
    try:
        return total / n
    except ZeroDivisionError:
        raise StatisticsError("fmean requires at least one data point") from None


def geometric_mean(data):
    "Convert data to floats and compute the geometric mean.\n\n    Raises a StatisticsError if the input dataset is empty,\n    if it contains a zero, or if it contains a negative value.\n\n    No special efforts are made to achieve exact results.\n    (However, this may change in the future.)\n\n    >>> round(geometric_mean([54, 24, 36]), 9)\n    36.0\n    "
    try:
        return exp(fmean(map(log, data)))
    except ValueError:
        raise StatisticsError(
            "geometric mean requires a non-empty dataset  containing positive numbers"
        ) from None


def harmonic_mean(data, weights=None):
    "Return the harmonic mean of data.\n\n    The harmonic mean is the reciprocal of the arithmetic mean of the\n    reciprocals of the data.  It can be used for averaging ratios or\n    rates, for example speeds.\n\n    Suppose a car travels 40 km/hr for 5 km and then speeds-up to\n    60 km/hr for another 5 km. What is the average speed?\n\n        >>> harmonic_mean([40, 60])\n        48.0\n\n    Suppose a car travels 40 km/hr for 5 km, and when traffic clears,\n    speeds-up to 60 km/hr for the remaining 30 km of the journey. What\n    is the average speed?\n\n        >>> harmonic_mean([40, 60], weights=[5, 30])\n        56.0\n\n    If ``data`` is empty, or any element is less than zero,\n    ``harmonic_mean`` will raise ``StatisticsError``.\n    "
    if iter(data) is data:
        data = list(data)
    errmsg = "harmonic mean does not support negative values"
    n = len(data)
    if n < 1:
        raise StatisticsError("harmonic_mean requires at least one data point")
    elif (n == 1) and (weights is None):
        x = data[0]
        if isinstance(x, (numbers.Real, Decimal)):
            if x < 0:
                raise StatisticsError(errmsg)
            return x
        else:
            raise TypeError("unsupported type")
    if weights is None:
        weights = repeat(1, n)
        sum_weights = n
    else:
        if iter(weights) is weights:
            weights = list(weights)
        if len(weights) != n:
            raise StatisticsError("Number of weights does not match data size")
        (_, sum_weights, _) = _sum((w for w in _fail_neg(weights, errmsg)))
    try:
        data = _fail_neg(data, errmsg)
        (T, total, count) = _sum(
            (((w / x) if w else 0) for (w, x) in zip(weights, data))
        )
    except ZeroDivisionError:
        return 0
    if total <= 0:
        raise StatisticsError("Weighted sum must be positive")
    return _convert((sum_weights / total), T)


def median(data):
    "Return the median (middle value) of numeric data.\n\n    When the number of data points is odd, return the middle data point.\n    When the number of data points is even, the median is interpolated by\n    taking the average of the two middle values:\n\n    >>> median([1, 3, 5])\n    3\n    >>> median([1, 3, 5, 7])\n    4.0\n\n    "
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("no median for empty data")
    if (n % 2) == 1:
        return data[(n // 2)]
    else:
        i = n // 2
        return (data[(i - 1)] + data[i]) / 2


def median_low(data):
    "Return the low median of numeric data.\n\n    When the number of data points is odd, the middle value is returned.\n    When it is even, the smaller of the two middle values is returned.\n\n    >>> median_low([1, 3, 5])\n    3\n    >>> median_low([1, 3, 5, 7])\n    3\n\n    "
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("no median for empty data")
    if (n % 2) == 1:
        return data[(n // 2)]
    else:
        return data[((n // 2) - 1)]


def median_high(data):
    "Return the high median of data.\n\n    When the number of data points is odd, the middle value is returned.\n    When it is even, the larger of the two middle values is returned.\n\n    >>> median_high([1, 3, 5])\n    3\n    >>> median_high([1, 3, 5, 7])\n    5\n\n    "
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("no median for empty data")
    return data[(n // 2)]


def median_grouped(data, interval=1):
    "Return the 50th percentile (median) of grouped continuous data.\n\n    >>> median_grouped([1, 2, 2, 3, 4, 4, 4, 4, 4, 5])\n    3.7\n    >>> median_grouped([52, 52, 53, 54])\n    52.5\n\n    This calculates the median as the 50th percentile, and should be\n    used when your data is continuous and grouped. In the above example,\n    the values 1, 2, 3, etc. actually represent the midpoint of classes\n    0.5-1.5, 1.5-2.5, 2.5-3.5, etc. The middle value falls somewhere in\n    class 3.5-4.5, and interpolation is used to estimate it.\n\n    Optional argument ``interval`` represents the class interval, and\n    defaults to 1. Changing the class interval naturally will change the\n    interpolated 50th percentile value:\n\n    >>> median_grouped([1, 3, 3, 5, 7], interval=1)\n    3.25\n    >>> median_grouped([1, 3, 3, 5, 7], interval=2)\n    3.5\n\n    This function does not check whether the data points are at least\n    ``interval`` apart.\n    "
    data = sorted(data)
    n = len(data)
    if n == 0:
        raise StatisticsError("no median for empty data")
    elif n == 1:
        return data[0]
    x = data[(n // 2)]
    for obj in (x, interval):
        if isinstance(obj, (str, bytes)):
            raise TypeError(("expected number but got %r" % obj))
    try:
        L = x - (interval / 2)
    except TypeError:
        L = float(x) - (float(interval) / 2)
    l1 = _find_lteq(data, x)
    l2 = _find_rteq(data, l1, x)
    cf = l1
    f = (l2 - l1) + 1
    return L + ((interval * ((n / 2) - cf)) / f)


def mode(data):
    "Return the most common data point from discrete or nominal data.\n\n    ``mode`` assumes discrete data, and returns a single value. This is the\n    standard treatment of the mode as commonly taught in schools:\n\n        >>> mode([1, 1, 2, 3, 3, 3, 3, 4])\n        3\n\n    This also works with nominal (non-numeric) data:\n\n        >>> mode([\"red\", \"blue\", \"blue\", \"red\", \"green\", \"red\", \"red\"])\n        'red'\n\n    If there are multiple modes with same frequency, return the first one\n    encountered:\n\n        >>> mode(['red', 'red', 'green', 'blue', 'blue'])\n        'red'\n\n    If *data* is empty, ``mode``, raises StatisticsError.\n\n    "
    pairs = Counter(iter(data)).most_common(1)
    try:
        return pairs[0][0]
    except IndexError:
        raise StatisticsError("no mode for empty data") from None


def multimode(data):
    "Return a list of the most frequently occurring values.\n\n    Will return more than one result if there are multiple modes\n    or an empty list if *data* is empty.\n\n    >>> multimode('aabbbbbbbbcc')\n    ['b']\n    >>> multimode('aabbbbccddddeeffffgg')\n    ['b', 'd', 'f']\n    >>> multimode('')\n    []\n    "
    counts = Counter(iter(data)).most_common()
    (maxcount, mode_items) = next(groupby(counts, key=itemgetter(1)), (0, []))
    return list(map(itemgetter(0), mode_items))


def quantiles(data, *, n=4, method="exclusive"):
    "Divide *data* into *n* continuous intervals with equal probability.\n\n    Returns a list of (n - 1) cut points separating the intervals.\n\n    Set *n* to 4 for quartiles (the default).  Set *n* to 10 for deciles.\n    Set *n* to 100 for percentiles which gives the 99 cuts points that\n    separate *data* in to 100 equal sized groups.\n\n    The *data* can be any iterable containing sample.\n    The cut points are linearly interpolated between data points.\n\n    If *method* is set to *inclusive*, *data* is treated as population\n    data.  The minimum value is treated as the 0th percentile and the\n    maximum value is treated as the 100th percentile.\n    "
    if n < 1:
        raise StatisticsError("n must be at least 1")
    data = sorted(data)
    ld = len(data)
    if ld < 2:
        raise StatisticsError("must have at least two data points")
    if method == "inclusive":
        m = ld - 1
        result = []
        for i in range(1, n):
            (j, delta) = divmod((i * m), n)
            interpolated = ((data[j] * (n - delta)) + (data[(j + 1)] * delta)) / n
            result.append(interpolated)
        return result
    if method == "exclusive":
        m = ld + 1
        result = []
        for i in range(1, n):
            j = (i * m) // n
            j = 1 if (j < 1) else ((ld - 1) if (j > (ld - 1)) else j)
            delta = (i * m) - (j * n)
            interpolated = ((data[(j - 1)] * (n - delta)) + (data[j] * delta)) / n
            result.append(interpolated)
        return result
    raise ValueError(f"Unknown method: {method!r}")


def _ss(data, c=None):
    "Return sum of square deviations of sequence data.\n\n    If ``c`` is None, the mean is calculated in one pass, and the deviations\n    from the mean are calculated in a second pass. Otherwise, deviations are\n    calculated from ``c`` as given. Use the second case with care, as it can\n    lead to garbage results.\n    "
    if c is not None:
        (T, total, count) = _sum((((x - c) ** 2) for x in data))
        return (T, total)
    c = mean(data)
    (T, total, count) = _sum((((x - c) ** 2) for x in data))
    (U, total2, count2) = _sum(((x - c) for x in data))
    assert (T == U) and (count == count2)
    total -= (total2 ** 2) / len(data)
    assert not (total < 0), "negative sum of square deviations: %f" % total
    return (T, total)


def variance(data, xbar=None):
    'Return the sample variance of data.\n\n    data should be an iterable of Real-valued numbers, with at least two\n    values. The optional argument xbar, if given, should be the mean of\n    the data. If it is missing or None, the mean is automatically calculated.\n\n    Use this function when your data is a sample from a population. To\n    calculate the variance from the entire population, see ``pvariance``.\n\n    Examples:\n\n    >>> data = [2.75, 1.75, 1.25, 0.25, 0.5, 1.25, 3.5]\n    >>> variance(data)\n    1.3720238095238095\n\n    If you have already calculated the mean of your data, you can pass it as\n    the optional second argument ``xbar`` to avoid recalculating it:\n\n    >>> m = mean(data)\n    >>> variance(data, m)\n    1.3720238095238095\n\n    This function does not check that ``xbar`` is actually the mean of\n    ``data``. Giving arbitrary values for ``xbar`` may lead to invalid or\n    impossible results.\n\n    Decimals and Fractions are supported:\n\n    >>> from decimal import Decimal as D\n    >>> variance([D("27.5"), D("30.25"), D("30.25"), D("34.5"), D("41.75")])\n    Decimal(\'31.01875\')\n\n    >>> from fractions import Fraction as F\n    >>> variance([F(1, 6), F(1, 2), F(5, 3)])\n    Fraction(67, 108)\n\n    '
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if n < 2:
        raise StatisticsError("variance requires at least two data points")
    (T, ss) = _ss(data, xbar)
    return _convert((ss / (n - 1)), T)


def pvariance(data, mu=None):
    'Return the population variance of ``data``.\n\n    data should be a sequence or iterable of Real-valued numbers, with at least one\n    value. The optional argument mu, if given, should be the mean of\n    the data. If it is missing or None, the mean is automatically calculated.\n\n    Use this function to calculate the variance from the entire population.\n    To estimate the variance from a sample, the ``variance`` function is\n    usually a better choice.\n\n    Examples:\n\n    >>> data = [0.0, 0.25, 0.25, 1.25, 1.5, 1.75, 2.75, 3.25]\n    >>> pvariance(data)\n    1.25\n\n    If you have already calculated the mean of the data, you can pass it as\n    the optional second argument to avoid recalculating it:\n\n    >>> mu = mean(data)\n    >>> pvariance(data, mu)\n    1.25\n\n    Decimals and Fractions are supported:\n\n    >>> from decimal import Decimal as D\n    >>> pvariance([D("27.5"), D("30.25"), D("30.25"), D("34.5"), D("41.75")])\n    Decimal(\'24.815\')\n\n    >>> from fractions import Fraction as F\n    >>> pvariance([F(1, 4), F(5, 4), F(1, 2)])\n    Fraction(13, 72)\n\n    '
    if iter(data) is data:
        data = list(data)
    n = len(data)
    if n < 1:
        raise StatisticsError("pvariance requires at least one data point")
    (T, ss) = _ss(data, mu)
    return _convert((ss / n), T)


def stdev(data, xbar=None):
    "Return the square root of the sample variance.\n\n    See ``variance`` for arguments and other details.\n\n    >>> stdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])\n    1.0810874155219827\n\n    "
    var = variance(data, xbar)
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)


def pstdev(data, mu=None):
    "Return the square root of the population variance.\n\n    See ``pvariance`` for arguments and other details.\n\n    >>> pstdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])\n    0.986893273527251\n\n    "
    var = pvariance(data, mu)
    try:
        return var.sqrt()
    except AttributeError:
        return math.sqrt(var)


def _normal_dist_inv_cdf(p, mu, sigma):
    q = p - 0.5
    if fabs(q) <= 0.425:
        r = 0.180625 - (q * q)
        num = (
            (
                (
                    (
                        (
                            (
                                (
                                    (
                                        (
                                            (
                                                (
                                                    (
                                                        (
                                                            (2509.0809287301227 * r)
                                                            + 33430.57558358813
                                                        )
                                                        * r
                                                    )
                                                    + 67265.7709270087
                                                )
                                                * r
                                            )
                                            + 45921.95393154987
                                        )
                                        * r
                                    )
                                    + 13731.69376550946
                                )
                                * r
                            )
                            + 1971.5909503065513
                        )
                        * r
                    )
                    + 133.14166789178438
                )
                * r
            )
            + 3.3871328727963665
        ) * q
        den = (
            (
                (
                    (
                        (
                            (
                                (
                                    (
                                        (
                                            (
                                                (
                                                    (
                                                        (5226.495278852854 * r)
                                                        + 28729.085735721943
                                                    )
                                                    * r
                                                )
                                                + 39307.89580009271
                                            )
                                            * r
                                        )
                                        + 21213.794301586597
                                    )
                                    * r
                                )
                                + 5394.196021424751
                            )
                            * r
                        )
                        + 687.1870074920579
                    )
                    * r
                )
                + 42.31333070160091
            )
            * r
        ) + 1.0
        x = num / den
        return mu + (x * sigma)
    r = p if (q <= 0.0) else (1.0 - p)
    r = sqrt((-log(r)))
    if r <= 5.0:
        r = r - 1.6
        num = (
            (
                (
                    (
                        (
                            (
                                (
                                    (
                                        (
                                            (
                                                (
                                                    (
                                                        (0.0007745450142783414 * r)
                                                        + 0.022723844989269184
                                                    )
                                                    * r
                                                )
                                                + 0.2417807251774506
                                            )
                                            * r
                                        )
                                        + 1.2704582524523684
                                    )
                                    * r
                                )
                                + 3.6478483247632045
                            )
                            * r
                        )
                        + 5.769497221460691
                    )
                    * r
                )
                + 4.630337846156546
            )
            * r
        ) + 1.4234371107496835
        den = (
            (
                (
                    (
                        (
                            (
                                (
                                    (
                                        (
                                            (
                                                (
                                                    (
                                                        (1.0507500716444169e-09 * r)
                                                        + 0.0005475938084995345
                                                    )
                                                    * r
                                                )
                                                + 0.015198666563616457
                                            )
                                            * r
                                        )
                                        + 0.14810397642748008
                                    )
                                    * r
                                )
                                + 0.6897673349851
                            )
                            * r
                        )
                        + 1.6763848301838038
                    )
                    * r
                )
                + 2.053191626637759
            )
            * r
        ) + 1.0
    else:
        r = r - 5.0
        num = (
            (
                (
                    (
                        (
                            (
                                (
                                    (
                                        (
                                            (
                                                (
                                                    (
                                                        (2.0103343992922881e-07 * r)
                                                        + 2.7115555687434876e-05
                                                    )
                                                    * r
                                                )
                                                + 0.0012426609473880784
                                            )
                                            * r
                                        )
                                        + 0.026532189526576124
                                    )
                                    * r
                                )
                                + 0.29656057182850487
                            )
                            * r
                        )
                        + 1.7848265399172913
                    )
                    * r
                )
                + 5.463784911164114
            )
            * r
        ) + 6.657904643501103
        den = (
            (
                (
                    (
                        (
                            (
                                (
                                    (
                                        (
                                            (
                                                (
                                                    (
                                                        (2.0442631033899397e-15 * r)
                                                        + 1.421511758316446e-07
                                                    )
                                                    * r
                                                )
                                                + 1.8463183175100548e-05
                                            )
                                            * r
                                        )
                                        + 0.0007868691311456133
                                    )
                                    * r
                                )
                                + 0.014875361290850615
                            )
                            * r
                        )
                        + 0.1369298809227358
                    )
                    * r
                )
                + 0.599832206555888
            )
            * r
        ) + 1.0
    x = num / den
    if q < 0.0:
        x = -x
    return mu + (x * sigma)


try:
    from _statistics import _normal_dist_inv_cdf
except ImportError:
    pass


class NormalDist:
    "Normal distribution of a random variable"
    __slots__ = {
        "_mu": "Arithmetic mean of a normal distribution",
        "_sigma": "Standard deviation of a normal distribution",
    }

    def __init__(self, mu=0.0, sigma=1.0):
        "NormalDist where mu is the mean and sigma is the standard deviation."
        if sigma < 0.0:
            raise StatisticsError("sigma must be non-negative")
        self._mu = float(mu)
        self._sigma = float(sigma)

    @classmethod
    def from_samples(cls, data):
        "Make a normal distribution instance from sample data."
        if not isinstance(data, (list, tuple)):
            data = list(data)
        xbar = fmean(data)
        return cls(xbar, stdev(data, xbar))

    def samples(self, n, *, seed=None):
        "Generate *n* samples for a given mean and standard deviation."
        gauss = random.gauss if (seed is None) else random.Random(seed).gauss
        (mu, sigma) = (self._mu, self._sigma)
        return [gauss(mu, sigma) for i in range(n)]

    def pdf(self, x):
        "Probability density function.  P(x <= X < x+dx) / dx"
        variance = self._sigma ** 2.0
        if not variance:
            raise StatisticsError("pdf() not defined when sigma is zero")
        return exp((((x - self._mu) ** 2.0) / ((-2.0) * variance))) / sqrt(
            (tau * variance)
        )

    def cdf(self, x):
        "Cumulative distribution function.  P(X <= x)"
        if not self._sigma:
            raise StatisticsError("cdf() not defined when sigma is zero")
        return 0.5 * (1.0 + erf(((x - self._mu) / (self._sigma * sqrt(2.0)))))

    def inv_cdf(self, p):
        "Inverse cumulative distribution function.  x : P(X <= x) = p\n\n        Finds the value of the random variable such that the probability of\n        the variable being less than or equal to that value equals the given\n        probability.\n\n        This function is also called the percent point function or quantile\n        function.\n        "
        if (p <= 0.0) or (p >= 1.0):
            raise StatisticsError("p must be in the range 0.0 < p < 1.0")
        if self._sigma <= 0.0:
            raise StatisticsError("cdf() not defined when sigma at or below zero")
        return _normal_dist_inv_cdf(p, self._mu, self._sigma)

    def quantiles(self, n=4):
        "Divide into *n* continuous intervals with equal probability.\n\n        Returns a list of (n - 1) cut points separating the intervals.\n\n        Set *n* to 4 for quartiles (the default).  Set *n* to 10 for deciles.\n        Set *n* to 100 for percentiles which gives the 99 cuts points that\n        separate the normal distribution in to 100 equal sized groups.\n        "
        return [self.inv_cdf((i / n)) for i in range(1, n)]

    def overlap(self, other):
        "Compute the overlapping coefficient (OVL) between two normal distributions.\n\n        Measures the agreement between two normal probability distributions.\n        Returns a value between 0.0 and 1.0 giving the overlapping area in\n        the two underlying probability density functions.\n\n            >>> N1 = NormalDist(2.4, 1.6)\n            >>> N2 = NormalDist(3.2, 2.0)\n            >>> N1.overlap(N2)\n            0.8035050657330205\n        "
        if not isinstance(other, NormalDist):
            raise TypeError("Expected another NormalDist instance")
        (X, Y) = (self, other)
        if (Y._sigma, Y._mu) < (X._sigma, X._mu):
            (X, Y) = (Y, X)
        (X_var, Y_var) = (X.variance, Y.variance)
        if (not X_var) or (not Y_var):
            raise StatisticsError("overlap() not defined when sigma is zero")
        dv = Y_var - X_var
        dm = fabs((Y._mu - X._mu))
        if not dv:
            return 1.0 - erf((dm / ((2.0 * X._sigma) * sqrt(2.0))))
        a = (X._mu * Y_var) - (Y._mu * X_var)
        b = (X._sigma * Y._sigma) * sqrt(((dm ** 2.0) + (dv * log((Y_var / X_var)))))
        x1 = (a + b) / dv
        x2 = (a - b) / dv
        return 1.0 - (fabs((Y.cdf(x1) - X.cdf(x1))) + fabs((Y.cdf(x2) - X.cdf(x2))))

    def zscore(self, x):
        "Compute the Standard Score.  (x - mean) / stdev\n\n        Describes *x* in terms of the number of standard deviations\n        above or below the mean of the normal distribution.\n        "
        if not self._sigma:
            raise StatisticsError("zscore() not defined when sigma is zero")
        return (x - self._mu) / self._sigma

    @property
    def mean(self):
        "Arithmetic mean of the normal distribution."
        return self._mu

    @property
    def median(self):
        "Return the median of the normal distribution"
        return self._mu

    @property
    def mode(self):
        "Return the mode of the normal distribution\n\n        The mode is the value x where which the probability density\n        function (pdf) takes its maximum value.\n        "
        return self._mu

    @property
    def stdev(self):
        "Standard deviation of the normal distribution."
        return self._sigma

    @property
    def variance(self):
        "Square of the standard deviation."
        return self._sigma ** 2.0

    def __add__(x1, x2):
        "Add a constant or another NormalDist instance.\n\n        If *other* is a constant, translate mu by the constant,\n        leaving sigma unchanged.\n\n        If *other* is a NormalDist, add both the means and the variances.\n        Mathematically, this works only if the two distributions are\n        independent or if they are jointly normally distributed.\n        "
        if isinstance(x2, NormalDist):
            return NormalDist((x1._mu + x2._mu), hypot(x1._sigma, x2._sigma))
        return NormalDist((x1._mu + x2), x1._sigma)

    def __sub__(x1, x2):
        "Subtract a constant or another NormalDist instance.\n\n        If *other* is a constant, translate by the constant mu,\n        leaving sigma unchanged.\n\n        If *other* is a NormalDist, subtract the means and add the variances.\n        Mathematically, this works only if the two distributions are\n        independent or if they are jointly normally distributed.\n        "
        if isinstance(x2, NormalDist):
            return NormalDist((x1._mu - x2._mu), hypot(x1._sigma, x2._sigma))
        return NormalDist((x1._mu - x2), x1._sigma)

    def __mul__(x1, x2):
        "Multiply both mu and sigma by a constant.\n\n        Used for rescaling, perhaps to change measurement units.\n        Sigma is scaled with the absolute value of the constant.\n        "
        return NormalDist((x1._mu * x2), (x1._sigma * fabs(x2)))

    def __truediv__(x1, x2):
        "Divide both mu and sigma by a constant.\n\n        Used for rescaling, perhaps to change measurement units.\n        Sigma is scaled with the absolute value of the constant.\n        "
        return NormalDist((x1._mu / x2), (x1._sigma / fabs(x2)))

    def __pos__(x1):
        "Return a copy of the instance."
        return NormalDist(x1._mu, x1._sigma)

    def __neg__(x1):
        "Negates mu while keeping sigma the same."
        return NormalDist((-x1._mu), x1._sigma)

    __radd__ = __add__

    def __rsub__(x1, x2):
        "Subtract a NormalDist from a constant or another NormalDist."
        return -(x1 - x2)

    __rmul__ = __mul__

    def __eq__(x1, x2):
        "Two NormalDist objects are equal if their mu and sigma are both equal."
        if not isinstance(x2, NormalDist):
            return NotImplemented
        return (x1._mu == x2._mu) and (x1._sigma == x2._sigma)

    def __hash__(self):
        "NormalDist objects hash equal if their mu and sigma are both equal."
        return hash((self._mu, self._sigma))

    def __repr__(self):
        return f"{type(self).__name__}(mu={self._mu!r}, sigma={self._sigma!r})"
