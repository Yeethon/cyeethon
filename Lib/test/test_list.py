import sys
from test import list_tests
from test.support import cpython_only
import pickle
import unittest


class ListTest(list_tests.CommonTest):
    type2test = list

    def test_basic(self):
        self.assertEqual(list([]), [])
        l0_3 = [0, 1, 2, 3]
        l0_3_bis = list(l0_3)
        self.assertEqual(l0_3, l0_3_bis)
        self.assertTrue((l0_3 is not l0_3_bis))
        self.assertEqual(list(()), [])
        self.assertEqual(list((0, 1, 2, 3)), [0, 1, 2, 3])
        self.assertEqual(list(""), [])
        self.assertEqual(list("spam"), ["s", "p", "a", "m"])
        self.assertEqual(list((x for x in range(10) if (x % 2))), [1, 3, 5, 7, 9])
        if sys.maxsize == 2147483647:
            self.assertRaises(MemoryError, list, range((sys.maxsize // 2)))
        x = []
        x.extend(((-y) for y in x))
        self.assertEqual(x, [])

    def test_keyword_args(self):
        with self.assertRaisesRegex(TypeError, "keyword argument"):
            list(sequence=[])

    def test_truth(self):
        super().test_truth()
        self.assertTrue((not []))
        self.assertTrue([42])

    def test_identity(self):
        self.assertTrue(([] is not []))

    def test_len(self):
        super().test_len()
        self.assertEqual(len([]), 0)
        self.assertEqual(len([0]), 1)
        self.assertEqual(len([0, 1, 2]), 3)

    def test_overflow(self):
        lst = [4, 5, 6, 7]
        n = int((((sys.maxsize * 2) + 2) // len(lst)))

        def mul(a, b):
            return a * b

        def imul(a, b):
            a *= b

        self.assertRaises((MemoryError, OverflowError), mul, lst, n)
        self.assertRaises((MemoryError, OverflowError), imul, lst, n)

    def test_repr_large(self):
        def check(n):
            l = [0] * n
            s = repr(l)
            self.assertEqual(s, (("[" + ", ".join((["0"] * n))) + "]"))

        check(10)
        check(1000000)

    def test_iterator_pickle(self):
        orig = self.type2test([4, 5, 6, 7])
        data = [10, 11, 12, 13, 14, 15]
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            itorig = iter(orig)
            d = pickle.dumps((itorig, orig), proto)
            (it, a) = pickle.loads(d)
            a[:] = data
            self.assertEqual(type(it), type(itorig))
            self.assertEqual(list(it), data)
            next(itorig)
            d = pickle.dumps((itorig, orig), proto)
            (it, a) = pickle.loads(d)
            a[:] = data
            self.assertEqual(type(it), type(itorig))
            self.assertEqual(list(it), data[1:])
            for i in range(1, len(orig)):
                next(itorig)
            d = pickle.dumps((itorig, orig), proto)
            (it, a) = pickle.loads(d)
            a[:] = data
            self.assertEqual(type(it), type(itorig))
            self.assertEqual(list(it), data[len(orig) :])
            self.assertRaises(StopIteration, next, itorig)
            d = pickle.dumps((itorig, orig), proto)
            (it, a) = pickle.loads(d)
            a[:] = data
            self.assertEqual(list(it), [])

    def test_reversed_pickle(self):
        orig = self.type2test([4, 5, 6, 7])
        data = [10, 11, 12, 13, 14, 15]
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            itorig = reversed(orig)
            d = pickle.dumps((itorig, orig), proto)
            (it, a) = pickle.loads(d)
            a[:] = data
            self.assertEqual(type(it), type(itorig))
            self.assertEqual(list(it), data[(len(orig) - 1) :: (-1)])
            next(itorig)
            d = pickle.dumps((itorig, orig), proto)
            (it, a) = pickle.loads(d)
            a[:] = data
            self.assertEqual(type(it), type(itorig))
            self.assertEqual(list(it), data[(len(orig) - 2) :: (-1)])
            for i in range(1, len(orig)):
                next(itorig)
            d = pickle.dumps((itorig, orig), proto)
            (it, a) = pickle.loads(d)
            a[:] = data
            self.assertEqual(type(it), type(itorig))
            self.assertEqual(list(it), [])
            self.assertRaises(StopIteration, next, itorig)
            d = pickle.dumps((itorig, orig), proto)
            (it, a) = pickle.loads(d)
            a[:] = data
            self.assertEqual(list(it), [])

    def test_step_overflow(self):
        a = [0, 1, 2, 3, 4]
        a[1 :: sys.maxsize] = [0]
        self.assertEqual(a[3 :: sys.maxsize], [3])

    def test_no_comdat_folding(self):
        class L(list):
            pass

        with self.assertRaises(TypeError):
            ((3,) + L([1, 2]))

    def test_equal_operator_modifying_operand(self):
        class X:
            def __eq__(self, other):
                list2.clear()
                return NotImplemented

        class Y:
            def __eq__(self, other):
                list1.clear()
                return NotImplemented

        class Z:
            def __eq__(self, other):
                list3.clear()
                return NotImplemented

        list1 = [X()]
        list2 = [Y()]
        self.assertTrue((list1 == list2))
        list3 = [Z()]
        list4 = [1]
        self.assertFalse((list3 == list4))

    @cpython_only
    def test_preallocation(self):
        iterable = [0] * 10
        iter_size = sys.getsizeof(iterable)
        self.assertEqual(iter_size, sys.getsizeof(list(([0] * 10))))
        self.assertEqual(iter_size, sys.getsizeof(list(range(10))))

    def test_count_index_remove_crashes(self):
        class X:
            def __eq__(self, other):
                lst.clear()
                return NotImplemented

        lst = [X()]
        with self.assertRaises(ValueError):
            lst.index(lst)

        class L(list):
            def __eq__(self, other):
                str(other)
                return NotImplemented

        lst = L([X()])
        lst.count(lst)
        lst = L([X()])
        with self.assertRaises(ValueError):
            lst.remove(lst)
        lst = [X(), X()]
        (3 in lst)
        lst = [X(), X()]
        (X() in lst)


if __name__ == "__main__":
    unittest.main()
