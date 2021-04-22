import copy
import gc
import pickle
import sys
import unittest
import weakref
import inspect
from test import support

try:
    import _testcapi
except ImportError:
    _testcapi = None


@unittest.skipUnless(
    ((_testcapi is not None) and hasattr(_testcapi, "raise_SIGINT_then_send_None")),
    "needs _testcapi.raise_SIGINT_then_send_None",
)
class SignalAndYieldFromTest(unittest.TestCase):
    def generator1(self):
        return (yield from self.generator2())

    def generator2(self):
        try:
            (yield)
        except KeyboardInterrupt:
            return "PASSED"
        else:
            return "FAILED"

    def test_raise_and_yield_from(self):
        gen = self.generator1()
        gen.send(None)
        try:
            _testcapi.raise_SIGINT_then_send_None(gen)
        except BaseException as _exc:
            exc = _exc
        self.assertIs(type(exc), StopIteration)
        self.assertEqual(exc.value, "PASSED")


class FinalizationTest(unittest.TestCase):
    def test_frame_resurrect(self):
        def gen():
            nonlocal frame
            try:
                (yield)
            finally:
                frame = sys._getframe()

        g = gen()
        wr = weakref.ref(g)
        next(g)
        del g
        support.gc_collect()
        self.assertIs(wr(), None)
        self.assertTrue(frame)
        del frame
        support.gc_collect()

    def test_refcycle(self):
        old_garbage = gc.garbage[:]
        finalized = False

        def gen():
            nonlocal finalized
            try:
                g = yield
                (yield 1)
            finally:
                finalized = True

        g = gen()
        next(g)
        g.send(g)
        self.assertGreater(sys.getrefcount(g), 2)
        self.assertFalse(finalized)
        del g
        support.gc_collect()
        self.assertTrue(finalized)
        self.assertEqual(gc.garbage, old_garbage)

    def test_lambda_generator(self):
        f = lambda: (yield 1)

        def g():
            return (yield 1)

        f2 = lambda: (yield from g())

        def g2():
            return (yield from g())

        f3 = lambda: (yield from f())

        def g3():
            return (yield from f())

        for gen_fun in (f, g, f2, g2, f3, g3):
            gen = gen_fun()
            self.assertEqual(next(gen), 1)
            with self.assertRaises(StopIteration) as cm:
                gen.send(2)
            self.assertEqual(cm.exception.value, 2)


class GeneratorTest(unittest.TestCase):
    def test_name(self):
        def func():
            (yield 1)

        gen = func()
        self.assertEqual(gen.__name__, "func")
        self.assertEqual(gen.__qualname__, "GeneratorTest.test_name.<locals>.func")
        gen.__name__ = "name"
        gen.__qualname__ = "qualname"
        self.assertEqual(gen.__name__, "name")
        self.assertEqual(gen.__qualname__, "qualname")
        self.assertRaises(TypeError, setattr, gen, "__name__", 123)
        self.assertRaises(TypeError, setattr, gen, "__qualname__", 123)
        self.assertRaises(TypeError, delattr, gen, "__name__")
        self.assertRaises(TypeError, delattr, gen, "__qualname__")
        func.__qualname__ = "func_qualname"
        func.__name__ = "func_name"
        gen = func()
        self.assertEqual(gen.__name__, "func_name")
        self.assertEqual(gen.__qualname__, "func_qualname")
        gen = (x for x in range(10))
        self.assertEqual(gen.__name__, "<genexpr>")
        self.assertEqual(gen.__qualname__, "GeneratorTest.test_name.<locals>.<genexpr>")

    def test_copy(self):
        def f():
            (yield 1)

        g = f()
        with self.assertRaises(TypeError):
            copy.copy(g)

    def test_pickle(self):
        def f():
            (yield 1)

        g = f()
        for proto in range((pickle.HIGHEST_PROTOCOL + 1)):
            with self.assertRaises((TypeError, pickle.PicklingError)):
                pickle.dumps(g, proto)


class ExceptionTest(unittest.TestCase):
    def test_except_throw(self):
        def store_raise_exc_generator():
            try:
                self.assertEqual(sys.exc_info()[0], None)
                (yield)
            except Exception as exc:
                self.assertEqual(sys.exc_info()[0], ValueError)
                self.assertIsNone(exc.__context__)
                (yield)
                self.assertEqual(sys.exc_info()[0], ValueError)
                (yield)
                raise

        make = store_raise_exc_generator()
        next(make)
        try:
            raise ValueError()
        except Exception as exc:
            try:
                make.throw(exc)
            except Exception:
                pass
        next(make)
        with self.assertRaises(ValueError) as cm:
            next(make)
        self.assertIsNone(cm.exception.__context__)
        self.assertEqual(sys.exc_info(), (None, None, None))

    def test_except_next(self):
        def gen():
            self.assertEqual(sys.exc_info()[0], ValueError)
            (yield "done")

        g = gen()
        try:
            raise ValueError
        except Exception:
            self.assertEqual(next(g), "done")
        self.assertEqual(sys.exc_info(), (None, None, None))

    def test_except_gen_except(self):
        def gen():
            try:
                self.assertEqual(sys.exc_info()[0], None)
                (yield)
                raise TypeError()
            except TypeError as exc:
                self.assertEqual(sys.exc_info()[0], TypeError)
                self.assertEqual(type(exc.__context__), ValueError)
            self.assertEqual(sys.exc_info()[0], ValueError)
            (yield)
            self.assertIsNone(sys.exc_info()[0])
            (yield "done")

        g = gen()
        next(g)
        try:
            raise ValueError
        except Exception:
            next(g)
        self.assertEqual(next(g), "done")
        self.assertEqual(sys.exc_info(), (None, None, None))

    def test_except_throw_exception_context(self):
        def gen():
            try:
                try:
                    self.assertEqual(sys.exc_info()[0], None)
                    (yield)
                except ValueError:
                    self.assertEqual(sys.exc_info()[0], ValueError)
                    raise TypeError()
            except Exception as exc:
                self.assertEqual(sys.exc_info()[0], TypeError)
                self.assertEqual(type(exc.__context__), ValueError)
            self.assertEqual(sys.exc_info()[0], ValueError)
            (yield)
            self.assertIsNone(sys.exc_info()[0])
            (yield "done")

        g = gen()
        next(g)
        try:
            raise ValueError
        except Exception as exc:
            g.throw(exc)
        self.assertEqual(next(g), "done")
        self.assertEqual(sys.exc_info(), (None, None, None))

    def test_stopiteration_error(self):
        def gen():
            raise StopIteration
            (yield)

        with self.assertRaisesRegex(RuntimeError, "raised StopIteration"):
            next(gen())

    def test_tutorial_stopiteration(self):
        def f():
            (yield 1)
            raise StopIteration
            (yield 2)

        g = f()
        self.assertEqual(next(g), 1)
        with self.assertRaisesRegex(RuntimeError, "raised StopIteration"):
            next(g)

    def test_return_tuple(self):
        def g():
            return (yield 1)

        gen = g()
        self.assertEqual(next(gen), 1)
        with self.assertRaises(StopIteration) as cm:
            gen.send((2,))
        self.assertEqual(cm.exception.value, (2,))

    def test_return_stopiteration(self):
        def g():
            return (yield 1)

        gen = g()
        self.assertEqual(next(gen), 1)
        with self.assertRaises(StopIteration) as cm:
            gen.send(StopIteration(2))
        self.assertIsInstance(cm.exception.value, StopIteration)
        self.assertEqual(cm.exception.value.value, 2)


