import unittest
import unittest.mock
import random
import os
import time
import pickle
import warnings
import test.support
from functools import partial
from math import log, exp, pi, fsum, sin, factorial
from test import support
from fractions import Fraction
from collections import abc, Counter


class TestBasicOps:
    def randomlist(self, n):
        "Helper function to make a list of random numbers"
        return [self.gen.random() for i in range(n)]

    def test_autoseed(self):
        self.gen.seed()
        state1 = self.gen.getstate()
        time.sleep(0.1)
        self.gen.seed()
        state2 = self.gen.getstate()
        self.assertNotEqual(state1, state2)

    def test_saverestore(self):
        N = 1000
        self.gen.seed()
        state = self.gen.getstate()
        randseq = self.randomlist(N)
        self.gen.setstate(state)
        self.assertEqual(randseq, self.randomlist(N))

    def test_seedargs(self):
        class MySeed(object):
            def __hash__(self):
                return -1729

        for arg in [
            None,
            0,
            1,
            (-1),
            (10 ** 20),
            (-(10 ** 20)),
            False,
            True,
            3.14,
            "a",
        ]:
            self.gen.seed(arg)
        for arg in [(1 + 2j), tuple("abc"), MySeed()]:
            with self.assertWarns(DeprecationWarning):
                self.gen.seed(arg)
        for arg in [list(range(3)), dict(one=1)]:
            with self.assertWarns(DeprecationWarning):
                self.assertRaises(TypeError, self.gen.seed, arg)
        self.assertRaises(TypeError, self.gen.seed, 1, 2, 3, 4)
        self.assertRaises(TypeError, type(self.gen), [])

    @unittest.mock.patch("random._urandom")
    def test_seed_when_randomness_source_not_found(self, urandom_mock):
        urandom_mock.side_effect = NotImplementedError
        self.test_seedargs()

    def test_shuffle(self):
        shuffle = self.gen.shuffle
        lst = []
        shuffle(lst)
        self.assertEqual(lst, [])
        lst = [37]
        shuffle(lst)
        self.assertEqual(lst, [37])
        seqs = [list(range(n)) for n in range(10)]
        shuffled_seqs = [list(range(n)) for n in range(10)]
        for shuffled_seq in shuffled_seqs:
            shuffle(shuffled_seq)
        for (seq, shuffled_seq) in zip(seqs, shuffled_seqs):
            self.assertEqual(len(seq), len(shuffled_seq))
            self.assertEqual(set(seq), set(shuffled_seq))
        lst = list(range(1000))
        shuffled_lst = list(range(1000))
        shuffle(shuffled_lst)
        self.assertTrue((lst != shuffled_lst))
        shuffle(lst)
        self.assertTrue((lst != shuffled_lst))
        self.assertRaises(TypeError, shuffle, (1, 2, 3))

    def test_shuffle_random_argument(self):
        shuffle = self.gen.shuffle
        mock_random = unittest.mock.Mock(return_value=0.5)
        seq = bytearray(b"abcdefghijk")
        with self.assertWarns(DeprecationWarning):
            shuffle(seq, mock_random)
        mock_random.assert_called_with()

    def test_choice(self):
        choice = self.gen.choice
        with self.assertRaises(IndexError):
            choice([])
        self.assertEqual(choice([50]), 50)
        self.assertIn(choice([25, 75]), [25, 75])

    def test_sample(self):
        N = 100
        population = range(N)
        for k in range((N + 1)):
            s = self.gen.sample(population, k)
            self.assertEqual(len(s), k)
            uniq = set(s)
            self.assertEqual(len(uniq), k)
            self.assertTrue((uniq <= set(population)))
        self.assertEqual(self.gen.sample([], 0), [])
        self.assertRaises(ValueError, self.gen.sample, population, (N + 1))
        self.assertRaises(ValueError, self.gen.sample, [], (-1))

    def test_sample_distribution(self):
        n = 5
        pop = range(n)
        trials = 10000
        for k in range(n):
            expected = factorial(n) // factorial((n - k))
            perms = {}
            for i in range(trials):
                perms[tuple(self.gen.sample(pop, k))] = None
                if len(perms) == expected:
                    break
            else:
                self.fail()

    def test_sample_inputs(self):
        self.gen.sample(range(20), 2)
        self.gen.sample(range(20), 2)
        self.gen.sample(str("abcdefghijklmnopqrst"), 2)
        self.gen.sample(tuple("abcdefghijklmnopqrst"), 2)

    def test_sample_on_dicts(self):
        self.assertRaises(TypeError, self.gen.sample, dict.fromkeys("abcdef"), 2)

    def test_sample_on_sets(self):
        with self.assertWarns(DeprecationWarning):
            population = {10, 20, 30, 40, 50, 60, 70}
            self.gen.sample(population, k=5)

    def test_sample_on_seqsets(self):
        class SeqSet(abc.Sequence, abc.Set):
            def __init__(self, items):
                self._items = items

            def __len__(self):
                return len(self._items)

            def __getitem__(self, index):
                return self._items[index]

        population = SeqSet([2, 4, 1, 3])
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            self.gen.sample(population, k=2)

    def test_sample_with_counts(self):
        sample = self.gen.sample
        colors = ["red", "green", "blue", "orange", "black", "brown", "amber"]
        counts = [500, 200, 20, 10, 5, 0, 1]
        k = 700
        summary = Counter(sample(colors, counts=counts, k=k))
        self.assertEqual(sum(summary.values()), k)
        for (color, weight) in zip(colors, counts):
            self.assertLessEqual(summary[color], weight)
        self.assertNotIn("brown", summary)
        k = sum(counts)
        summary = Counter(sample(colors, counts=counts, k=k))
        self.assertEqual(sum(summary.values()), k)
        for (color, weight) in zip(colors, counts):
            self.assertLessEqual(summary[color], weight)
        self.assertNotIn("brown", summary)
        summary = Counter(sample(["x"], counts=[10], k=8))
        self.assertEqual(summary, Counter(x=8))
        nc = len(colors)
        summary = Counter(sample(colors, counts=([10] * nc), k=(10 * nc)))
        self.assertEqual(summary, Counter((10 * colors)))
        with self.assertRaises(TypeError):
            sample(["red", "green", "blue"], counts=10, k=10)
        with self.assertRaises(ValueError):
            sample(["red", "green", "blue"], counts=[(-3), (-7), (-8)], k=2)
        with self.assertRaises(ValueError):
            sample(["red", "green", "blue"], counts=[0, 0, 0], k=2)
        with self.assertRaises(ValueError):
            sample(["red", "green"], counts=[10, 10], k=21)
        with self.assertRaises(ValueError):
            sample(["red", "green", "blue"], counts=[1, 2], k=2)
        with self.assertRaises(ValueError):
            sample(["red", "green", "blue"], counts=[1, 2, 3, 4], k=2)

    def test_choices(self):
        choices = self.gen.choices
        data = ["red", "green", "blue", "yellow"]
        str_data = "abcd"
        range_data = range(4)
        set_data = set(range(4))
        for sample in [
            choices(data, k=5),
            choices(data, range(4), k=5),
            choices(k=5, population=data, weights=range(4)),
            choices(k=5, population=data, cum_weights=range(4)),
        ]:
            self.assertEqual(len(sample), 5)
            self.assertEqual(type(sample), list)
            self.assertTrue((set(sample) <= set(data)))
        with self.assertRaises(TypeError):
            choices(2)
        self.assertEqual(choices(data, k=0), [])
        self.assertEqual(choices(data, k=(-1)), [])
        with self.assertRaises(TypeError):
            choices(data, k=2.5)
        self.assertTrue((set(choices(str_data, k=5)) <= set(str_data)))
        self.assertTrue((set(choices(range_data, k=5)) <= set(range_data)))
        with self.assertRaises(TypeError):
            choices(set_data, k=2)
        self.assertTrue((set(choices(data, None, k=5)) <= set(data)))
        self.assertTrue((set(choices(data, weights=None, k=5)) <= set(data)))
        with self.assertRaises(ValueError):
            choices(data, [1, 2], k=5)
        with self.assertRaises(TypeError):
            choices(data, 10, k=5)
        with self.assertRaises(TypeError):
            choices(data, ([None] * 4), k=5)
        for weights in [
            [15, 10, 25, 30],
            [15.1, 10.2, 25.2, 30.3],
            [Fraction(1, 3), Fraction(2, 6), Fraction(3, 6), Fraction(4, 6)],
            [True, False, True, False],
        ]:
            self.assertTrue((set(choices(data, weights, k=5)) <= set(data)))
        with self.assertRaises(ValueError):
            choices(data, cum_weights=[1, 2], k=5)
        with self.assertRaises(TypeError):
            choices(data, cum_weights=10, k=5)
        with self.assertRaises(TypeError):
            choices(data, cum_weights=([None] * 4), k=5)
        with self.assertRaises(TypeError):
            choices(data, range(4), cum_weights=range(4), k=5)
        for weights in [
            [15, 10, 25, 30],
            [15.1, 10.2, 25.2, 30.3],
            [Fraction(1, 3), Fraction(2, 6), Fraction(3, 6), Fraction(4, 6)],
        ]:
            self.assertTrue((set(choices(data, cum_weights=weights, k=5)) <= set(data)))
        self.assertEqual(choices("abcd", [1, 0, 0, 0]), ["a"])
        self.assertEqual(choices("abcd", [0, 1, 0, 0]), ["b"])
        self.assertEqual(choices("abcd", [0, 0, 1, 0]), ["c"])
        self.assertEqual(choices("abcd", [0, 0, 0, 1]), ["d"])
        with self.assertRaises(IndexError):
            choices([], k=1)
        with self.assertRaises(IndexError):
            choices([], weights=[], k=1)
        with self.assertRaises(IndexError):
            choices([], cum_weights=[], k=5)

    def test_choices_subnormal(self):
        choices = self.gen.choices
        choices(population=[1, 2], weights=[1e-323, 1e-323], k=5000)

    def test_choices_with_all_zero_weights(self):
        with self.assertRaises(ValueError):
            self.gen.choices("AB", [0.0, 0.0])

    def test_choices_negative_total(self):
        with self.assertRaises(ValueError):
            self.gen.choices("ABC", [3, (-5), 1])

    def test_choices_infinite_total(self):
        with self.assertRaises(ValueError):
            self.gen.choices("A", [float("inf")])
        with self.assertRaises(ValueError):
            self.gen.choices("AB", [0.0, float("inf")])
        with self.assertRaises(ValueError):
            self.gen.choices("AB", [(-float("inf")), 123])
        with self.assertRaises(ValueError):
            self.gen.choices("AB", [0.0, float("nan")])
        with self.assertRaises(ValueError):
            self.gen.choices("AB", [float("-inf"), float("inf")])

    def test_gauss(self):
        for seed in (1, 12, 123, 1234, 12345, 123456, 654321):
            self.gen.seed(seed)
            x1 = self.gen.random()
            y1 = self.gen.gauss(0, 1)
            self.gen.seed(seed)
            x2 = self.gen.random()
            y2 = self.gen.gauss(0, 1)
            self.assertEqual(x1, x2)
            self.assertEqual(y1, y2)

    def test_getrandbits(self):
        for k in range(1, 1000):
            self.assertTrue((0 <= self.gen.getrandbits(k) < (2 ** k)))
        self.assertEqual(self.gen.getrandbits(0), 0)
        getbits = self.gen.getrandbits
        for span in [1, 2, 3, 4, 31, 32, 32, 52, 53, 54, 119, 127, 128, 129]:
            all_bits = (2 ** span) - 1
            cum = 0
            cpl_cum = 0
            for i in range(100):
                v = getbits(span)
                cum |= v
                cpl_cum |= all_bits ^ v
            self.assertEqual(cum, all_bits)
            self.assertEqual(cpl_cum, all_bits)
        self.assertRaises(TypeError, self.gen.getrandbits)
        self.assertRaises(TypeError, self.gen.getrandbits, 1, 2)
        self.assertRaises(ValueError, self.gen.getrandbits, (-1))
        self.assertRaises(TypeError, self.gen.getrandbits, 10.1)

    def test_pickling(self):
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            state = pickle.dumps(self.gen, proto)
            origseq = [self.gen.random() for i in range(10)]
            newgen = pickle.loads(state)
            restoredseq = [newgen.random() for i in range(10)]
            self.assertEqual(origseq, restoredseq)

    @test.support.cpython_only
    def test_bug_41052(self):
        import _random

        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            r = _random.Random()
            self.assertRaises(TypeError, pickle.dumps, r, proto)

    @test.support.cpython_only
    def test_bug_42008(self):
        import _random

        r1 = _random.Random()
        r1.seed(8675309)
        r2 = _random.Random(8675309)
        self.assertEqual(r1.random(), r2.random())

    def test_bug_1727780(self):
        files = [("randv2_32.pck", 780), ("randv2_64.pck", 866), ("randv3.pck", 343)]
        for (file, value) in files:
            with open(support.findfile(file), "rb") as f:
                r = pickle.load(f)
            self.assertEqual(int((r.random() * 1000)), value)

    def test_bug_9025(self):
        n = 100000
        randrange = self.gen.randrange
        k = sum((((randrange(6755399441055744) % 3) == 2) for i in range(n)))
        self.assertTrue((0.3 < (k / n) < 0.37), (k / n))

    def test_randbytes(self):
        for n in range(1, 10):
            data = self.gen.randbytes(n)
            self.assertEqual(type(data), bytes)
            self.assertEqual(len(data), n)
        self.assertEqual(self.gen.randbytes(0), b"")
        self.assertRaises(TypeError, self.gen.randbytes)
        self.assertRaises(TypeError, self.gen.randbytes, 1, 2)
        self.assertRaises(ValueError, self.gen.randbytes, (-1))
        self.assertRaises(TypeError, self.gen.randbytes, 1.0)


