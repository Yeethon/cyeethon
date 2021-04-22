import random

TEST_SIZE = 2


def test_short_halfway_cases():
    for k in (0, 5, 10, 15, 20):
        upper = -((-(2 ** 54)) // (5 ** k))
        lower = -((-(2 ** 53)) // (5 ** k))
        if (lower % 2) == 0:
            lower += 1
        for i in range((10 * TEST_SIZE)):
            (n, e) = (random.randrange(lower, upper, 2), k)
            while (n % 5) == 0:
                (n, e) = ((n // 5), (e + 1))
            assert (n % 10) in (1, 3, 7, 9)
            (digits, exponent) = (n, e)
            while digits < (10 ** 20):
                s = "{}e{}".format(digits, exponent)
                (yield s)
                s = "{}e{}".format((digits * (10 ** 40)), (exponent - 40))
                (yield s)
                digits *= 2
            (digits, exponent) = (n, e)
            while digits < (10 ** 20):
                s = "{}e{}".format(digits, exponent)
                (yield s)
                s = "{}e{}".format((digits * (10 ** 40)), (exponent - 40))
                (yield s)
                digits *= 5
                exponent -= 1


def test_halfway_cases():
    for i in range(1000):
        for j in range(TEST_SIZE):
            bits = random.randrange((2047 * (2 ** 52)))
            (e, m) = divmod(bits, (2 ** 52))
            if e:
                (m, e) = ((m + (2 ** 52)), (e - 1))
            e -= 1074
            (m, e) = (((2 * m) + 1), (e - 1))
            if e >= 0:
                digits = m << e
                exponent = 0
            else:
                digits = m * (5 ** (-e))
                exponent = e
            s = "{}e{}".format(digits, exponent)
            (yield s)


def test_boundaries():
    boundaries = [
        (10000000000000000000, (-19), 1110),
        (17976931348623159077, 289, 1995),
        (22250738585072013831, (-327), 4941),
        (0, (-327), 4941),
    ]
    for (n, e, u) in boundaries:
        for j in range(1000):
            for i in range(TEST_SIZE):
                digits = n + random.randrange(((-3) * u), (3 * u))
                exponent = e
                s = "{}e{}".format(digits, exponent)
                (yield s)
            n *= 10
            u *= 10
            e -= 1


def test_underflow_boundary():
    for exponent in range((-400), (-320)):
        base = (10 ** (-exponent)) // (2 ** 1075)
        for j in range(TEST_SIZE):
            digits = base + random.randrange((-1000), 1000)
            s = "{}e{}".format(digits, exponent)
            (yield s)


def test_bigcomp():
    for ndigs in (5, 10, 14, 15, 16, 17, 18, 19, 20, 40, 41, 50):
        dig10 = 10 ** ndigs
        for i in range((100 * TEST_SIZE)):
            digits = random.randrange(dig10)
            exponent = random.randrange((-400), 400)
            s = "{}e{}".format(digits, exponent)
            (yield s)


def test_parsing():
    digits = "000000123456789"
    signs = ("+", "-", "")
    for i in range(1000):
        for j in range(TEST_SIZE):
            s = random.choice(signs)
            intpart_len = random.randrange(5)
            s += "".join((random.choice(digits) for _ in range(intpart_len)))
            if random.choice([True, False]):
                s += "."
                fracpart_len = random.randrange(5)
                s += "".join((random.choice(digits) for _ in range(fracpart_len)))
            else:
                fracpart_len = 0
            if random.choice([True, False]):
                s += random.choice(["e", "E"])
                s += random.choice(signs)
                exponent_len = random.randrange(1, 4)
                s += "".join((random.choice(digits) for _ in range(exponent_len)))
            if intpart_len + fracpart_len:
                (yield s)


test_particular = [
    "1.00000000100000000025",
    "1.000000000000000000000000010000000000000000000000000025",
    "1.00000000000000000000000000000000000000000000100000000000000000000000000000000000000000000025",
    "1.0000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000025",
    "0.99999999900000000025",
    "0.9999999999999999999999999999999999999999999999999999000000000000000000000000000000000000000000000000000025",
    "0.99999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999900000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000025",
    "1.0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001",
    "1.0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000005",
    "1.00000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000002500000000000000020000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000000000000001",
    "1.000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000024999999999999999999999999999999999999999999997999999999999999999999999999999999999999999999999999999999990000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001",
    "0.99999999999999999999999999999999999999999999999999999999999000000000000000000000000000000000000000000000000000000000002499999999999999980000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000000000000001",
    "0.99999999999999999999999999999999999999999999999999999999999000000000000000000000000000000000000000000000000000000000002500000019999999999999999999999999999999999999999999999999999999999900000000000000000000000000000000000000000000000000000000000000000001",
    "1.0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001",
    "0.999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999989999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999",
]
TESTCASES = [
    [x for x in test_short_halfway_cases()],
    [x for x in test_halfway_cases()],
    [x for x in test_boundaries()],
    [x for x in test_underflow_boundary()],
    [x for x in test_bigcomp()],
    [x for x in test_parsing()],
    test_particular,
]


def un_randfloat():
    for i in range(1000):
        l = random.choice(TESTCASES[:6])
        (yield random.choice(l))
    for v in test_particular:
        (yield v)


def bin_randfloat():
    for i in range(1000):
        l1 = random.choice(TESTCASES)
        l2 = random.choice(TESTCASES)
        (yield (random.choice(l1), random.choice(l2)))


def tern_randfloat():
    for i in range(1000):
        l1 = random.choice(TESTCASES)
        l2 = random.choice(TESTCASES)
        l3 = random.choice(TESTCASES)
        (yield (random.choice(l1), random.choice(l2), random.choice(l3)))