class GeneratorThrowTest(unittest.TestCase):
    def test_exception_context_with_yield(self):
        def f():
            try:
                raise KeyError("a")
            except Exception:
                (yield)

        gen = f()
        gen.send(None)
        with self.assertRaises(ValueError) as cm:
            gen.throw(ValueError)
        context = cm.exception.__context__
        self.assertEqual((type(context), context.args), (KeyError, ("a",)))

    def test_exception_context_with_yield_inside_generator(self):
        def f():
            try:
                raise KeyError("a")
            except Exception:
                try:
                    (yield)
                except Exception as exc:
                    self.assertEqual(type(exc), ValueError)
                    context = exc.__context__
                    self.assertEqual((type(context), context.args), (KeyError, ("a",)))
                    (yield "b")

        gen = f()
        gen.send(None)
        actual = gen.throw(ValueError)
        self.assertEqual(actual, "b")

    def test_exception_context_with_yield_from(self):
        def f():
            (yield)

        def g():
            try:
                raise KeyError("a")
            except Exception:
                (yield from f())

        gen = g()
        gen.send(None)
        with self.assertRaises(ValueError) as cm:
            gen.throw(ValueError)
        context = cm.exception.__context__
        self.assertEqual((type(context), context.args), (KeyError, ("a",)))

    def test_exception_context_with_yield_from_with_context_cycle(self):
        has_cycle = None

        def f():
            (yield)

        def g(exc):
            nonlocal has_cycle
            try:
                raise exc
            except Exception:
                try:
                    (yield from f())
                except Exception as exc:
                    has_cycle = exc is exc.__context__
            (yield)

        exc = KeyError("a")
        gen = g(exc)
        gen.send(None)
        gen.throw(exc)
        self.assertEqual(has_cycle, False)

    def test_throw_after_none_exc_type(self):
        def g():
            try:
                raise KeyError
            except KeyError:
                pass
            try:
                (yield)
            except Exception:
                raise RuntimeError

        gen = g()
        gen.send(None)
        with self.assertRaises(RuntimeError) as cm:
            gen.throw(ValueError)


class GeneratorStackTraceTest(unittest.TestCase):
    def check_stack_names(self, frame, expected):
        names = []
        while frame:
            name = frame.f_code.co_name
            if name.startswith("check_") or name.startswith("call_"):
                break
            names.append(name)
            frame = frame.f_back
        self.assertEqual(names, expected)

    def check_yield_from_example(self, call_method):
        def f():
            self.check_stack_names(sys._getframe(), ["f", "g"])
            try:
                (yield)
            except Exception:
                pass
            self.check_stack_names(sys._getframe(), ["f", "g"])

        def g():
            self.check_stack_names(sys._getframe(), ["g"])
            (yield from f())
            self.check_stack_names(sys._getframe(), ["g"])

        gen = g()
        gen.send(None)
        try:
            call_method(gen)
        except StopIteration:
            pass

    def test_send_with_yield_from(self):
        def call_send(gen):
            gen.send(None)

        self.check_yield_from_example(call_send)

    def test_throw_with_yield_from(self):
        def call_throw(gen):
            gen.throw(RuntimeError)

        self.check_yield_from_example(call_throw)


class YieldFromTests(unittest.TestCase):
    def test_generator_gi_yieldfrom(self):
        def a():
            self.assertEqual(inspect.getgeneratorstate(gen_b), inspect.GEN_RUNNING)
            self.assertIsNone(gen_b.gi_yieldfrom)
            (yield)
            self.assertEqual(inspect.getgeneratorstate(gen_b), inspect.GEN_RUNNING)
            self.assertIsNone(gen_b.gi_yieldfrom)

        def b():
            self.assertIsNone(gen_b.gi_yieldfrom)
            (yield from a())
            self.assertIsNone(gen_b.gi_yieldfrom)
            (yield)
            self.assertIsNone(gen_b.gi_yieldfrom)

        gen_b = b()
        self.assertEqual(inspect.getgeneratorstate(gen_b), inspect.GEN_CREATED)
        self.assertIsNone(gen_b.gi_yieldfrom)
        gen_b.send(None)
        self.assertEqual(inspect.getgeneratorstate(gen_b), inspect.GEN_SUSPENDED)
        self.assertEqual(gen_b.gi_yieldfrom.gi_code.co_name, "a")
        gen_b.send(None)
        self.assertEqual(inspect.getgeneratorstate(gen_b), inspect.GEN_SUSPENDED)
        self.assertIsNone(gen_b.gi_yieldfrom)
        [] = gen_b
        self.assertEqual(inspect.getgeneratorstate(gen_b), inspect.GEN_CLOSED)
        self.assertIsNone(gen_b.gi_yieldfrom)


