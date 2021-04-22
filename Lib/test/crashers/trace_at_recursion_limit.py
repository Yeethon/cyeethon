"\nFrom http://bugs.python.org/issue6717\n\nA misbehaving trace hook can trigger a segfault by exceeding the recursion\nlimit.\n"
import sys


def x():
    pass


def g(*args):
    if True:
        try:
            x()
        except:
            pass
    return g


def f():
    print(sys.getrecursionlimit())
    f()


sys.settrace(g)
f()
