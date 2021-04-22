from test import support, seq_tests
import unittest
import gc
import pickle

RUN_ALL_HASH_TESTS = False
JUST_SHOW_HASH_RESULTS = False


class TupleTest(seq_tests.CommonTest):
    type2test = tuple

    def test_getitem_error(self):
        t = ()
        msg = "tuple indices must be integers or slices"
        with self.assertRaisesRegex(TypeError, msg):
            t["a"]

    def test_constructors(self):
        super().test_constructors()
        self.assertEqual(tuple(), ())
        t0_3 = (0, 1, 2, 3)
        t0_3_bis = tuple(t0_3)
        self.assertTrue((t0_3 is t0_3_bis))
        self.assertEqual(tuple([]), ())
        self.assertEqual(tuple([0, 1, 2, 3]), (0, 1, 2, 3))
        self.assertEqual(tuple(""), ())
        self.assertEqual(tuple("spam"), ("s", "p", "a", "m"))
        self.assertEqual(tuple((x for x in range(10) if (x % 2))), (1, 3, 5, 7, 9))

    def test_keyword_args(self):
        with self.assertRaisesRegex(TypeError, "keyword argument"):
            tuple(sequence=())

    def test_truth(self):
        super().test_truth()
        self.assertTrue((not ()))
        self.assertTrue((42,))

    def test_len(self):
        super().test_len()
        self.assertEqual(len(()), 0)
        self.assertEqual(len((0,)), 1)
        self.assertEqual(len((0, 1, 2)), 3)

    def test_iadd(self):
        super().test_iadd()
        u = (0, 1)
        u2 = u
        u += (2, 3)
        self.assertTrue((u is not u2))

    def test_imul(self):
        super().test_imul()
        u = (0, 1)
        u2 = u
        u *= 3
        self.assertTrue((u is not u2))

    def test_tupleresizebug(self):
        def f():
            for i in range(1000):
                (yield i)

        self.assertEqual(list(tuple(f())), list(range(1000)))

    def test_hash_exact(self):
        def check_one_exact(t, e32, e64):
            got = hash(t)
            expected = e32 if (support.NHASHBITS == 32) else e64
            if got != expected:
                msg = f"FAIL hash({t!r}) == {got} != {expected}"
                self.fail(msg)

        check_one_exact((), 750394483, 5740354900026072187)
        check_one_exact((0,), 1214856301, (-8753497827991233192))
        check_one_exact((0, 0), (-168982784), (-8458139203682520985))
        check_one_exact((0.5,), 2077348973, (-408149959306781352))
        check_one_exact((0.5, (), ((-2), 3, (4, 6))), 714642271, (-1845940830829704396))

    def test_hash_optional(self):
        from itertools import product

        if not RUN_ALL_HASH_TESTS:
            return

        def tryone_inner(tag, nbins, hashes, expected=None, zlimit=None):
            from collections import Counter

            nballs = len(hashes)
            (mean, sdev) = support.collision_stats(nbins, nballs)
            c = Counter(hashes)
            collisions = nballs - len(c)
            z = (collisions - mean) / sdev
            pileup = max(c.values()) - 1
            del c
            got = (collisions, pileup)
            failed = False
            prefix = ""
            if (zlimit is not None) and (z > zlimit):
                failed = True
                prefix = f"FAIL z > {zlimit}; "
            if (expected is not None) and (got != expected):
                failed = True
                prefix += f"FAIL {got} != {expected}; "
            if failed or JUST_SHOW_HASH_RESULTS:
                msg = f"{prefix}{tag}; pileup {pileup:,} mean {mean:.1f} "
                msg += f"coll {collisions:,} z {z:+.1f}"
                if JUST_SHOW_HASH_RESULTS:
                    import sys

                    print(msg, file=sys.__stdout__)
                else:
                    self.fail(msg)

        def tryone(
            tag, xs, native32=None, native64=None, hi32=None, lo32=None, zlimit=None
        ):
            NHASHBITS = support.NHASHBITS
            hashes = list(map(hash, xs))
            tryone_inner(
                (tag + f"; {NHASHBITS}-bit hash codes"),
                (1 << NHASHBITS),
                hashes,
                (native32 if (NHASHBITS == 32) else native64),
                zlimit,
            )
            if NHASHBITS > 32:
                shift = NHASHBITS - 32
                tryone_inner(
                    (tag + "; 32-bit upper hash codes"),
                    (1 << 32),
                    [(h >> shift) for h in hashes],
                    hi32,
                    zlimit,
                )
                mask = (1 << 32) - 1
                tryone_inner(
                    (tag + "; 32-bit lower hash codes"),
                    (1 << 32),
                    [(h & mask) for h in hashes],
                    lo32,
                    zlimit,
                )

        tryone(
            "range(100) by 3",
            list(product(range(100), repeat=3)),
            (0, 0),
            (0, 0),
            (4, 1),
            (0, 0),
        )
        cands = list(range((-10), (-1))) + list(range(9))
        tryone(
            "-10 .. 8 by 4",
            list(product(cands, repeat=4)),
            (0, 0),
            (0, 0),
            (0, 0),
            (0, 0),
        )
        del cands
        L = [(n << 60) for n in range(100)]
        tryone(
            "0..99 << 60 by 3",
            list(product(L, repeat=3)),
            (0, 0),
            (0, 0),
            (0, 0),
            (324, 1),
        )
        del L
        tryone(
            "[-3, 3] by 18",
            list(product([(-3), 3], repeat=18)),
            (7, 1),
            (0, 0),
            (7, 1),
            (6, 1),
        )
        tryone(
            "[0, 0.5] by 18",
            list(product([0, 0.5], repeat=18)),
            (5, 1),
            (0, 0),
            (9, 1),
            (12, 1),
        )
        tryone(
            "4-char tuples",
            list(product("abcdefghijklmnopqrstuvwxyz", repeat=4)),
            zlimit=4.0,
        )
        N = 50
        base = list(range(N))
        xp = list(product(base, repeat=2))
        inps = (
            ((base + list(product(base, xp))) + list(product(xp, base))) + xp
        ) + list(zip(base))
        tryone("old tuple test", inps, (2, 1), (0, 0), (52, 49), (7, 1))
        del base, xp, inps
        n = 5
        A = [x for x in range((-n), (n + 1)) if (x != (-1))]
        B = A + [(a,) for a in A]
        L2 = list(product(A, repeat=2))
        L3 = L2 + list(product(A, repeat=3))
        L4 = L3 + list(product(A, repeat=4))
        T = A
        T += [(a,) for a in (B + L4)]
        T += product(L3, B)
        T += product(L2, repeat=2)
        T += product(B, L3)
        T += product(B, B, L2)
        T += product(B, L2, B)
        T += product(L2, B, B)
        T += product(B, repeat=4)
        assert len(T) == 345130
        tryone("new tuple test", T, (9, 1), (0, 0), (21, 5), (6, 1))

    def test_repr(self):
        l0 = tuple()
        l2 = (0, 1, 2)
        a0 = self.type2test(l0)
        a2 = self.type2test(l2)
        self.assertEqual(str(a0), repr(l0))
        self.assertEqual(str(a2), repr(l2))
        self.assertEqual(repr(a0), "()")
        self.assertEqual(repr(a2), "(0, 1, 2)")

    def _not_tracked(self, t):
        gc.collect()
        gc.collect()
        self.assertFalse(gc.is_tracked(t), t)

    def _tracked(self, t):
        self.assertTrue(gc.is_tracked(t), t)
        gc.collect()
        gc.collect()
        self.assertTrue(gc.is_tracked(t), t)

    @support.cpython_only
    def test_track_literals(self):
        (x, y, z) = (1.5, "a", [])
        self._not_tracked(())
        self._not_tracked((1,))
        self._not_tracked((1, 2))
        self._not_tracked((1, 2, "a"))
        self._not_tracked((1, 2, (None, True, False, ()), int))
        self._not_tracked((object(),))
        self._not_tracked(((1, x), y, (2, 3)))
        self._tracked(([],))
        self._tracked(([1],))
        self._tracked(({},))
        self._tracked((set(),))
        self._tracked((x, y, z))

    def check_track_dynamic(self, tp, always_track):
        (x, y, z) = (1.5, "a", [])
        check = self._tracked if always_track else self._not_tracked
        check(tp())
        check(tp([]))
        check(tp(set()))
        check(tp([1, x, y]))
        check(tp((obj for obj in [1, x, y])))
        check(tp(set([1, x, y])))
        check(tp((tuple([obj]) for obj in [1, x, y])))
        check(tuple((tp([obj]) for obj in [1, x, y])))
        self._tracked(tp([z]))
        self._tracked(tp([[x, y]]))
        self._tracked(tp([{x: y}]))
        self._tracked(tp((obj for obj in [x, y, z])))
        self._tracked(tp((tuple([obj]) for obj in [x, y, z])))
        self._tracked(tuple((tp([obj]) for obj in [x, y, z])))

    @support.cpython_only
    def test_track_dynamic(self):
        self.check_track_dynamic(tuple, False)

    @support.cpython_only
    def test_track_subtypes(self):
        class MyTuple(tuple):
            pass

        self.check_track_dynamic(MyTuple, True)

    @support.cpython_only
    def test_bug7466(self):
        self._not_tracked(tuple((gc.collect() for i in range(101))))

    def test_repr_large(self):
        def check(n):
            l = (0,) * n
            s = repr(l)
            self.assertEqual(s, (("(" + ", ".join((["0"] * n))) + ")"))

        check(10)
        check(1000000)

    def test_iterator_pickle(self):
        data = self.type2test([4, 5, 6, 7])
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            itorg = iter(data)
            d = pickle.dumps(itorg, proto)
            it = pickle.loads(d)
            self.assertEqual(type(itorg), type(it))
            self.assertEqual(self.type2test(it), self.type2test(data))
            it = pickle.loads(d)
            next(it)
            d = pickle.dumps(it, proto)
            self.assertEqual(self.type2test(it), self.type2test(data)[1:])

    def test_reversed_pickle(self):
        data = self.type2test([4, 5, 6, 7])
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            itorg = reversed(data)
            d = pickle.dumps(itorg, proto)
            it = pickle.loads(d)
            self.assertEqual(type(itorg), type(it))
            self.assertEqual(self.type2test(it), self.type2test(reversed(data)))
            it = pickle.loads(d)
            next(it)
            d = pickle.dumps(it, proto)
            self.assertEqual(self.type2test(it), self.type2test(reversed(data))[1:])

    def test_no_comdat_folding(self):
        class T(tuple):
            pass

        with self.assertRaises(TypeError):
            ([3] + T((1, 2)))

    def test_lexicographic_ordering(self):
        a = self.type2test([1, 2])
        b = self.type2test([1, 2, 0])
        c = self.type2test([1, 3])
        self.assertLess(a, b)
        self.assertLess(b, c)


if __name__ == "__main__":
    unittest.main()