tutorial_tests = '\nLet\'s try a simple generator:\n\n    >>> def f():\n    ...    yield 1\n    ...    yield 2\n\n    >>> for i in f():\n    ...     print(i)\n    1\n    2\n    >>> g = f()\n    >>> next(g)\n    1\n    >>> next(g)\n    2\n\n"Falling off the end" stops the generator:\n\n    >>> next(g)\n    Traceback (most recent call last):\n      File "<stdin>", line 1, in ?\n      File "<stdin>", line 2, in g\n    StopIteration\n\n"return" also stops the generator:\n\n    >>> def f():\n    ...     yield 1\n    ...     return\n    ...     yield 2 # never reached\n    ...\n    >>> g = f()\n    >>> next(g)\n    1\n    >>> next(g)\n    Traceback (most recent call last):\n      File "<stdin>", line 1, in ?\n      File "<stdin>", line 3, in f\n    StopIteration\n    >>> next(g) # once stopped, can\'t be resumed\n    Traceback (most recent call last):\n      File "<stdin>", line 1, in ?\n    StopIteration\n\nHowever, "return" and StopIteration are not exactly equivalent:\n\n    >>> def g1():\n    ...     try:\n    ...         return\n    ...     except:\n    ...         yield 1\n    ...\n    >>> list(g1())\n    []\n\n    >>> def g2():\n    ...     try:\n    ...         raise StopIteration\n    ...     except:\n    ...         yield 42\n    >>> print(list(g2()))\n    [42]\n\nThis may be surprising at first:\n\n    >>> def g3():\n    ...     try:\n    ...         return\n    ...     finally:\n    ...         yield 1\n    ...\n    >>> list(g3())\n    [1]\n\nLet\'s create an alternate range() function implemented as a generator:\n\n    >>> def yrange(n):\n    ...     for i in range(n):\n    ...         yield i\n    ...\n    >>> list(yrange(5))\n    [0, 1, 2, 3, 4]\n\nGenerators always return to the most recent caller:\n\n    >>> def creator():\n    ...     r = yrange(5)\n    ...     print("creator", next(r))\n    ...     return r\n    ...\n    >>> def caller():\n    ...     r = creator()\n    ...     for i in r:\n    ...             print("caller", i)\n    ...\n    >>> caller()\n    creator 0\n    caller 1\n    caller 2\n    caller 3\n    caller 4\n\nGenerators can call other generators:\n\n    >>> def zrange(n):\n    ...     for i in yrange(n):\n    ...         yield i\n    ...\n    >>> list(zrange(5))\n    [0, 1, 2, 3, 4]\n\n'
pep_tests = '\n\nSpecification:  Yield\n\n    Restriction:  A generator cannot be resumed while it is actively\n    running:\n\n    >>> def g():\n    ...     i = next(me)\n    ...     yield i\n    >>> me = g()\n    >>> next(me)\n    Traceback (most recent call last):\n     ...\n      File "<string>", line 2, in g\n    ValueError: generator already executing\n\nSpecification: Return\n\n    Note that return isn\'t always equivalent to raising StopIteration:  the\n    difference lies in how enclosing try/except constructs are treated.\n    For example,\n\n        >>> def f1():\n        ...     try:\n        ...         return\n        ...     except:\n        ...        yield 1\n        >>> print(list(f1()))\n        []\n\n    because, as in any function, return simply exits, but\n\n        >>> def f2():\n        ...     try:\n        ...         raise StopIteration\n        ...     except:\n        ...         yield 42\n        >>> print(list(f2()))\n        [42]\n\n    because StopIteration is captured by a bare "except", as is any\n    exception.\n\nSpecification: Generators and Exception Propagation\n\n    >>> def f():\n    ...     return 1//0\n    >>> def g():\n    ...     yield f()  # the zero division exception propagates\n    ...     yield 42   # and we\'ll never get here\n    >>> k = g()\n    >>> next(k)\n    Traceback (most recent call last):\n      File "<stdin>", line 1, in ?\n      File "<stdin>", line 2, in g\n      File "<stdin>", line 2, in f\n    ZeroDivisionError: integer division or modulo by zero\n    >>> next(k)  # and the generator cannot be resumed\n    Traceback (most recent call last):\n      File "<stdin>", line 1, in ?\n    StopIteration\n    >>>\n\nSpecification: Try/Except/Finally\n\n    >>> def f():\n    ...     try:\n    ...         yield 1\n    ...         try:\n    ...             yield 2\n    ...             1//0\n    ...             yield 3  # never get here\n    ...         except ZeroDivisionError:\n    ...             yield 4\n    ...             yield 5\n    ...             raise\n    ...         except:\n    ...             yield 6\n    ...         yield 7     # the "raise" above stops this\n    ...     except:\n    ...         yield 8\n    ...     yield 9\n    ...     try:\n    ...         x = 12\n    ...     finally:\n    ...         yield 10\n    ...     yield 11\n    >>> print(list(f()))\n    [1, 2, 4, 5, 8, 9, 10, 11]\n    >>>\n\nGuido\'s binary tree example.\n\n    >>> # A binary tree class.\n    >>> class Tree:\n    ...\n    ...     def __init__(self, label, left=None, right=None):\n    ...         self.label = label\n    ...         self.left = left\n    ...         self.right = right\n    ...\n    ...     def __repr__(self, level=0, indent="    "):\n    ...         s = level*indent + repr(self.label)\n    ...         if self.left:\n    ...             s = s + "\\n" + self.left.__repr__(level+1, indent)\n    ...         if self.right:\n    ...             s = s + "\\n" + self.right.__repr__(level+1, indent)\n    ...         return s\n    ...\n    ...     def __iter__(self):\n    ...         return inorder(self)\n\n    >>> # Create a Tree from a list.\n    >>> def tree(list):\n    ...     n = len(list)\n    ...     if n == 0:\n    ...         return []\n    ...     i = n // 2\n    ...     return Tree(list[i], tree(list[:i]), tree(list[i+1:]))\n\n    >>> # Show it off: create a tree.\n    >>> t = tree("ABCDEFGHIJKLMNOPQRSTUVWXYZ")\n\n    >>> # A recursive generator that generates Tree labels in in-order.\n    >>> def inorder(t):\n    ...     if t:\n    ...         for x in inorder(t.left):\n    ...             yield x\n    ...         yield t.label\n    ...         for x in inorder(t.right):\n    ...             yield x\n\n    >>> # Show it off: create a tree.\n    >>> t = tree("ABCDEFGHIJKLMNOPQRSTUVWXYZ")\n    >>> # Print the nodes of the tree in in-order.\n    >>> for x in t:\n    ...     print(\' \'+x, end=\'\')\n     A B C D E F G H I J K L M N O P Q R S T U V W X Y Z\n\n    >>> # A non-recursive generator.\n    >>> def inorder(node):\n    ...     stack = []\n    ...     while node:\n    ...         while node.left:\n    ...             stack.append(node)\n    ...             node = node.left\n    ...         yield node.label\n    ...         while not node.right:\n    ...             try:\n    ...                 node = stack.pop()\n    ...             except IndexError:\n    ...                 return\n    ...             yield node.label\n    ...         node = node.right\n\n    >>> # Exercise the non-recursive generator.\n    >>> for x in t:\n    ...     print(\' \'+x, end=\'\')\n     A B C D E F G H I J K L M N O P Q R S T U V W X Y Z\n\n'
email_tests = "\n\nThe difference between yielding None and returning it.\n\n>>> def g():\n...     for i in range(3):\n...         yield None\n...     yield None\n...     return\n>>> list(g())\n[None, None, None, None]\n\nEnsure that explicitly raising StopIteration acts like any other exception\nin try/except, not like a return.\n\n>>> def g():\n...     yield 1\n...     try:\n...         raise StopIteration\n...     except:\n...         yield 2\n...     yield 3\n>>> list(g())\n[1, 2, 3]\n\nNext one was posted to c.l.py.\n\n>>> def gcomb(x, k):\n...     \"Generate all combinations of k elements from list x.\"\n...\n...     if k > len(x):\n...         return\n...     if k == 0:\n...         yield []\n...     else:\n...         first, rest = x[0], x[1:]\n...         # A combination does or doesn't contain first.\n...         # If it does, the remainder is a k-1 comb of rest.\n...         for c in gcomb(rest, k-1):\n...             c.insert(0, first)\n...             yield c\n...         # If it doesn't contain first, it's a k comb of rest.\n...         for c in gcomb(rest, k):\n...             yield c\n\n>>> seq = list(range(1, 5))\n>>> for k in range(len(seq) + 2):\n...     print(\"%d-combs of %s:\" % (k, seq))\n...     for c in gcomb(seq, k):\n...         print(\"   \", c)\n0-combs of [1, 2, 3, 4]:\n    []\n1-combs of [1, 2, 3, 4]:\n    [1]\n    [2]\n    [3]\n    [4]\n2-combs of [1, 2, 3, 4]:\n    [1, 2]\n    [1, 3]\n    [1, 4]\n    [2, 3]\n    [2, 4]\n    [3, 4]\n3-combs of [1, 2, 3, 4]:\n    [1, 2, 3]\n    [1, 2, 4]\n    [1, 3, 4]\n    [2, 3, 4]\n4-combs of [1, 2, 3, 4]:\n    [1, 2, 3, 4]\n5-combs of [1, 2, 3, 4]:\n\nFrom the Iterators list, about the types of these things.\n\n>>> def g():\n...     yield 1\n...\n>>> type(g)\n<class 'function'>\n>>> i = g()\n>>> type(i)\n<class 'generator'>\n>>> [s for s in dir(i) if not s.startswith('_')]\n['close', 'gi_code', 'gi_frame', 'gi_running', 'gi_yieldfrom', 'send', 'throw']\n>>> from test.support import HAVE_DOCSTRINGS\n>>> print(i.__next__.__doc__ if HAVE_DOCSTRINGS else 'Implement next(self).')\nImplement next(self).\n>>> iter(i) is i\nTrue\n>>> import types\n>>> isinstance(i, types.GeneratorType)\nTrue\n\nAnd more, added later.\n\n>>> i.gi_running\n0\n>>> type(i.gi_frame)\n<class 'frame'>\n>>> i.gi_running = 42\nTraceback (most recent call last):\n  ...\nAttributeError: attribute 'gi_running' of 'generator' objects is not writable\n>>> def g():\n...     yield me.gi_running\n>>> me = g()\n>>> me.gi_running\n0\n>>> next(me)\n1\n>>> me.gi_running\n0\n\nA clever union-find implementation from c.l.py, due to David Eppstein.\nSent: Friday, June 29, 2001 12:16 PM\nTo: python-list@python.org\nSubject: Re: PEP 255: Simple Generators\n\n>>> class disjointSet:\n...     def __init__(self, name):\n...         self.name = name\n...         self.parent = None\n...         self.generator = self.generate()\n...\n...     def generate(self):\n...         while not self.parent:\n...             yield self\n...         for x in self.parent.generator:\n...             yield x\n...\n...     def find(self):\n...         return next(self.generator)\n...\n...     def union(self, parent):\n...         if self.parent:\n...             raise ValueError(\"Sorry, I'm not a root!\")\n...         self.parent = parent\n...\n...     def __str__(self):\n...         return self.name\n\n>>> names = \"ABCDEFGHIJKLM\"\n>>> sets = [disjointSet(name) for name in names]\n>>> roots = sets[:]\n\n>>> import random\n>>> gen = random.Random(42)\n>>> while 1:\n...     for s in sets:\n...         print(\" %s->%s\" % (s, s.find()), end='')\n...     print()\n...     if len(roots) > 1:\n...         s1 = gen.choice(roots)\n...         roots.remove(s1)\n...         s2 = gen.choice(roots)\n...         s1.union(s2)\n...         print(\"merged\", s1, \"into\", s2)\n...     else:\n...         break\n A->A B->B C->C D->D E->E F->F G->G H->H I->I J->J K->K L->L M->M\nmerged K into B\n A->A B->B C->C D->D E->E F->F G->G H->H I->I J->J K->B L->L M->M\nmerged A into F\n A->F B->B C->C D->D E->E F->F G->G H->H I->I J->J K->B L->L M->M\nmerged E into F\n A->F B->B C->C D->D E->F F->F G->G H->H I->I J->J K->B L->L M->M\nmerged D into C\n A->F B->B C->C D->C E->F F->F G->G H->H I->I J->J K->B L->L M->M\nmerged M into C\n A->F B->B C->C D->C E->F F->F G->G H->H I->I J->J K->B L->L M->C\nmerged J into B\n A->F B->B C->C D->C E->F F->F G->G H->H I->I J->B K->B L->L M->C\nmerged B into C\n A->F B->C C->C D->C E->F F->F G->G H->H I->I J->C K->C L->L M->C\nmerged F into G\n A->G B->C C->C D->C E->G F->G G->G H->H I->I J->C K->C L->L M->C\nmerged L into C\n A->G B->C C->C D->C E->G F->G G->G H->H I->I J->C K->C L->C M->C\nmerged G into I\n A->I B->C C->C D->C E->I F->I G->I H->H I->I J->C K->C L->C M->C\nmerged I into H\n A->H B->C C->C D->C E->H F->H G->H H->H I->H J->C K->C L->C M->C\nmerged C into H\n A->H B->H C->H D->H E->H F->H G->H H->H I->H J->H K->H L->H M->H\n\n"
fun_tests = '\n\nBuild up to a recursive Sieve of Eratosthenes generator.\n\n>>> def firstn(g, n):\n...     return [next(g) for i in range(n)]\n\n>>> def intsfrom(i):\n...     while 1:\n...         yield i\n...         i += 1\n\n>>> firstn(intsfrom(5), 7)\n[5, 6, 7, 8, 9, 10, 11]\n\n>>> def exclude_multiples(n, ints):\n...     for i in ints:\n...         if i % n:\n...             yield i\n\n>>> firstn(exclude_multiples(3, intsfrom(1)), 6)\n[1, 2, 4, 5, 7, 8]\n\n>>> def sieve(ints):\n...     prime = next(ints)\n...     yield prime\n...     not_divisible_by_prime = exclude_multiples(prime, ints)\n...     for p in sieve(not_divisible_by_prime):\n...         yield p\n\n>>> primes = sieve(intsfrom(2))\n>>> firstn(primes, 20)\n[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]\n\n\nAnother famous problem:  generate all integers of the form\n    2**i * 3**j  * 5**k\nin increasing order, where i,j,k >= 0.  Trickier than it may look at first!\nTry writing it without generators, and correctly, and without generating\n3 internal results for each result output.\n\n>>> def times(n, g):\n...     for i in g:\n...         yield n * i\n>>> firstn(times(10, intsfrom(1)), 10)\n[10, 20, 30, 40, 50, 60, 70, 80, 90, 100]\n\n>>> def merge(g, h):\n...     ng = next(g)\n...     nh = next(h)\n...     while 1:\n...         if ng < nh:\n...             yield ng\n...             ng = next(g)\n...         elif ng > nh:\n...             yield nh\n...             nh = next(h)\n...         else:\n...             yield ng\n...             ng = next(g)\n...             nh = next(h)\n\nThe following works, but is doing a whale of a lot of redundant work --\nit\'s not clear how to get the internal uses of m235 to share a single\ngenerator.  Note that me_times2 (etc) each need to see every element in the\nresult sequence.  So this is an example where lazy lists are more natural\n(you can look at the head of a lazy list any number of times).\n\n>>> def m235():\n...     yield 1\n...     me_times2 = times(2, m235())\n...     me_times3 = times(3, m235())\n...     me_times5 = times(5, m235())\n...     for i in merge(merge(me_times2,\n...                          me_times3),\n...                    me_times5):\n...         yield i\n\nDon\'t print "too many" of these -- the implementation above is extremely\ninefficient:  each call of m235() leads to 3 recursive calls, and in\nturn each of those 3 more, and so on, and so on, until we\'ve descended\nenough levels to satisfy the print stmts.  Very odd:  when I printed 5\nlines of results below, this managed to screw up Win98\'s malloc in "the\nusual" way, i.e. the heap grew over 4Mb so Win98 started fragmenting\naddress space, and it *looked* like a very slow leak.\n\n>>> result = m235()\n>>> for i in range(3):\n...     print(firstn(result, 15))\n[1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24]\n[25, 27, 30, 32, 36, 40, 45, 48, 50, 54, 60, 64, 72, 75, 80]\n[81, 90, 96, 100, 108, 120, 125, 128, 135, 144, 150, 160, 162, 180, 192]\n\nHeh.  Here\'s one way to get a shared list, complete with an excruciating\nnamespace renaming trick.  The *pretty* part is that the times() and merge()\nfunctions can be reused as-is, because they only assume their stream\narguments are iterable -- a LazyList is the same as a generator to times().\n\n>>> class LazyList:\n...     def __init__(self, g):\n...         self.sofar = []\n...         self.fetch = g.__next__\n...\n...     def __getitem__(self, i):\n...         sofar, fetch = self.sofar, self.fetch\n...         while i >= len(sofar):\n...             sofar.append(fetch())\n...         return sofar[i]\n\n>>> def m235():\n...     yield 1\n...     # Gack:  m235 below actually refers to a LazyList.\n...     me_times2 = times(2, m235)\n...     me_times3 = times(3, m235)\n...     me_times5 = times(5, m235)\n...     for i in merge(merge(me_times2,\n...                          me_times3),\n...                    me_times5):\n...         yield i\n\nPrint as many of these as you like -- *this* implementation is memory-\nefficient.\n\n>>> m235 = LazyList(m235())\n>>> for i in range(5):\n...     print([m235[j] for j in range(15*i, 15*(i+1))])\n[1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24]\n[25, 27, 30, 32, 36, 40, 45, 48, 50, 54, 60, 64, 72, 75, 80]\n[81, 90, 96, 100, 108, 120, 125, 128, 135, 144, 150, 160, 162, 180, 192]\n[200, 216, 225, 240, 243, 250, 256, 270, 288, 300, 320, 324, 360, 375, 384]\n[400, 405, 432, 450, 480, 486, 500, 512, 540, 576, 600, 625, 640, 648, 675]\n\nYe olde Fibonacci generator, LazyList style.\n\n>>> def fibgen(a, b):\n...\n...     def sum(g, h):\n...         while 1:\n...             yield next(g) + next(h)\n...\n...     def tail(g):\n...         next(g)    # throw first away\n...         for x in g:\n...             yield x\n...\n...     yield a\n...     yield b\n...     for s in sum(iter(fib),\n...                  tail(iter(fib))):\n...         yield s\n\n>>> fib = LazyList(fibgen(1, 2))\n>>> firstn(iter(fib), 17)\n[1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584]\n\n\nRunning after your tail with itertools.tee (new in version 2.4)\n\nThe algorithms "m235" (Hamming) and Fibonacci presented above are both\nexamples of a whole family of FP (functional programming) algorithms\nwhere a function produces and returns a list while the production algorithm\nsuppose the list as already produced by recursively calling itself.\nFor these algorithms to work, they must:\n\n- produce at least a first element without presupposing the existence of\n  the rest of the list\n- produce their elements in a lazy manner\n\nTo work efficiently, the beginning of the list must not be recomputed over\nand over again. This is ensured in most FP languages as a built-in feature.\nIn python, we have to explicitly maintain a list of already computed results\nand abandon genuine recursivity.\n\nThis is what had been attempted above with the LazyList class. One problem\nwith that class is that it keeps a list of all of the generated results and\ntherefore continually grows. This partially defeats the goal of the generator\nconcept, viz. produce the results only as needed instead of producing them\nall and thereby wasting memory.\n\nThanks to itertools.tee, it is now clear "how to get the internal uses of\nm235 to share a single generator".\n\n>>> from itertools import tee\n>>> def m235():\n...     def _m235():\n...         yield 1\n...         for n in merge(times(2, m2),\n...                        merge(times(3, m3),\n...                              times(5, m5))):\n...             yield n\n...     m1 = _m235()\n...     m2, m3, m5, mRes = tee(m1, 4)\n...     return mRes\n\n>>> it = m235()\n>>> for i in range(5):\n...     print(firstn(it, 15))\n[1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24]\n[25, 27, 30, 32, 36, 40, 45, 48, 50, 54, 60, 64, 72, 75, 80]\n[81, 90, 96, 100, 108, 120, 125, 128, 135, 144, 150, 160, 162, 180, 192]\n[200, 216, 225, 240, 243, 250, 256, 270, 288, 300, 320, 324, 360, 375, 384]\n[400, 405, 432, 450, 480, 486, 500, 512, 540, 576, 600, 625, 640, 648, 675]\n\nThe "tee" function does just what we want. It internally keeps a generated\nresult for as long as it has not been "consumed" from all of the duplicated\niterators, whereupon it is deleted. You can therefore print the hamming\nsequence during hours without increasing memory usage, or very little.\n\nThe beauty of it is that recursive running-after-their-tail FP algorithms\nare quite straightforwardly expressed with this Python idiom.\n\nYe olde Fibonacci generator, tee style.\n\n>>> def fib():\n...\n...     def _isum(g, h):\n...         while 1:\n...             yield next(g) + next(h)\n...\n...     def _fib():\n...         yield 1\n...         yield 2\n...         next(fibTail) # throw first away\n...         for res in _isum(fibHead, fibTail):\n...             yield res\n...\n...     realfib = _fib()\n...     fibHead, fibTail, fibRes = tee(realfib, 3)\n...     return fibRes\n\n>>> firstn(fib(), 17)\n[1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584]\n\n'
syntax_tests = "\n\nThese are fine:\n\n>>> def f():\n...     yield 1\n...     return\n\n>>> def f():\n...     try:\n...         yield 1\n...     finally:\n...         pass\n\n>>> def f():\n...     try:\n...         try:\n...             1//0\n...         except ZeroDivisionError:\n...             yield 666\n...         except:\n...             pass\n...     finally:\n...         pass\n\n>>> def f():\n...     try:\n...         try:\n...             yield 12\n...             1//0\n...         except ZeroDivisionError:\n...             yield 666\n...         except:\n...             try:\n...                 x = 12\n...             finally:\n...                 yield 12\n...     except:\n...         return\n>>> list(f())\n[12, 666]\n\n>>> def f():\n...    yield\n>>> type(f())\n<class 'generator'>\n\n\n>>> def f():\n...    if 0:\n...        yield\n>>> type(f())\n<class 'generator'>\n\n\n>>> def f():\n...     if 0:\n...         yield 1\n>>> type(f())\n<class 'generator'>\n\n>>> def f():\n...    if \"\":\n...        yield None\n>>> type(f())\n<class 'generator'>\n\n>>> def f():\n...     return\n...     try:\n...         if x==4:\n...             pass\n...         elif 0:\n...             try:\n...                 1//0\n...             except SyntaxError:\n...                 pass\n...             else:\n...                 if 0:\n...                     while 12:\n...                         x += 1\n...                         yield 2 # don't blink\n...                         f(a, b, c, d, e)\n...         else:\n...             pass\n...     except:\n...         x = 1\n...     return\n>>> type(f())\n<class 'generator'>\n\n>>> def f():\n...     if 0:\n...         def g():\n...             yield 1\n...\n>>> type(f())\n<class 'NoneType'>\n\n>>> def f():\n...     if 0:\n...         class C:\n...             def __init__(self):\n...                 yield 1\n...             def f(self):\n...                 yield 2\n>>> type(f())\n<class 'NoneType'>\n\n>>> def f():\n...     if 0:\n...         return\n...     if 0:\n...         yield 2\n>>> type(f())\n<class 'generator'>\n\nThis one caused a crash (see SF bug 567538):\n\n>>> def f():\n...     for i in range(3):\n...         try:\n...             continue\n...         finally:\n...             yield i\n...\n>>> g = f()\n>>> print(next(g))\n0\n>>> print(next(g))\n1\n>>> print(next(g))\n2\n>>> print(next(g))\nTraceback (most recent call last):\nStopIteration\n\n\nTest the gi_code attribute\n\n>>> def f():\n...     yield 5\n...\n>>> g = f()\n>>> g.gi_code is f.__code__\nTrue\n>>> next(g)\n5\n>>> next(g)\nTraceback (most recent call last):\nStopIteration\n>>> g.gi_code is f.__code__\nTrue\n\n\nTest the __name__ attribute and the repr()\n\n>>> def f():\n...    yield 5\n...\n>>> g = f()\n>>> g.__name__\n'f'\n>>> repr(g)  # doctest: +ELLIPSIS\n'<generator object f at ...>'\n\nLambdas shouldn't have their usual return behavior.\n\n>>> x = lambda: (yield 1)\n>>> list(x())\n[1]\n\n>>> x = lambda: ((yield 1), (yield 2))\n>>> list(x())\n[1, 2]\n"