try:
    random.SystemRandom().random()
except NotImplementedError:
    SystemRandom_available = False
else:
    SystemRandom_available = True


@unittest.skipUnless(SystemRandom_available, "random.SystemRandom not available")
class SystemRandom_TestBasicOps(TestBasicOps, unittest.TestCase):
    gen = random.SystemRandom()

    def test_autoseed(self):
        self.gen.seed()

    def test_saverestore(self):
        self.assertRaises(NotImplementedError, self.gen.getstate)
        self.assertRaises(NotImplementedError, self.gen.setstate, None)

    def test_seedargs(self):
        self.gen.seed(100)

    def test_gauss(self):
        self.gen.gauss_next = None
        self.gen.seed(100)
        self.assertEqual(self.gen.gauss_next, None)

    def test_pickling(self):
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            self.assertRaises(NotImplementedError, pickle.dumps, self.gen, proto)

    def test_53_bits_per_float(self):
        span = 2 ** 53
        cum = 0
        for i in range(100):
            cum |= int((self.gen.random() * span))
        self.assertEqual(cum, (span - 1))

    def test_bigrand(self):
        span = 2 ** 500
        cum = 0
        for i in range(100):
            r = self.gen.randrange(span)
            self.assertTrue((0 <= r < span))
            cum |= r
        self.assertEqual(cum, (span - 1))

    def test_bigrand_ranges(self):
        for i in [40, 80, 160, 200, 211, 250, 375, 512, 550]:
            start = self.gen.randrange((2 ** (i - 2)))
            stop = self.gen.randrange((2 ** i))
            if stop <= start:
                continue
            self.assertTrue((start <= self.gen.randrange(start, stop) < stop))

    def test_rangelimits(self):
        for (start, stop) in [
            ((-2), 0),
            (((-(2 ** 60)) - 2), (-(2 ** 60))),
            ((2 ** 60), ((2 ** 60) + 2)),
        ]:
            self.assertEqual(
                set(range(start, stop)),
                set([self.gen.randrange(start, stop) for i in range(100)]),
            )

    def test_randrange_nonunit_step(self):
        rint = self.gen.randrange(0, 10, 2)
        self.assertIn(rint, (0, 2, 4, 6, 8))
        rint = self.gen.randrange(0, 2, 2)
        self.assertEqual(rint, 0)

    def test_randrange_errors(self):
        raises = partial(self.assertRaises, ValueError, self.gen.randrange)
        raises(3, 3)
        raises((-721))
        raises(0, 100, (-12))
        self.assertWarns(DeprecationWarning, raises, 3.14159)
        self.assertWarns(DeprecationWarning, self.gen.randrange, 3.0)
        self.assertWarns(DeprecationWarning, self.gen.randrange, Fraction(3, 1))
        self.assertWarns(DeprecationWarning, raises, "3")
        self.assertWarns(DeprecationWarning, raises, 0, 2.71828)
        self.assertWarns(DeprecationWarning, self.gen.randrange, 0, 2.0)
        self.assertWarns(DeprecationWarning, self.gen.randrange, 0, Fraction(2, 1))
        self.assertWarns(DeprecationWarning, raises, 0, "2")
        raises(0, 42, 0)
        self.assertWarns(DeprecationWarning, raises, 0, 42, 0.0)
        self.assertWarns(DeprecationWarning, raises, 0, 0, 0.0)
        self.assertWarns(DeprecationWarning, raises, 0, 42, 3.14159)
        self.assertWarns(DeprecationWarning, self.gen.randrange, 0, 42, 3.0)
        self.assertWarns(DeprecationWarning, self.gen.randrange, 0, 42, Fraction(3, 1))
        self.assertWarns(DeprecationWarning, raises, 0, 42, "3")
        self.assertWarns(DeprecationWarning, self.gen.randrange, 0, 42, 1.0)
        self.assertWarns(DeprecationWarning, raises, 0, 0, 1.0)

    def test_randrange_argument_handling(self):
        randrange = self.gen.randrange
        with self.assertWarns(DeprecationWarning):
            randrange(10.0, 20, 2)
        with self.assertWarns(DeprecationWarning):
            randrange(10, 20.0, 2)
        with self.assertWarns(DeprecationWarning):
            randrange(10, 20, 1.0)
        with self.assertWarns(DeprecationWarning):
            randrange(10, 20, 2.0)
        with self.assertWarns(DeprecationWarning):
            with self.assertRaises(ValueError):
                randrange(10.5)
        with self.assertWarns(DeprecationWarning):
            with self.assertRaises(ValueError):
                randrange(10, 20.5)
        with self.assertWarns(DeprecationWarning):
            with self.assertRaises(ValueError):
                randrange(10, 20, 1.5)

    def test_randrange_step(self):
        randrange = self.gen.randrange
        with self.assertRaises(TypeError):
            randrange(1000, step=100)
        with self.assertRaises(TypeError):
            randrange(1000, None, step=100)

    def test_randbelow_logic(self, _log=log, int=int):
        for i in range(1, 1000):
            n = 1 << i
            numbits = i + 1
            k = int((1.00001 + _log(n, 2)))
            self.assertEqual(k, numbits)
            self.assertEqual(n, (2 ** (k - 1)))
            n += n - 1
            k = int((1.00001 + _log(n, 2)))
            self.assertIn(k, [numbits, (numbits + 1)])
            self.assertTrue(((2 ** k) > n > (2 ** (k - 2))))
            n -= n >> 15
            k = int((1.00001 + _log(n, 2)))
            self.assertEqual(k, numbits)
            self.assertTrue(((2 ** k) > n > (2 ** (k - 1))))


