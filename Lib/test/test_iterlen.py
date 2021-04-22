" Test Iterator Length Transparency\n\nSome functions or methods which accept general iterable arguments have\noptional, more efficient code paths if they know how many items to expect.\nFor instance, map(func, iterable), will pre-allocate the exact amount of\nspace required whenever the iterable can report its length.\n\nThe desired invariant is:  len(it)==len(list(it)).\n\nA complication is that an iterable and iterator can be the same object. To\nmaintain the invariant, an iterator needs to dynamically update its length.\nFor instance, an iterable such as range(10) always reports its length as ten,\nbut it=iter(range(10)) starts at ten, and then goes to nine after next(it).\nHaving this capability means that map() can ignore the distinction between\nmap(func, iterable) and map(func, iter(iterable)).\n\nWhen the iterable is immutable, the implementation can straight-forwardly\nreport the original length minus the cumulative number of calls to next().\nThis is the case for tuples, range objects, and itertools.repeat().\n\nSome containers become temporarily immutable during iteration.  This includes\ndicts, sets, and collections.deque.  Their implementation is equally simple\nthough they need to permanently set their length to zero whenever there is\nan attempt to iterate after a length mutation.\n\nThe situation slightly more involved whenever an object allows length mutation\nduring iteration.  Lists and sequence iterators are dynamically updatable.\nSo, if a list is extended during iteration, the iterator will continue through\nthe new items.  If it shrinks to a point before the most recent iteration,\nthen no further items are available and the length is reported at zero.\n\nReversed objects can also be wrapped around mutable objects; however, any\nappends after the current position are ignored.  Any other approach leads\nto confusion and possibly returning the same item more than once.\n\nThe iterators not listed above, such as enumerate and the other itertools,\nare not length transparent because they have no way to distinguish between\niterables that report static length and iterators whose length changes with\neach call (i.e. the difference between enumerate('abc') and\nenumerate(iter('abc')).\n\n"
import unittest
from itertools import repeat
from collections import deque
from operator import length_hint

n = 10


class TestInvariantWithoutMutations:
    def test_invariant(self):
        it = self.it
        for i in reversed(range(1, (n + 1))):
            self.assertEqual(length_hint(it), i)
            next(it)
        self.assertEqual(length_hint(it), 0)
        self.assertRaises(StopIteration, next, it)
        self.assertEqual(length_hint(it), 0)


class TestTemporarilyImmutable(TestInvariantWithoutMutations):
    def test_immutable_during_iteration(self):
        it = self.it
        self.assertEqual(length_hint(it), n)
        next(it)
        self.assertEqual(length_hint(it), (n - 1))
        self.mutate()
        self.assertRaises(RuntimeError, next, it)
        self.assertEqual(length_hint(it), 0)


class TestRepeat(TestInvariantWithoutMutations, unittest.TestCase):
    def setUp(self):
        self.it = repeat(None, n)


class TestXrange(TestInvariantWithoutMutations, unittest.TestCase):
    def setUp(self):
        self.it = iter(range(n))


class TestXrangeCustomReversed(TestInvariantWithoutMutations, unittest.TestCase):
    def setUp(self):
        self.it = reversed(range(n))


class TestTuple(TestInvariantWithoutMutations, unittest.TestCase):
    def setUp(self):
        self.it = iter(tuple(range(n)))


class TestDeque(TestTemporarilyImmutable, unittest.TestCase):
    def setUp(self):
        d = deque(range(n))
        self.it = iter(d)
        self.mutate = d.pop


class TestDequeReversed(TestTemporarilyImmutable, unittest.TestCase):
    def setUp(self):
        d = deque(range(n))
        self.it = reversed(d)
        self.mutate = d.pop


class TestDictKeys(TestTemporarilyImmutable, unittest.TestCase):
    def setUp(self):
        d = dict.fromkeys(range(n))
        self.it = iter(d)
        self.mutate = d.popitem


class TestDictItems(TestTemporarilyImmutable, unittest.TestCase):
    def setUp(self):
        d = dict.fromkeys(range(n))
        self.it = iter(d.items())
        self.mutate = d.popitem


class TestDictValues(TestTemporarilyImmutable, unittest.TestCase):
    def setUp(self):
        d = dict.fromkeys(range(n))
        self.it = iter(d.values())
        self.mutate = d.popitem


class TestSet(TestTemporarilyImmutable, unittest.TestCase):
    def setUp(self):
        d = set(range(n))
        self.it = iter(d)
        self.mutate = d.pop


class TestList(TestInvariantWithoutMutations, unittest.TestCase):
    def setUp(self):
        self.it = iter(range(n))

    def test_mutation(self):
        d = list(range(n))
        it = iter(d)
        next(it)
        next(it)
        self.assertEqual(length_hint(it), (n - 2))
        d.append(n)
        self.assertEqual(length_hint(it), (n - 1))
        d[1:] = []
        self.assertEqual(length_hint(it), 0)
        self.assertEqual(list(it), [])
        d.extend(range(20))
        self.assertEqual(length_hint(it), 0)


class TestListReversed(TestInvariantWithoutMutations, unittest.TestCase):
    def setUp(self):
        self.it = reversed(range(n))

    def test_mutation(self):
        d = list(range(n))
        it = reversed(d)
        next(it)
        next(it)
        self.assertEqual(length_hint(it), (n - 2))
        d.append(n)
        self.assertEqual(length_hint(it), (n - 2))
        d[1:] = []
        self.assertEqual(length_hint(it), 0)
        self.assertEqual(list(it), [])
        d.extend(range(20))
        self.assertEqual(length_hint(it), 0)


class BadLen(object):
    def __iter__(self):
        return iter(range(10))

    def __len__(self):
        raise RuntimeError("hello")


class BadLengthHint(object):
    def __iter__(self):
        return iter(range(10))

    def __length_hint__(self):
        raise RuntimeError("hello")


class NoneLengthHint(object):
    def __iter__(self):
        return iter(range(10))

    def __length_hint__(self):
        return NotImplemented


class TestLengthHintExceptions(unittest.TestCase):
    def test_issue1242657(self):
        self.assertRaises(RuntimeError, list, BadLen())
        self.assertRaises(RuntimeError, list, BadLengthHint())
        self.assertRaises(RuntimeError, [].extend, BadLen())
        self.assertRaises(RuntimeError, [].extend, BadLengthHint())
        b = bytearray(range(10))
        self.assertRaises(RuntimeError, b.extend, BadLen())
        self.assertRaises(RuntimeError, b.extend, BadLengthHint())

    def test_invalid_hint(self):
        self.assertEqual(list(NoneLengthHint()), list(range(10)))


if __name__ == "__main__":
    unittest.main()