def simple_conjoin(gs):
    values = [None] * len(gs)

    def gen(i):
        if i >= len(gs):
            (yield values)
        else:
            for values[i] in gs[i]():
                for x in gen((i + 1)):
                    (yield x)

    for x in gen(0):
        (yield x)


def conjoin(gs):
    n = len(gs)
    values = [None] * n

    def gen(i):
        if i >= n:
            (yield values)
        elif (n - i) % 3:
            ip1 = i + 1
            for values[i] in gs[i]():
                for x in gen(ip1):
                    (yield x)
        else:
            for x in _gen3(i):
                (yield x)

    def _gen3(i):
        assert (i < n) and (((n - i) % 3) == 0)
        (ip1, ip2, ip3) = ((i + 1), (i + 2), (i + 3))
        (g, g1, g2) = gs[i:ip3]
        if ip3 >= n:
            for values[i] in g():
                for values[ip1] in g1():
                    for values[ip2] in g2():
                        (yield values)
        else:
            for values[i] in g():
                for values[ip1] in g1():
                    for values[ip2] in g2():
                        for x in _gen3(ip3):
                            (yield x)

    for x in gen(0):
        (yield x)


def flat_conjoin(gs):
    n = len(gs)
    values = [None] * n
    iters = [None] * n
    _StopIteration = StopIteration
    i = 0
    while 1:
        try:
            while i < n:
                it = iters[i] = gs[i]().__next__
                values[i] = it()
                i += 1
        except _StopIteration:
            pass
        else:
            assert i == n
            (yield values)
        i -= 1
        while i >= 0:
            try:
                values[i] = iters[i]()
                i += 1
                break
            except _StopIteration:
                i -= 1
        else:
            assert i < 0
            break