class MersenneTwister_TestBasicOps(TestBasicOps, unittest.TestCase):
    gen = random.Random()

    def test_guaranteed_stable(self):
        self.gen.seed(3456147, version=1)
        self.assertEqual(
            [self.gen.random().hex() for i in range(4)],
            [
                "0x1.ac362300d90d2p-1",
                "0x1.9d16f74365005p-1",
                "0x1.1ebb4352e4c4dp-1",
                "0x1.1a7422abf9c11p-1",
            ],
        )
        self.gen.seed("the quick brown fox", version=2)
        self.assertEqual(
            [self.gen.random().hex() for i in range(4)],
            [
                "0x1.1239ddfb11b7cp-3",
                "0x1.b3cbb5c51b120p-4",
                "0x1.8c4f55116b60fp-1",
                "0x1.63eb525174a27p-1",
            ],
        )

    def test_bug_27706(self):
        self.gen.seed("nofar", version=1)
        self.assertEqual(
            [self.gen.random().hex() for i in range(4)],
            [
                "0x1.8645314505ad7p-1",
                "0x1.afb1f82e40a40p-5",
                "0x1.2a59d2285e971p-1",
                "0x1.56977142a7880p-6",
            ],
        )
        self.gen.seed("rachel", version=1)
        self.assertEqual(
            [self.gen.random().hex() for i in range(4)],
            [
                "0x1.0b294cc856fcdp-1",
                "0x1.2ad22d79e77b8p-3",
                "0x1.3052b9c072678p-2",
                "0x1.578f332106574p-3",
            ],
        )
        self.gen.seed("", version=1)
        self.assertEqual(
            [self.gen.random().hex() for i in range(4)],
            [
                "0x1.b0580f98a7dbep-1",
                "0x1.84129978f9c1ap-1",
                "0x1.aeaa51052e978p-2",
                "0x1.092178fb945a6p-2",
            ],
        )

    def test_bug_31478(self):
        class BadInt(int):
            def __abs__(self):
                return None

        try:
            self.gen.seed(BadInt())
        except TypeError:
            pass

    def test_bug_31482(self):
        self.gen.seed(b"nofar", version=1)
        self.assertEqual(
            [self.gen.random().hex() for i in range(4)],
            [
                "0x1.8645314505ad7p-1",
                "0x1.afb1f82e40a40p-5",
                "0x1.2a59d2285e971p-1",
                "0x1.56977142a7880p-6",
            ],
        )
        self.gen.seed(b"rachel", version=1)
        self.assertEqual(
            [self.gen.random().hex() for i in range(4)],
            [
                "0x1.0b294cc856fcdp-1",
                "0x1.2ad22d79e77b8p-3",
                "0x1.3052b9c072678p-2",
                "0x1.578f332106574p-3",
            ],
        )
        self.gen.seed(b"", version=1)
        self.assertEqual(
            [self.gen.random().hex() for i in range(4)],
            [
                "0x1.b0580f98a7dbep-1",
                "0x1.84129978f9c1ap-1",
                "0x1.aeaa51052e978p-2",
                "0x1.092178fb945a6p-2",
            ],
        )
        b = b"\x00 @`\x80\xa0\xc0\xe0\xf0"
        self.gen.seed(b, version=1)
        self.assertEqual(
            [self.gen.random().hex() for i in range(4)],
            [
                "0x1.52c2fde444d23p-1",
                "0x1.875174f0daea4p-2",
                "0x1.9e9b2c50e5cd2p-1",
                "0x1.fa57768bd321cp-2",
            ],
        )

    def test_setstate_first_arg(self):
        self.assertRaises(ValueError, self.gen.setstate, (1, None, None))

    def test_setstate_middle_arg(self):
        start_state = self.gen.getstate()
        self.assertRaises(TypeError, self.gen.setstate, (2, None, None))
        self.assertRaises(ValueError, self.gen.setstate, (2, (1, 2, 3), None))
        self.assertRaises(TypeError, self.gen.setstate, (2, (("a",) * 625), None))
        self.assertRaises(
            TypeError, self.gen.setstate, (2, (((0,) * 624) + ("a",)), None)
        )
        with self.assertRaises((ValueError, OverflowError)):
            self.gen.setstate((2, (((1,) * 624) + (625,)), None))
        with self.assertRaises((ValueError, OverflowError)):
            self.gen.setstate((2, (((1,) * 624) + ((-1),)), None))
        bits100 = self.gen.getrandbits(100)
        self.gen.setstate(start_state)
        self.assertEqual(self.gen.getrandbits(100), bits100)
        state_values = self.gen.getstate()[1]
        state_values = list(state_values)
        state_values[(-1)] = float("nan")
        state = (int(x) for x in state_values)
        self.assertRaises(TypeError, self.gen.setstate, (2, state, None))

    def test_referenceImplementation(self):
        expected = [
            0.4583980307371326,
            0.8605781520197878,
            0.9284833172678215,
            0.3593268111978246,
            0.08182349376244957,
            0.1433222647016933,
            0.08429782382352002,
            0.5381486467183145,
            0.0892150249119934,
            0.7848619610537291,
        ]
        self.gen.seed((((61731 + (24903 << 32)) + (614 << 64)) + (42143 << 96)))
        actual = self.randomlist(2000)[(-10):]
        for (a, e) in zip(actual, expected):
            self.assertAlmostEqual(a, e, places=14)

    def test_strong_reference_implementation(self):
        from math import ldexp

        expected = [
            4128882400830239,
            7751398889519013,
            8363034243334166,
            3236528186029503,
            737000512037440,
            1290932195808883,
            759287295919497,
            4847212089661076,
            803577505899006,
            7069408070677702,
        ]
        self.gen.seed((((61731 + (24903 << 32)) + (614 << 64)) + (42143 << 96)))
        actual = self.randomlist(2000)[(-10):]
        for (a, e) in zip(actual, expected):
            self.assertEqual(int(ldexp(a, 53)), e)

    def test_long_seed(self):
        seed = (1 << (10000 * 8)) - 1
        self.gen.seed(seed)

    def test_53_bits_per_float(self):
        span = 2 ** 53
        cum = 0
        for i in range(100):
            cum |= int((self.gen.random() * span))
        self.assertEqual(cum, (span - 1))

    def test_bigrand(self):
        span = 2 ** 500
        cum = 0
        for i in range(100):
            r = self.gen.randrange(span)
            self.assertTrue((0 <= r < span))
            cum |= r
        self.assertEqual(cum, (span - 1))

    def test_bigrand_ranges(self):
        for i in [40, 80, 160, 200, 211, 250, 375, 512, 550]:
            start = self.gen.randrange((2 ** (i - 2)))
            stop = self.gen.randrange((2 ** i))
            if stop <= start:
                continue
            self.assertTrue((start <= self.gen.randrange(start, stop) < stop))

    def test_rangelimits(self):
        for (start, stop) in [
            ((-2), 0),
            (((-(2 ** 60)) - 2), (-(2 ** 60))),
            ((2 ** 60), ((2 ** 60) + 2)),
        ]:
            self.assertEqual(
                set(range(start, stop)),
                set([self.gen.randrange(start, stop) for i in range(100)]),
            )

    def test_getrandbits(self):
        super().test_getrandbits()
        self.gen.seed(1234567)
        self.assertEqual(self.gen.getrandbits(100), 97904845777343510404718956115)

    def test_randrange_uses_getrandbits(self):
        self.gen.seed(1234567)
        self.assertEqual(self.gen.randrange((2 ** 99)), 97904845777343510404718956115)

    def test_randbelow_logic(self, _log=log, int=int):
        for i in range(1, 1000):
            n = 1 << i
            numbits = i + 1
            k = int((1.00001 + _log(n, 2)))
            self.assertEqual(k, numbits)
            self.assertEqual(n, (2 ** (k - 1)))
            n += n - 1
            k = int((1.00001 + _log(n, 2)))
            self.assertIn(k, [numbits, (numbits + 1)])
            self.assertTrue(((2 ** k) > n > (2 ** (k - 2))))
            n -= n >> 15
            k = int((1.00001 + _log(n, 2)))
            self.assertEqual(k, numbits)
            self.assertTrue(((2 ** k) > n > (2 ** (k - 1))))

    def test_randbelow_without_getrandbits(self):
        maxsize = 1 << random.BPF
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.gen._randbelow_without_getrandbits((maxsize + 1), maxsize=maxsize)
        self.gen._randbelow_without_getrandbits(5640, maxsize=maxsize)
        x = self.gen._randbelow_without_getrandbits(0, maxsize=maxsize)
        self.assertEqual(x, 0)
        n = 42
        epsilon = 0.01
        limit = (maxsize - (maxsize % n)) / maxsize
        with unittest.mock.patch.object(random.Random, "random") as random_mock:
            random_mock.side_effect = [(limit + epsilon), (limit - epsilon)]
            self.gen._randbelow_without_getrandbits(n, maxsize=maxsize)
            self.assertEqual(random_mock.call_count, 2)

    def test_randrange_bug_1590891(self):
        start = 1000000000000
        stop = -100000000000000000000
        step = -200
        x = self.gen.randrange(start, stop, step)
        self.assertTrue((stop < x <= start))
        self.assertEqual(((x + stop) % step), 0)

    def test_choices_algorithms(self):
        choices = self.gen.choices
        n = 104729
        self.gen.seed(8675309)
        a = self.gen.choices(range(n), k=10000)
        self.gen.seed(8675309)
        b = self.gen.choices(range(n), ([1] * n), k=10000)
        self.assertEqual(a, b)
        self.gen.seed(8675309)
        c = self.gen.choices(range(n), cum_weights=range(1, (n + 1)), k=10000)
        self.assertEqual(a, c)
        population = ["Red", "Black", "Green"]
        weights = [18, 18, 2]
        cum_weights = [18, 36, 38]
        expanded_population = ((["Red"] * 18) + (["Black"] * 18)) + (["Green"] * 2)
        self.gen.seed(9035768)
        a = self.gen.choices(expanded_population, k=10000)
        self.gen.seed(9035768)
        b = self.gen.choices(population, weights, k=10000)
        self.assertEqual(a, b)
        self.gen.seed(9035768)
        c = self.gen.choices(population, cum_weights=cum_weights, k=10000)
        self.assertEqual(a, c)

    def test_randbytes(self):
        super().test_randbytes()
        seed = 8675309
        expected = b"3\xa8\xf9f\xf4\xa4\xd06\x19\x8f\x9f\x82\x02oe\xf0"
        self.gen.seed(seed)
        self.assertEqual(self.gen.randbytes(16), expected)
        self.gen.seed(seed)
        self.assertEqual(self.gen.randbytes(0), b"")
        self.assertEqual(self.gen.randbytes(16), expected)
        self.gen.seed(seed)
        self.assertEqual(b"".join([self.gen.randbytes(4) for _ in range(4)]), expected)
        self.gen.seed(seed)
        expected1 = expected[3::4]
        self.assertEqual(b"".join((self.gen.randbytes(1) for _ in range(4))), expected1)
        self.gen.seed(seed)
        expected2 = b"".join(
            (expected[(i + 2) : (i + 4)] for i in range(0, len(expected), 4))
        )
        self.assertEqual(b"".join((self.gen.randbytes(2) for _ in range(4))), expected2)
        self.gen.seed(seed)
        expected3 = b"".join(
            (expected[(i + 1) : (i + 4)] for i in range(0, len(expected), 4))
        )
        self.assertEqual(b"".join((self.gen.randbytes(3) for _ in range(4))), expected3)

    def test_randbytes_getrandbits(self):
        seed = 2849427419
        gen2 = random.Random()
        self.gen.seed(seed)
        gen2.seed(seed)
        for n in range(9):
            self.assertEqual(
                self.gen.randbytes(n), gen2.getrandbits((n * 8)).to_bytes(n, "little")
            )

    def test_sample_counts_equivalence(self):
        sample = self.gen.sample
        seed = self.gen.seed
        colors = ["red", "green", "blue", "orange", "black", "amber"]
        counts = [500, 200, 20, 10, 5, 1]
        k = 700
        seed(8675309)
        s1 = sample(colors, counts=counts, k=k)
        seed(8675309)
        expanded = [
            color for (color, count) in zip(colors, counts) for i in range(count)
        ]
        self.assertEqual(len(expanded), sum(counts))
        s2 = sample(expanded, k=k)
        self.assertEqual(s1, s2)
        pop = "abcdefghi"
        counts = [10, 9, 8, 7, 6, 5, 4, 3, 2]
        seed(8675309)
        s1 = "".join(sample(pop, counts=counts, k=30))
        expanded = "".join(
            [letter for (letter, count) in zip(pop, counts) for i in range(count)]
        )
        seed(8675309)
        s2 = "".join(sample(expanded, k=30))
        self.assertEqual(s1, s2)