class Queens:
    def __init__(self, n):
        self.n = n
        rangen = range(n)
        self.rowgenerators = []
        for i in rangen:
            rowuses = [
                (
                    ((1 << j) | (1 << ((((n + i) - j) + n) - 1)))
                    | (1 << ((((n + (2 * n)) - 1) + i) + j))
                )
                for j in rangen
            ]

            def rowgen(rowuses=rowuses):
                for j in rangen:
                    uses = rowuses[j]
                    if (uses & self.used) == 0:
                        self.used |= uses
                        (yield j)
                        self.used &= ~uses

            self.rowgenerators.append(rowgen)

    def solve(self):
        self.used = 0
        for row2col in conjoin(self.rowgenerators):
            (yield row2col)

    def printsolution(self, row2col):
        n = self.n
        assert n == len(row2col)
        sep = "+" + ("-+" * n)
        print(sep)
        for i in range(n):
            squares = [" " for j in range(n)]
            squares[row2col[i]] = "Q"
            print((("|" + "|".join(squares)) + "|"))
            print(sep)


class Knights:
    def __init__(self, m, n, hard=0):
        (self.m, self.n) = (m, n)
        succs = self.succs = []

        def remove_from_successors(i0, len=len):
            ne0 = ne1 = 0
            for i in succs[i0]:
                s = succs[i]
                s.remove(i0)
                e = len(s)
                if e == 0:
                    ne0 += 1
                elif e == 1:
                    ne1 += 1
            return (ne0 == 0) and (ne1 < 2)

        def add_to_successors(i0):
            for i in succs[i0]:
                succs[i].append(i0)

        def first():
            if (m < 1) or (n < 1):
                return
            corner = self.coords2index(0, 0)
            remove_from_successors(corner)
            self.lastij = corner
            (yield corner)
            add_to_successors(corner)

        def second():
            corner = self.coords2index(0, 0)
            assert self.lastij == corner
            if (m < 3) or (n < 3):
                return
            assert len(succs[corner]) == 2
            assert self.coords2index(1, 2) in succs[corner]
            assert self.coords2index(2, 1) in succs[corner]
            for (i, j) in ((1, 2), (2, 1)):
                this = self.coords2index(i, j)
                final = self.coords2index((3 - i), (3 - j))
                self.final = final
                remove_from_successors(this)
                succs[final].append(corner)
                self.lastij = this
                (yield this)
                succs[final].remove(corner)
                add_to_successors(this)

        def advance(len=len):
            candidates = []
            for i in succs[self.lastij]:
                e = len(succs[i])
                assert e > 0, "else remove_from_successors() pruning flawed"
                if e == 1:
                    candidates = [(e, i)]
                    break
                candidates.append((e, i))
            else:
                candidates.sort()
            for (e, i) in candidates:
                if i != self.final:
                    if remove_from_successors(i):
                        self.lastij = i
                        (yield i)
                    add_to_successors(i)

        def advance_hard(vmid=((m - 1) / 2.0), hmid=((n - 1) / 2.0), len=len):
            candidates = []
            for i in succs[self.lastij]:
                e = len(succs[i])
                assert e > 0, "else remove_from_successors() pruning flawed"
                if e == 1:
                    candidates = [(e, 0, i)]
                    break
                (i1, j1) = self.index2coords(i)
                d = ((i1 - vmid) ** 2) + ((j1 - hmid) ** 2)
                candidates.append((e, (-d), i))
            else:
                candidates.sort()
            for (e, d, i) in candidates:
                if i != self.final:
                    if remove_from_successors(i):
                        self.lastij = i
                        (yield i)
                    add_to_successors(i)

        def last():
            assert self.final in succs[self.lastij]
            (yield self.final)

        if (m * n) < 4:
            self.squaregenerators = [first]
        else:
            self.squaregenerators = (
                [first, second]
                + ([((hard and advance_hard) or advance)] * ((m * n) - 3))
            ) + [last]

    def coords2index(self, i, j):
        assert 0 <= i < self.m
        assert 0 <= j < self.n
        return (i * self.n) + j

    def index2coords(self, index):
        assert 0 <= index < (self.m * self.n)
        return divmod(index, self.n)

    def _init_board(self):
        succs = self.succs
        del succs[:]
        (m, n) = (self.m, self.n)
        c2i = self.coords2index
        offsets = [
            (1, 2),
            (2, 1),
            (2, (-1)),
            (1, (-2)),
            ((-1), (-2)),
            ((-2), (-1)),
            ((-2), 1),
            ((-1), 2),
        ]
        rangen = range(n)
        for i in range(m):
            for j in rangen:
                s = [
                    c2i((i + io), (j + jo))
                    for (io, jo) in offsets
                    if ((0 <= (i + io) < m) and (0 <= (j + jo) < n))
                ]
                succs.append(s)

    def solve(self):
        self._init_board()
        for x in conjoin(self.squaregenerators):
            (yield x)

    def printsolution(self, x):
        (m, n) = (self.m, self.n)
        assert len(x) == (m * n)
        w = len(str((m * n)))
        format = ("%" + str(w)) + "d"
        squares = [([None] * n) for i in range(m)]
        k = 1
        for i in x:
            (i1, j1) = self.index2coords(i)
            squares[i1][j1] = format % k
            k += 1
        sep = "+" + ((("-" * w) + "+") * n)
        print(sep)
        for i in range(m):
            row = squares[i]
            print((("|" + "|".join(row)) + "|"))
            print(sep)


conjoin_tests = '\n\nGenerate the 3-bit binary numbers in order.  This illustrates dumbest-\npossible use of conjoin, just to generate the full cross-product.\n\n>>> for c in conjoin([lambda: iter((0, 1))] * 3):\n...     print(c)\n[0, 0, 0]\n[0, 0, 1]\n[0, 1, 0]\n[0, 1, 1]\n[1, 0, 0]\n[1, 0, 1]\n[1, 1, 0]\n[1, 1, 1]\n\nFor efficiency in typical backtracking apps, conjoin() yields the same list\nobject each time.  So if you want to save away a full account of its\ngenerated sequence, you need to copy its results.\n\n>>> def gencopy(iterator):\n...     for x in iterator:\n...         yield x[:]\n\n>>> for n in range(10):\n...     all = list(gencopy(conjoin([lambda: iter((0, 1))] * n)))\n...     print(n, len(all), all[0] == [0] * n, all[-1] == [1] * n)\n0 1 True True\n1 2 True True\n2 4 True True\n3 8 True True\n4 16 True True\n5 32 True True\n6 64 True True\n7 128 True True\n8 256 True True\n9 512 True True\n\nAnd run an 8-queens solver.\n\n>>> q = Queens(8)\n>>> LIMIT = 2\n>>> count = 0\n>>> for row2col in q.solve():\n...     count += 1\n...     if count <= LIMIT:\n...         print("Solution", count)\n...         q.printsolution(row2col)\nSolution 1\n+-+-+-+-+-+-+-+-+\n|Q| | | | | | | |\n+-+-+-+-+-+-+-+-+\n| | | | |Q| | | |\n+-+-+-+-+-+-+-+-+\n| | | | | | | |Q|\n+-+-+-+-+-+-+-+-+\n| | | | | |Q| | |\n+-+-+-+-+-+-+-+-+\n| | |Q| | | | | |\n+-+-+-+-+-+-+-+-+\n| | | | | | |Q| |\n+-+-+-+-+-+-+-+-+\n| |Q| | | | | | |\n+-+-+-+-+-+-+-+-+\n| | | |Q| | | | |\n+-+-+-+-+-+-+-+-+\nSolution 2\n+-+-+-+-+-+-+-+-+\n|Q| | | | | | | |\n+-+-+-+-+-+-+-+-+\n| | | | | |Q| | |\n+-+-+-+-+-+-+-+-+\n| | | | | | | |Q|\n+-+-+-+-+-+-+-+-+\n| | |Q| | | | | |\n+-+-+-+-+-+-+-+-+\n| | | | | | |Q| |\n+-+-+-+-+-+-+-+-+\n| | | |Q| | | | |\n+-+-+-+-+-+-+-+-+\n| |Q| | | | | | |\n+-+-+-+-+-+-+-+-+\n| | | | |Q| | | |\n+-+-+-+-+-+-+-+-+\n\n>>> print(count, "solutions in all.")\n92 solutions in all.\n\nAnd run a Knight\'s Tour on a 10x10 board.  Note that there are about\n20,000 solutions even on a 6x6 board, so don\'t dare run this to exhaustion.\n\n>>> k = Knights(10, 10)\n>>> LIMIT = 2\n>>> count = 0\n>>> for x in k.solve():\n...     count += 1\n...     if count <= LIMIT:\n...         print("Solution", count)\n...         k.printsolution(x)\n...     else:\n...         break\nSolution 1\n+---+---+---+---+---+---+---+---+---+---+\n|  1| 58| 27| 34|  3| 40| 29| 10|  5|  8|\n+---+---+---+---+---+---+---+---+---+---+\n| 26| 35|  2| 57| 28| 33|  4|  7| 30| 11|\n+---+---+---+---+---+---+---+---+---+---+\n| 59|100| 73| 36| 41| 56| 39| 32|  9|  6|\n+---+---+---+---+---+---+---+---+---+---+\n| 74| 25| 60| 55| 72| 37| 42| 49| 12| 31|\n+---+---+---+---+---+---+---+---+---+---+\n| 61| 86| 99| 76| 63| 52| 47| 38| 43| 50|\n+---+---+---+---+---+---+---+---+---+---+\n| 24| 75| 62| 85| 54| 71| 64| 51| 48| 13|\n+---+---+---+---+---+---+---+---+---+---+\n| 87| 98| 91| 80| 77| 84| 53| 46| 65| 44|\n+---+---+---+---+---+---+---+---+---+---+\n| 90| 23| 88| 95| 70| 79| 68| 83| 14| 17|\n+---+---+---+---+---+---+---+---+---+---+\n| 97| 92| 21| 78| 81| 94| 19| 16| 45| 66|\n+---+---+---+---+---+---+---+---+---+---+\n| 22| 89| 96| 93| 20| 69| 82| 67| 18| 15|\n+---+---+---+---+---+---+---+---+---+---+\nSolution 2\n+---+---+---+---+---+---+---+---+---+---+\n|  1| 58| 27| 34|  3| 40| 29| 10|  5|  8|\n+---+---+---+---+---+---+---+---+---+---+\n| 26| 35|  2| 57| 28| 33|  4|  7| 30| 11|\n+---+---+---+---+---+---+---+---+---+---+\n| 59|100| 73| 36| 41| 56| 39| 32|  9|  6|\n+---+---+---+---+---+---+---+---+---+---+\n| 74| 25| 60| 55| 72| 37| 42| 49| 12| 31|\n+---+---+---+---+---+---+---+---+---+---+\n| 61| 86| 99| 76| 63| 52| 47| 38| 43| 50|\n+---+---+---+---+---+---+---+---+---+---+\n| 24| 75| 62| 85| 54| 71| 64| 51| 48| 13|\n+---+---+---+---+---+---+---+---+---+---+\n| 87| 98| 89| 80| 77| 84| 53| 46| 65| 44|\n+---+---+---+---+---+---+---+---+---+---+\n| 90| 23| 92| 95| 70| 79| 68| 83| 14| 17|\n+---+---+---+---+---+---+---+---+---+---+\n| 97| 88| 21| 78| 81| 94| 19| 16| 45| 66|\n+---+---+---+---+---+---+---+---+---+---+\n| 22| 91| 96| 93| 20| 69| 82| 67| 18| 15|\n+---+---+---+---+---+---+---+---+---+---+\n'
weakref_tests = "Generators are weakly referencable:\n\n>>> import weakref\n>>> def gen():\n...     yield 'foo!'\n...\n>>> wr = weakref.ref(gen)\n>>> wr() is gen\nTrue\n>>> p = weakref.proxy(gen)\n\nGenerator-iterators are weakly referencable as well:\n\n>>> gi = gen()\n>>> wr = weakref.ref(gi)\n>>> wr() is gi\nTrue\n>>> p = weakref.proxy(gi)\n>>> list(p)\n['foo!']\n\n"
coroutine_tests = "Sending a value into a started generator:\n\n>>> def f():\n...     print((yield 1))\n...     yield 2\n>>> g = f()\n>>> next(g)\n1\n>>> g.send(42)\n42\n2\n\nSending a value into a new generator produces a TypeError:\n\n>>> f().send(\"foo\")\nTraceback (most recent call last):\n...\nTypeError: can't send non-None value to a just-started generator\n\n\nYield by itself yields None:\n\n>>> def f(): yield\n>>> list(f())\n[None]\n\n\nYield is allowed only in the outermost iterable in generator expression:\n\n>>> def f(): list(i for i in [(yield 26)])\n>>> type(f())\n<class 'generator'>\n\n\nA yield expression with augmented assignment.\n\n>>> def coroutine(seq):\n...     count = 0\n...     while count < 200:\n...         count += yield\n...         seq.append(count)\n>>> seq = []\n>>> c = coroutine(seq)\n>>> next(c)\n>>> print(seq)\n[]\n>>> c.send(10)\n>>> print(seq)\n[10]\n>>> c.send(10)\n>>> print(seq)\n[10, 20]\n>>> c.send(10)\n>>> print(seq)\n[10, 20, 30]\n\n\nCheck some syntax errors for yield expressions:\n\n>>> f=lambda: (yield 1),(yield 2)\nTraceback (most recent call last):\n  ...\nSyntaxError: 'yield' outside function\n\n# Pegen does not produce this error message yet\n# >>> def f(): x = yield = y\n# Traceback (most recent call last):\n#   ...\n# SyntaxError: assignment to yield expression not possible\n\n>>> def f(): (yield bar) = y\nTraceback (most recent call last):\n  ...\nSyntaxError: cannot assign to yield expression here. Maybe you meant '==' instead of '='?\n\n>>> def f(): (yield bar) += y\nTraceback (most recent call last):\n  ...\nSyntaxError: 'yield expression' is an illegal expression for augmented assignment\n\n\nNow check some throw() conditions:\n\n>>> def f():\n...     while True:\n...         try:\n...             print((yield))\n...         except ValueError as v:\n...             print(\"caught ValueError (%s)\" % (v))\n>>> import sys\n>>> g = f()\n>>> next(g)\n\n>>> g.throw(ValueError) # type only\ncaught ValueError ()\n\n>>> g.throw(ValueError(\"xyz\"))  # value only\ncaught ValueError (xyz)\n\n>>> g.throw(ValueError, ValueError(1))   # value+matching type\ncaught ValueError (1)\n\n>>> g.throw(ValueError, TypeError(1))  # mismatched type, rewrapped\ncaught ValueError (1)\n\n>>> g.throw(ValueError, ValueError(1), None)   # explicit None traceback\ncaught ValueError (1)\n\n>>> g.throw(ValueError(1), \"foo\")       # bad args\nTraceback (most recent call last):\n  ...\nTypeError: instance exception may not have a separate value\n\n>>> g.throw(ValueError, \"foo\", 23)      # bad args\nTraceback (most recent call last):\n  ...\nTypeError: throw() third argument must be a traceback object\n\n>>> g.throw(\"abc\")\nTraceback (most recent call last):\n  ...\nTypeError: exceptions must be classes or instances deriving from BaseException, not str\n\n>>> g.throw(0)\nTraceback (most recent call last):\n  ...\nTypeError: exceptions must be classes or instances deriving from BaseException, not int\n\n>>> g.throw(list)\nTraceback (most recent call last):\n  ...\nTypeError: exceptions must be classes or instances deriving from BaseException, not type\n\n>>> def throw(g,exc):\n...     try:\n...         raise exc\n...     except:\n...         g.throw(*sys.exc_info())\n>>> throw(g,ValueError) # do it with traceback included\ncaught ValueError ()\n\n>>> g.send(1)\n1\n\n>>> throw(g,TypeError)  # terminate the generator\nTraceback (most recent call last):\n  ...\nTypeError\n\n>>> print(g.gi_frame)\nNone\n\n>>> g.send(2)\nTraceback (most recent call last):\n  ...\nStopIteration\n\n>>> g.throw(ValueError,6)       # throw on closed generator\nTraceback (most recent call last):\n  ...\nValueError: 6\n\n>>> f().throw(ValueError,7)     # throw on just-opened generator\nTraceback (most recent call last):\n  ...\nValueError: 7\n\nPlain \"raise\" inside a generator should preserve the traceback (#13188).\nThe traceback should have 3 levels:\n- g.throw()\n- f()\n- 1/0\n\n>>> def f():\n...     try:\n...         yield\n...     except:\n...         raise\n>>> g = f()\n>>> try:\n...     1/0\n... except ZeroDivisionError as v:\n...     try:\n...         g.throw(v)\n...     except Exception as w:\n...         tb = w.__traceback__\n>>> levels = 0\n>>> while tb:\n...     levels += 1\n...     tb = tb.tb_next\n>>> levels\n3\n\nNow let's try closing a generator:\n\n>>> def f():\n...     try: yield\n...     except GeneratorExit:\n...         print(\"exiting\")\n\n>>> g = f()\n>>> next(g)\n>>> g.close()\nexiting\n>>> g.close()  # should be no-op now\n\n>>> f().close()  # close on just-opened generator should be fine\n\n>>> def f(): yield      # an even simpler generator\n>>> f().close()         # close before opening\n>>> g = f()\n>>> next(g)\n>>> g.close()           # close normally\n\nAnd finalization:\n\n>>> def f():\n...     try: yield\n...     finally:\n...         print(\"exiting\")\n\n>>> g = f()\n>>> next(g)\n>>> del g\nexiting\n\n\nGeneratorExit is not caught by except Exception:\n\n>>> def f():\n...     try: yield\n...     except Exception:\n...         print('except')\n...     finally:\n...         print('finally')\n\n>>> g = f()\n>>> next(g)\n>>> del g\nfinally\n\n\nNow let's try some ill-behaved generators:\n\n>>> def f():\n...     try: yield\n...     except GeneratorExit:\n...         yield \"foo!\"\n>>> g = f()\n>>> next(g)\n>>> g.close()\nTraceback (most recent call last):\n  ...\nRuntimeError: generator ignored GeneratorExit\n>>> g.close()\n\n\nOur ill-behaved code should be invoked during GC:\n\n>>> with support.catch_unraisable_exception() as cm:\n...     g = f()\n...     next(g)\n...     del g\n...\n...     cm.unraisable.exc_type == RuntimeError\n...     \"generator ignored GeneratorExit\" in str(cm.unraisable.exc_value)\n...     cm.unraisable.exc_traceback is not None\nTrue\nTrue\nTrue\n\nAnd errors thrown during closing should propagate:\n\n>>> def f():\n...     try: yield\n...     except GeneratorExit:\n...         raise TypeError(\"fie!\")\n>>> g = f()\n>>> next(g)\n>>> g.close()\nTraceback (most recent call last):\n  ...\nTypeError: fie!\n\n\nEnsure that various yield expression constructs make their\nenclosing function a generator:\n\n>>> def f(): x += yield\n>>> type(f())\n<class 'generator'>\n\n>>> def f(): x = yield\n>>> type(f())\n<class 'generator'>\n\n>>> def f(): lambda x=(yield): 1\n>>> type(f())\n<class 'generator'>\n\n>>> def f(d): d[(yield \"a\")] = d[(yield \"b\")] = 27\n>>> data = [1,2]\n>>> g = f(data)\n>>> type(g)\n<class 'generator'>\n>>> g.send(None)\n'a'\n>>> data\n[1, 2]\n>>> g.send(0)\n'b'\n>>> data\n[27, 2]\n>>> try: g.send(1)\n... except StopIteration: pass\n>>> data\n[27, 27]\n\n"
refleaks_tests = '\nPrior to adding cycle-GC support to itertools.tee, this code would leak\nreferences. We add it to the standard suite so the routine refleak-tests\nwould trigger if it starts being uncleanable again.\n\n>>> import itertools\n>>> def leak():\n...     class gen:\n...         def __iter__(self):\n...             return self\n...         def __next__(self):\n...             return self.item\n...     g = gen()\n...     head, tail = itertools.tee(g)\n...     g.item = head\n...     return head\n>>> it = leak()\n\nMake sure to also test the involvement of the tee-internal teedataobject,\nwhich stores returned items.\n\n>>> item = next(it)\n\n\n\nThis test leaked at one point due to generator finalization/destruction.\nIt was copied from Lib/test/leakers/test_generator_cycle.py before the file\nwas removed.\n\n>>> def leak():\n...    def gen():\n...        while True:\n...            yield g\n...    g = gen()\n\n>>> leak()\n\n\n\nThis test isn\'t really generator related, but rather exception-in-cleanup\nrelated. The coroutine tests (above) just happen to cause an exception in\nthe generator\'s __del__ (tp_del) method. We can also test for this\nexplicitly, without generators. We do have to redirect stderr to avoid\nprinting warnings and to doublecheck that we actually tested what we wanted\nto test.\n\n>>> from test import support\n>>> class Leaker:\n...     def __del__(self):\n...         def invoke(message):\n...             raise RuntimeError(message)\n...         invoke("del failed")\n...\n>>> with support.catch_unraisable_exception() as cm:\n...     l = Leaker()\n...     del l\n...\n...     cm.unraisable.object == Leaker.__del__\n...     cm.unraisable.exc_type == RuntimeError\n...     str(cm.unraisable.exc_value) == "del failed"\n...     cm.unraisable.exc_traceback is not None\nTrue\nTrue\nTrue\nTrue\n\n\nThese refleak tests should perhaps be in a testfile of their own,\ntest_generators just happened to be the test that drew these out.\n\n'
__test__ = {
    "tut": tutorial_tests,
    "pep": pep_tests,
    "email": email_tests,
    "fun": fun_tests,
    "syntax": syntax_tests,
    "conjoin": conjoin_tests,
    "weakref": weakref_tests,
    "coroutine": coroutine_tests,
    "refleaks": refleaks_tests,
}


def test_main(verbose=None):
    from test import support, test_generators

    support.run_unittest(__name__)
    support.run_doctest(test_generators, verbose)


if __name__ == "__main__":
    test_main(1)