def gamma(z, sqrt2pi=((2.0 * pi) ** 0.5)):
    if z < 0.5:
        return (pi / sin((pi * z))) / gamma((1.0 - z))
    az = z + (7.0 - 0.5)
    return (((az ** (z - 0.5)) / exp(az)) * sqrt2pi) * fsum(
        [
            0.9999999999995183,
            (676.5203681218835 / z),
            ((-1259.139216722289) / (z + 1.0)),
            (771.3234287757674 / (z + 2.0)),
            ((-176.6150291498386) / (z + 3.0)),
            (12.50734324009056 / (z + 4.0)),
            ((-0.1385710331296526) / (z + 5.0)),
            (9.934937113930748e-06 / (z + 6.0)),
            (1.659470187408462e-07 / (z + 7.0)),
        ]
    )


class TestDistributions(unittest.TestCase):
    def test_zeroinputs(self):
        g = random.Random()
        x = [g.random() for i in range(50)] + ([0.0] * 5)
        g.random = x[:].pop
        g.uniform(1, 10)
        g.random = x[:].pop
        g.paretovariate(1.0)
        g.random = x[:].pop
        g.expovariate(1.0)
        g.random = x[:].pop
        g.weibullvariate(1.0, 1.0)
        g.random = x[:].pop
        g.vonmisesvariate(1.0, 1.0)
        g.random = x[:].pop
        g.normalvariate(0.0, 1.0)
        g.random = x[:].pop
        g.gauss(0.0, 1.0)
        g.random = x[:].pop
        g.lognormvariate(0.0, 1.0)
        g.random = x[:].pop
        g.vonmisesvariate(0.0, 1.0)
        g.random = x[:].pop
        g.gammavariate(0.01, 1.0)
        g.random = x[:].pop
        g.gammavariate(1.0, 1.0)
        g.random = x[:].pop
        g.gammavariate(200.0, 1.0)
        g.random = x[:].pop
        g.betavariate(3.0, 3.0)
        g.random = x[:].pop
        g.triangular(0.0, 1.0, (1.0 / 3.0))

    def test_avg_std(self):
        g = random.Random()
        N = 5000
        x = [(i / float(N)) for i in range(1, N)]
        for (variate, args, mu, sigmasqrd) in [
            (g.uniform, (1.0, 10.0), ((10.0 + 1.0) / 2), (((10.0 - 1.0) ** 2) / 12)),
            (g.triangular, (0.0, 1.0, (1.0 / 3.0)), (4.0 / 9.0), ((7.0 / 9.0) / 18.0)),
            (g.expovariate, (1.5,), (1 / 1.5), (1 / (1.5 ** 2))),
            (g.vonmisesvariate, (1.23, 0), pi, ((pi ** 2) / 3)),
            (
                g.paretovariate,
                (5.0,),
                (5.0 / (5.0 - 1)),
                (5.0 / (((5.0 - 1) ** 2) * (5.0 - 2))),
            ),
            (
                g.weibullvariate,
                (1.0, 3.0),
                gamma((1 + (1 / 3.0))),
                (gamma((1 + (2 / 3.0))) - (gamma((1 + (1 / 3.0))) ** 2)),
            ),
        ]:
            g.random = x[:].pop
            y = []
            for i in range(len(x)):
                try:
                    y.append(variate(*args))
                except IndexError:
                    pass
            s1 = s2 = 0
            for e in y:
                s1 += e
                s2 += (e - mu) ** 2
            N = len(y)
            self.assertAlmostEqual(
                (s1 / N), mu, places=2, msg=("%s%r" % (variate.__name__, args))
            )
            self.assertAlmostEqual(
                (s2 / (N - 1)),
                sigmasqrd,
                places=2,
                msg=("%s%r" % (variate.__name__, args)),
            )

    def test_constant(self):
        g = random.Random()
        N = 100
        for (variate, args, expected) in [
            (g.uniform, (10.0, 10.0), 10.0),
            (g.triangular, (10.0, 10.0), 10.0),
            (g.triangular, (10.0, 10.0, 10.0), 10.0),
            (g.expovariate, (float("inf"),), 0.0),
            (g.vonmisesvariate, (3.0, float("inf")), 3.0),
            (g.gauss, (10.0, 0.0), 10.0),
            (g.lognormvariate, (0.0, 0.0), 1.0),
            (g.lognormvariate, ((-float("inf")), 0.0), 0.0),
            (g.normalvariate, (10.0, 0.0), 10.0),
            (g.paretovariate, (float("inf"),), 1.0),
            (g.weibullvariate, (10.0, float("inf")), 10.0),
            (g.weibullvariate, (0.0, 10.0), 0.0),
        ]:
            for i in range(N):
                self.assertEqual(variate(*args), expected)

    def test_von_mises_range(self):
        g = random.Random()
        N = 100
        for mu in (0.0, 0.1, 3.1, 6.2):
            for kappa in (0.0, 2.3, 500.0):
                for _ in range(N):
                    sample = g.vonmisesvariate(mu, kappa)
                    self.assertTrue(
                        (0 <= sample <= random.TWOPI),
                        msg="vonmisesvariate({}, {}) produced a result {} out of range [0, 2*pi]".format(
                            mu, kappa, sample
                        ),
                    )

    def test_von_mises_large_kappa(self):
        random.vonmisesvariate(0, 1000000000000000.0)
        random.vonmisesvariate(0, 1e100)

    def test_gammavariate_errors(self):
        self.assertRaises(ValueError, random.gammavariate, (-1), 3)
        self.assertRaises(ValueError, random.gammavariate, 0, 2)
        self.assertRaises(ValueError, random.gammavariate, 2, 0)
        self.assertRaises(ValueError, random.gammavariate, 1, (-3))

    @unittest.mock.patch("random.Random.random")
    def test_gammavariate_alpha_greater_one(self, random_mock):
        random_mock.side_effect = [1e-08, 0.5, 0.3]
        returned_value = random.gammavariate(1.1, 2.3)
        self.assertAlmostEqual(returned_value, 2.53)

    @unittest.mock.patch("random.Random.random")
    def test_gammavariate_alpha_equal_one(self, random_mock):
        random_mock.side_effect = [0.45]
        returned_value = random.gammavariate(1.0, 3.14)
        self.assertAlmostEqual(returned_value, 1.877208182372648)

    @unittest.mock.patch("random.Random.random")
    def test_gammavariate_alpha_equal_one_equals_expovariate(self, random_mock):
        beta = 3.14
        random_mock.side_effect = [1e-08, 1e-08]
        gammavariate_returned_value = random.gammavariate(1.0, beta)
        expovariate_returned_value = random.expovariate((1.0 / beta))
        self.assertAlmostEqual(gammavariate_returned_value, expovariate_returned_value)

    @unittest.mock.patch("random.Random.random")
    def test_gammavariate_alpha_between_zero_and_one(self, random_mock):
        _e = random._e
        _exp = random._exp
        _log = random._log
        alpha = 0.35
        beta = 1.45
        b = (_e + alpha) / _e
        epsilon = 0.01
        r1 = 0.8859296441566
        r2 = 0.3678794411714
        random_mock.side_effect = [r1, (r2 + epsilon), r1, r2]
        returned_value = random.gammavariate(alpha, beta)
        self.assertAlmostEqual(returned_value, 1.4499999999997544)
        r1 = 0.8959296441566
        r2 = 0.9445400408898141
        random_mock.side_effect = [r1, (r2 + epsilon), r1, r2]
        returned_value = random.gammavariate(alpha, beta)
        self.assertAlmostEqual(returned_value, 1.5830349561760781)

    @unittest.mock.patch("random.Random.gammavariate")
    def test_betavariate_return_zero(self, gammavariate_mock):
        gammavariate_mock.return_value = 0.0
        self.assertEqual(0.0, random.betavariate(2.71828, 3.14159))


class TestRandomSubclassing(unittest.TestCase):
    def test_random_subclass_with_kwargs(self):
        class Subclass(random.Random):
            def __init__(self, newarg=None):
                random.Random.__init__(self)

        Subclass(newarg=1)

    def test_subclasses_overriding_methods(self):
        class SubClass1(random.Random):
            def random(self):
                called.add("SubClass1.random")
                return random.Random.random(self)

            def getrandbits(self, n):
                called.add("SubClass1.getrandbits")
                return random.Random.getrandbits(self, n)

        called = set()
        SubClass1().randrange(42)
        self.assertEqual(called, {"SubClass1.getrandbits"})

        class SubClass2(random.Random):
            def random(self):
                called.add("SubClass2.random")
                return random.Random.random(self)

        called = set()
        SubClass2().randrange(42)
        self.assertEqual(called, {"SubClass2.random"})

        class SubClass3(SubClass2):
            def getrandbits(self, n):
                called.add("SubClass3.getrandbits")
                return random.Random.getrandbits(self, n)

        called = set()
        SubClass3().randrange(42)
        self.assertEqual(called, {"SubClass3.getrandbits"})

        class SubClass4(SubClass3):
            def random(self):
                called.add("SubClass4.random")
                return random.Random.random(self)

        called = set()
        SubClass4().randrange(42)
        self.assertEqual(called, {"SubClass4.random"})

        class Mixin1:
            def random(self):
                called.add("Mixin1.random")
                return random.Random.random(self)

        class Mixin2:
            def getrandbits(self, n):
                called.add("Mixin2.getrandbits")
                return random.Random.getrandbits(self, n)

        class SubClass5(Mixin1, random.Random):
            pass

        called = set()
        SubClass5().randrange(42)
        self.assertEqual(called, {"Mixin1.random"})

        class SubClass6(Mixin2, random.Random):
            pass

        called = set()
        SubClass6().randrange(42)
        self.assertEqual(called, {"Mixin2.getrandbits"})

        class SubClass7(Mixin1, Mixin2, random.Random):
            pass

        called = set()
        SubClass7().randrange(42)
        self.assertEqual(called, {"Mixin1.random"})

        class SubClass8(Mixin2, Mixin1, random.Random):
            pass

        called = set()
        SubClass8().randrange(42)
        self.assertEqual(called, {"Mixin2.getrandbits"})


class TestModule(unittest.TestCase):
    def testMagicConstants(self):
        self.assertAlmostEqual(random.NV_MAGICCONST, 1.71552776992141)
        self.assertAlmostEqual(random.TWOPI, 6.28318530718)
        self.assertAlmostEqual(random.LOG4, 1.38629436111989)
        self.assertAlmostEqual(random.SG_MAGICCONST, 2.50407739677627)

    def test__all__(self):
        self.assertTrue((set(random.__all__) <= set(dir(random))))

    @unittest.skipUnless(hasattr(os, "fork"), "fork() required")
    def test_after_fork(self):
        (r, w) = os.pipe()
        pid = os.fork()
        if pid == 0:
            try:
                val = random.getrandbits(128)
                with open(w, "w") as f:
                    f.write(str(val))
            finally:
                os._exit(0)
        else:
            os.close(w)
            val = random.getrandbits(128)
            with open(r, "r") as f:
                child_val = eval(f.read())
            self.assertNotEqual(val, child_val)
            support.wait_process(pid, exitcode=0)


if __name__ == "__main__":
    unittest.main()
