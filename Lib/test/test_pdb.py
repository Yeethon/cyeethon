import doctest
import os
import pdb
import sys
import types
import codecs
import unittest
import subprocess
import textwrap
from contextlib import ExitStack
from io import StringIO
from test.support import os_helper
from test.test_doctest import _FakeInput
from unittest.mock import patch


class PdbTestInput(object):
    "Context manager that makes testing Pdb in doctests easier."

    def __init__(self, input):
        self.input = input

    def __enter__(self):
        self.real_stdin = sys.stdin
        sys.stdin = _FakeInput(self.input)
        self.orig_trace = sys.gettrace() if hasattr(sys, "gettrace") else None

    def __exit__(self, *exc):
        sys.stdin = self.real_stdin
        if self.orig_trace:
            sys.settrace(self.orig_trace)


def test_pdb_displayhook():
    "This tests the custom displayhook for pdb.\n\n    >>> def test_function(foo, bar):\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     pass\n\n    >>> with PdbTestInput([\n    ...     'foo',\n    ...     'bar',\n    ...     'for i in range(5): print(i)',\n    ...     'continue',\n    ... ]):\n    ...     test_function(1, None)\n    > <doctest test.test_pdb.test_pdb_displayhook[0]>(3)test_function()\n    -> pass\n    (Pdb) foo\n    1\n    (Pdb) bar\n    (Pdb) for i in range(5): print(i)\n    0\n    1\n    2\n    3\n    4\n    (Pdb) continue\n    "


def test_pdb_basic_commands():
    "Test the basic commands of pdb.\n\n    >>> def test_function_2(foo, bar='default'):\n    ...     print(foo)\n    ...     for i in range(5):\n    ...         print(i)\n    ...     print(bar)\n    ...     for i in range(10):\n    ...         never_executed\n    ...     print('after for')\n    ...     print('...')\n    ...     return foo.upper()\n\n    >>> def test_function3(arg=None, *, kwonly=None):\n    ...     pass\n\n    >>> def test_function4(a, b, c, /):\n    ...     pass\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     ret = test_function_2('baz')\n    ...     test_function3(kwonly=True)\n    ...     test_function4(1, 2, 3)\n    ...     print(ret)\n\n    >>> with PdbTestInput([  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE\n    ...     'step',       # entering the function call\n    ...     'args',       # display function args\n    ...     'list',       # list function source\n    ...     'bt',         # display backtrace\n    ...     'up',         # step up to test_function()\n    ...     'down',       # step down to test_function_2() again\n    ...     'next',       # stepping to print(foo)\n    ...     'next',       # stepping to the for loop\n    ...     'step',       # stepping into the for loop\n    ...     'until',      # continuing until out of the for loop\n    ...     'next',       # executing the print(bar)\n    ...     'jump 8',     # jump over second for loop\n    ...     'return',     # return out of function\n    ...     'retval',     # display return value\n    ...     'next',       # step to test_function3()\n    ...     'step',       # stepping into test_function3()\n    ...     'args',       # display function args\n    ...     'return',     # return out of function\n    ...     'next',       # step to test_function4()\n    ...     'step',       # stepping to test_function4()\n    ...     'args',       # display function args\n    ...     'continue',\n    ... ]):\n    ...    test_function()\n    > <doctest test.test_pdb.test_pdb_basic_commands[3]>(3)test_function()\n    -> ret = test_function_2('baz')\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(1)test_function_2()\n    -> def test_function_2(foo, bar='default'):\n    (Pdb) args\n    foo = 'baz'\n    bar = 'default'\n    (Pdb) list\n      1  ->     def test_function_2(foo, bar='default'):\n      2             print(foo)\n      3             for i in range(5):\n      4                 print(i)\n      5             print(bar)\n      6             for i in range(10):\n      7                 never_executed\n      8             print('after for')\n      9             print('...')\n     10             return foo.upper()\n    [EOF]\n    (Pdb) bt\n    ...\n      <doctest test.test_pdb.test_pdb_basic_commands[4]>(25)<module>()\n    -> test_function()\n      <doctest test.test_pdb.test_pdb_basic_commands[3]>(3)test_function()\n    -> ret = test_function_2('baz')\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(1)test_function_2()\n    -> def test_function_2(foo, bar='default'):\n    (Pdb) up\n    > <doctest test.test_pdb.test_pdb_basic_commands[3]>(3)test_function()\n    -> ret = test_function_2('baz')\n    (Pdb) down\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(1)test_function_2()\n    -> def test_function_2(foo, bar='default'):\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(2)test_function_2()\n    -> print(foo)\n    (Pdb) next\n    baz\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(3)test_function_2()\n    -> for i in range(5):\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(4)test_function_2()\n    -> print(i)\n    (Pdb) until\n    0\n    1\n    2\n    3\n    4\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(5)test_function_2()\n    -> print(bar)\n    (Pdb) next\n    default\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(6)test_function_2()\n    -> for i in range(10):\n    (Pdb) jump 8\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(8)test_function_2()\n    -> print('after for')\n    (Pdb) return\n    after for\n    ...\n    --Return--\n    > <doctest test.test_pdb.test_pdb_basic_commands[0]>(10)test_function_2()->'BAZ'\n    -> return foo.upper()\n    (Pdb) retval\n    'BAZ'\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_basic_commands[3]>(4)test_function()\n    -> test_function3(kwonly=True)\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_basic_commands[1]>(1)test_function3()\n    -> def test_function3(arg=None, *, kwonly=None):\n    (Pdb) args\n    arg = None\n    kwonly = True\n    (Pdb) return\n    --Return--\n    > <doctest test.test_pdb.test_pdb_basic_commands[1]>(2)test_function3()->None\n    -> pass\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_basic_commands[3]>(5)test_function()\n    -> test_function4(1, 2, 3)\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_basic_commands[2]>(1)test_function4()\n    -> def test_function4(a, b, c, /):\n    (Pdb) args\n    a = 1\n    b = 2\n    c = 3\n    (Pdb) continue\n    BAZ\n    "


def reset_Breakpoint():
    import bdb

    bdb.Breakpoint.clearBreakpoints()


def test_pdb_breakpoint_commands():
    "Test basic commands related to breakpoints.\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     print(1)\n    ...     print(2)\n    ...     print(3)\n    ...     print(4)\n\n    First, need to clear bdb state that might be left over from previous tests.\n    Otherwise, the new breakpoints might get assigned different numbers.\n\n    >>> reset_Breakpoint()\n\n    Now test the breakpoint commands.  NORMALIZE_WHITESPACE is needed because\n    the breakpoint list outputs a tab for the \"stop only\" and \"ignore next\"\n    lines, which we don't want to put in here.\n\n    >>> with PdbTestInput([  # doctest: +NORMALIZE_WHITESPACE\n    ...     'break 3',\n    ...     'disable 1',\n    ...     'ignore 1 10',\n    ...     'condition 1 1 < 2',\n    ...     'break 4',\n    ...     'break 4',\n    ...     'break',\n    ...     'clear 3',\n    ...     'break',\n    ...     'condition 1',\n    ...     'enable 1',\n    ...     'clear 1',\n    ...     'commands 2',\n    ...     'p \"42\"',\n    ...     'print(\"42\", 7*6)',     # Issue 18764 (not about breakpoints)\n    ...     'end',\n    ...     'continue',  # will stop at breakpoint 2 (line 4)\n    ...     'clear',     # clear all!\n    ...     'y',\n    ...     'tbreak 5',\n    ...     'continue',  # will stop at temporary breakpoint\n    ...     'break',     # make sure breakpoint is gone\n    ...     'continue',\n    ... ]):\n    ...    test_function()\n    > <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>(3)test_function()\n    -> print(1)\n    (Pdb) break 3\n    Breakpoint 1 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:3\n    (Pdb) disable 1\n    Disabled breakpoint 1 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:3\n    (Pdb) ignore 1 10\n    Will ignore next 10 crossings of breakpoint 1.\n    (Pdb) condition 1 1 < 2\n    New condition set for breakpoint 1.\n    (Pdb) break 4\n    Breakpoint 2 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:4\n    (Pdb) break 4\n    Breakpoint 3 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:4\n    (Pdb) break\n    Num Type         Disp Enb   Where\n    1   breakpoint   keep no    at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:3\n            stop only if 1 < 2\n            ignore next 10 hits\n    2   breakpoint   keep yes   at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:4\n    3   breakpoint   keep yes   at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:4\n    (Pdb) clear 3\n    Deleted breakpoint 3 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:4\n    (Pdb) break\n    Num Type         Disp Enb   Where\n    1   breakpoint   keep no    at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:3\n            stop only if 1 < 2\n            ignore next 10 hits\n    2   breakpoint   keep yes   at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:4\n    (Pdb) condition 1\n    Breakpoint 1 is now unconditional.\n    (Pdb) enable 1\n    Enabled breakpoint 1 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:3\n    (Pdb) clear 1\n    Deleted breakpoint 1 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:3\n    (Pdb) commands 2\n    (com) p \"42\"\n    (com) print(\"42\", 7*6)\n    (com) end\n    (Pdb) continue\n    1\n    '42'\n    42 42\n    > <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>(4)test_function()\n    -> print(2)\n    (Pdb) clear\n    Clear all breaks? y\n    Deleted breakpoint 2 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:4\n    (Pdb) tbreak 5\n    Breakpoint 4 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:5\n    (Pdb) continue\n    2\n    Deleted breakpoint 4 at <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>:5\n    > <doctest test.test_pdb.test_pdb_breakpoint_commands[0]>(5)test_function()\n    -> print(3)\n    (Pdb) break\n    (Pdb) continue\n    3\n    4\n    "


def test_pdb_breakpoints_preserved_across_interactive_sessions():
    "Breakpoints are remembered between interactive sessions\n\n    >>> reset_Breakpoint()\n    >>> with PdbTestInput([  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE\n    ...    'import test.test_pdb',\n    ...    'break test.test_pdb.do_something',\n    ...    'break test.test_pdb.do_nothing',\n    ...    'break',\n    ...    'continue',\n    ... ]):\n    ...    pdb.run('print()')\n    > <string>(1)<module>()...\n    (Pdb) import test.test_pdb\n    (Pdb) break test.test_pdb.do_something\n    Breakpoint 1 at ...test_pdb.py:...\n    (Pdb) break test.test_pdb.do_nothing\n    Breakpoint 2 at ...test_pdb.py:...\n    (Pdb) break\n    Num Type         Disp Enb   Where\n    1   breakpoint   keep yes   at ...test_pdb.py:...\n    2   breakpoint   keep yes   at ...test_pdb.py:...\n    (Pdb) continue\n\n    >>> with PdbTestInput([  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE\n    ...    'break',\n    ...    'break pdb.find_function',\n    ...    'break',\n    ...    'clear 1',\n    ...    'continue',\n    ... ]):\n    ...    pdb.run('print()')\n    > <string>(1)<module>()...\n    (Pdb) break\n    Num Type         Disp Enb   Where\n    1   breakpoint   keep yes   at ...test_pdb.py:...\n    2   breakpoint   keep yes   at ...test_pdb.py:...\n    (Pdb) break pdb.find_function\n    Breakpoint 3 at ...pdb.py:94\n    (Pdb) break\n    Num Type         Disp Enb   Where\n    1   breakpoint   keep yes   at ...test_pdb.py:...\n    2   breakpoint   keep yes   at ...test_pdb.py:...\n    3   breakpoint   keep yes   at ...pdb.py:...\n    (Pdb) clear 1\n    Deleted breakpoint 1 at ...test_pdb.py:...\n    (Pdb) continue\n\n    >>> with PdbTestInput([  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE\n    ...    'break',\n    ...    'clear 2',\n    ...    'clear 3',\n    ...    'continue',\n    ... ]):\n    ...    pdb.run('print()')\n    > <string>(1)<module>()...\n    (Pdb) break\n    Num Type         Disp Enb   Where\n    2   breakpoint   keep yes   at ...test_pdb.py:...\n    3   breakpoint   keep yes   at ...pdb.py:...\n    (Pdb) clear 2\n    Deleted breakpoint 2 at ...test_pdb.py:...\n    (Pdb) clear 3\n    Deleted breakpoint 3 at ...pdb.py:...\n    (Pdb) continue\n    "


def do_nothing():
    pass


def do_something():
    print(42)


def test_list_commands():
    "Test the list and source commands of pdb.\n\n    >>> def test_function_2(foo):\n    ...     import test.test_pdb\n    ...     test.test_pdb.do_nothing()\n    ...     'some...'\n    ...     'more...'\n    ...     'code...'\n    ...     'to...'\n    ...     'make...'\n    ...     'a...'\n    ...     'long...'\n    ...     'listing...'\n    ...     'useful...'\n    ...     '...'\n    ...     '...'\n    ...     return foo\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     ret = test_function_2('baz')\n\n    >>> with PdbTestInput([  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE\n    ...     'list',      # list first function\n    ...     'step',      # step into second function\n    ...     'list',      # list second function\n    ...     'list',      # continue listing to EOF\n    ...     'list 1,3',  # list specific lines\n    ...     'list x',    # invalid argument\n    ...     'next',      # step to import\n    ...     'next',      # step over import\n    ...     'step',      # step into do_nothing\n    ...     'longlist',  # list all lines\n    ...     'source do_something',  # list all lines of function\n    ...     'source fooxxx',        # something that doesn't exit\n    ...     'continue',\n    ... ]):\n    ...    test_function()\n    > <doctest test.test_pdb.test_list_commands[1]>(3)test_function()\n    -> ret = test_function_2('baz')\n    (Pdb) list\n      1         def test_function():\n      2             import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n      3  ->         ret = test_function_2('baz')\n    [EOF]\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_list_commands[0]>(1)test_function_2()\n    -> def test_function_2(foo):\n    (Pdb) list\n      1  ->     def test_function_2(foo):\n      2             import test.test_pdb\n      3             test.test_pdb.do_nothing()\n      4             'some...'\n      5             'more...'\n      6             'code...'\n      7             'to...'\n      8             'make...'\n      9             'a...'\n     10             'long...'\n     11             'listing...'\n    (Pdb) list\n     12             'useful...'\n     13             '...'\n     14             '...'\n     15             return foo\n    [EOF]\n    (Pdb) list 1,3\n      1  ->     def test_function_2(foo):\n      2             import test.test_pdb\n      3             test.test_pdb.do_nothing()\n    (Pdb) list x\n    *** ...\n    (Pdb) next\n    > <doctest test.test_pdb.test_list_commands[0]>(2)test_function_2()\n    -> import test.test_pdb\n    (Pdb) next\n    > <doctest test.test_pdb.test_list_commands[0]>(3)test_function_2()\n    -> test.test_pdb.do_nothing()\n    (Pdb) step\n    --Call--\n    > ...test_pdb.py(...)do_nothing()\n    -> def do_nothing():\n    (Pdb) longlist\n    ...  ->     def do_nothing():\n    ...             pass\n    (Pdb) source do_something\n    ...         def do_something():\n    ...             print(42)\n    (Pdb) source fooxxx\n    *** ...\n    (Pdb) continue\n    "


def test_pdb_whatis_command():
    "Test the whatis command\n\n    >>> myvar = (1,2)\n    >>> def myfunc():\n    ...     pass\n\n    >>> class MyClass:\n    ...    def mymethod(self):\n    ...        pass\n\n    >>> def test_function():\n    ...   import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n\n    >>> with PdbTestInput([  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE\n    ...    'whatis myvar',\n    ...    'whatis myfunc',\n    ...    'whatis MyClass',\n    ...    'whatis MyClass()',\n    ...    'whatis MyClass.mymethod',\n    ...    'whatis MyClass().mymethod',\n    ...    'continue',\n    ... ]):\n    ...    test_function()\n    --Return--\n    > <doctest test.test_pdb.test_pdb_whatis_command[3]>(2)test_function()->None\n    -> import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    (Pdb) whatis myvar\n    <class 'tuple'>\n    (Pdb) whatis myfunc\n    Function myfunc\n    (Pdb) whatis MyClass\n    Class test.test_pdb.MyClass\n    (Pdb) whatis MyClass()\n    <class 'test.test_pdb.MyClass'>\n    (Pdb) whatis MyClass.mymethod\n    Function mymethod\n    (Pdb) whatis MyClass().mymethod\n    Method mymethod\n    (Pdb) continue\n    "


def test_post_mortem():
    "Test post mortem traceback debugging.\n\n    >>> def test_function_2():\n    ...     try:\n    ...         1/0\n    ...     finally:\n    ...         print('Exception!')\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     test_function_2()\n    ...     print('Not reached.')\n\n    >>> with PdbTestInput([  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE\n    ...     'next',      # step over exception-raising call\n    ...     'bt',        # get a backtrace\n    ...     'list',      # list code of test_function()\n    ...     'down',      # step into test_function_2()\n    ...     'list',      # list code of test_function_2()\n    ...     'continue',\n    ... ]):\n    ...    try:\n    ...        test_function()\n    ...    except ZeroDivisionError:\n    ...        print('Correctly reraised.')\n    > <doctest test.test_pdb.test_post_mortem[1]>(3)test_function()\n    -> test_function_2()\n    (Pdb) next\n    Exception!\n    ZeroDivisionError: division by zero\n    > <doctest test.test_pdb.test_post_mortem[1]>(3)test_function()\n    -> test_function_2()\n    (Pdb) bt\n    ...\n      <doctest test.test_pdb.test_post_mortem[2]>(10)<module>()\n    -> test_function()\n    > <doctest test.test_pdb.test_post_mortem[1]>(3)test_function()\n    -> test_function_2()\n      <doctest test.test_pdb.test_post_mortem[0]>(3)test_function_2()\n    -> 1/0\n    (Pdb) list\n      1         def test_function():\n      2             import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n      3  ->         test_function_2()\n      4             print('Not reached.')\n    [EOF]\n    (Pdb) down\n    > <doctest test.test_pdb.test_post_mortem[0]>(3)test_function_2()\n    -> 1/0\n    (Pdb) list\n      1         def test_function_2():\n      2             try:\n      3  >>             1/0\n      4             finally:\n      5  ->             print('Exception!')\n    [EOF]\n    (Pdb) continue\n    Correctly reraised.\n    "


def test_pdb_skip_modules():
    "This illustrates the simple case of module skipping.\n\n    >>> def skip_module():\n    ...     import string\n    ...     import pdb; pdb.Pdb(skip=['stri*'], nosigint=True, readrc=False).set_trace()\n    ...     string.capwords('FOO')\n\n    >>> with PdbTestInput([\n    ...     'step',\n    ...     'continue',\n    ... ]):\n    ...     skip_module()\n    > <doctest test.test_pdb.test_pdb_skip_modules[0]>(4)skip_module()\n    -> string.capwords('FOO')\n    (Pdb) step\n    --Return--\n    > <doctest test.test_pdb.test_pdb_skip_modules[0]>(4)skip_module()->None\n    -> string.capwords('FOO')\n    (Pdb) continue\n    "


mod = types.ModuleType("module_to_skip")
exec("def foo_pony(callback): x = 1; callback(); return None", mod.__dict__)


def test_pdb_skip_modules_with_callback():
    "This illustrates skipping of modules that call into other code.\n\n    >>> def skip_module():\n    ...     def callback():\n    ...         return None\n    ...     import pdb; pdb.Pdb(skip=['module_to_skip*'], nosigint=True, readrc=False).set_trace()\n    ...     mod.foo_pony(callback)\n\n    >>> with PdbTestInput([\n    ...     'step',\n    ...     'step',\n    ...     'step',\n    ...     'step',\n    ...     'step',\n    ...     'continue',\n    ... ]):\n    ...     skip_module()\n    ...     pass  # provides something to \"step\" to\n    > <doctest test.test_pdb.test_pdb_skip_modules_with_callback[0]>(5)skip_module()\n    -> mod.foo_pony(callback)\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_skip_modules_with_callback[0]>(2)callback()\n    -> def callback():\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_skip_modules_with_callback[0]>(3)callback()\n    -> return None\n    (Pdb) step\n    --Return--\n    > <doctest test.test_pdb.test_pdb_skip_modules_with_callback[0]>(3)callback()->None\n    -> return None\n    (Pdb) step\n    --Return--\n    > <doctest test.test_pdb.test_pdb_skip_modules_with_callback[0]>(5)skip_module()->None\n    -> mod.foo_pony(callback)\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_skip_modules_with_callback[1]>(10)<module>()\n    -> pass  # provides something to \"step\" to\n    (Pdb) continue\n    "


def test_pdb_continue_in_bottomframe():
    "Test that \"continue\" and \"next\" work properly in bottom frame (issue #5294).\n\n    >>> def test_function():\n    ...     import pdb, sys; inst = pdb.Pdb(nosigint=True, readrc=False)\n    ...     inst.set_trace()\n    ...     inst.botframe = sys._getframe()  # hackery to get the right botframe\n    ...     print(1)\n    ...     print(2)\n    ...     print(3)\n    ...     print(4)\n\n    >>> with PdbTestInput([  # doctest: +ELLIPSIS\n    ...     'next',\n    ...     'break 7',\n    ...     'continue',\n    ...     'next',\n    ...     'continue',\n    ...     'continue',\n    ... ]):\n    ...    test_function()\n    > <doctest test.test_pdb.test_pdb_continue_in_bottomframe[0]>(4)test_function()\n    -> inst.botframe = sys._getframe()  # hackery to get the right botframe\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_continue_in_bottomframe[0]>(5)test_function()\n    -> print(1)\n    (Pdb) break 7\n    Breakpoint ... at <doctest test.test_pdb.test_pdb_continue_in_bottomframe[0]>:7\n    (Pdb) continue\n    1\n    2\n    > <doctest test.test_pdb.test_pdb_continue_in_bottomframe[0]>(7)test_function()\n    -> print(3)\n    (Pdb) next\n    3\n    > <doctest test.test_pdb.test_pdb_continue_in_bottomframe[0]>(8)test_function()\n    -> print(4)\n    (Pdb) continue\n    4\n    "


def pdb_invoke(method, arg):
    "Run pdb.method(arg)."
    getattr(pdb.Pdb(nosigint=True, readrc=False), method)(arg)


def test_pdb_run_with_incorrect_argument():
    "Testing run and runeval with incorrect first argument.\n\n    >>> pti = PdbTestInput(['continue',])\n    >>> with pti:\n    ...     pdb_invoke('run', lambda x: x)\n    Traceback (most recent call last):\n    TypeError: exec() arg 1 must be a string, bytes or code object\n\n    >>> with pti:\n    ...     pdb_invoke('runeval', lambda x: x)\n    Traceback (most recent call last):\n    TypeError: eval() arg 1 must be a string, bytes or code object\n    "


def test_pdb_run_with_code_object():
    "Testing run and runeval with code object as a first argument.\n\n    >>> with PdbTestInput(['step','x', 'continue']):  # doctest: +ELLIPSIS\n    ...     pdb_invoke('run', compile('x=1', '<string>', 'exec'))\n    > <string>(1)<module>()...\n    (Pdb) step\n    --Return--\n    > <string>(1)<module>()->None\n    (Pdb) x\n    1\n    (Pdb) continue\n\n    >>> with PdbTestInput(['x', 'continue']):\n    ...     x=0\n    ...     pdb_invoke('runeval', compile('x+1', '<string>', 'eval'))\n    > <string>(1)<module>()->None\n    (Pdb) x\n    1\n    (Pdb) continue\n    "


def test_next_until_return_at_return_event():
    "Test that pdb stops after a next/until/return issued at a return debug event.\n\n    >>> def test_function_2():\n    ...     x = 1\n    ...     x = 2\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     test_function_2()\n    ...     test_function_2()\n    ...     test_function_2()\n    ...     end = 1\n\n    >>> reset_Breakpoint()\n    >>> with PdbTestInput(['break test_function_2',\n    ...                    'continue',\n    ...                    'return',\n    ...                    'next',\n    ...                    'continue',\n    ...                    'return',\n    ...                    'until',\n    ...                    'continue',\n    ...                    'return',\n    ...                    'return',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[1]>(3)test_function()\n    -> test_function_2()\n    (Pdb) break test_function_2\n    Breakpoint 1 at <doctest test.test_pdb.test_next_until_return_at_return_event[0]>:1\n    (Pdb) continue\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[0]>(2)test_function_2()\n    -> x = 1\n    (Pdb) return\n    --Return--\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[0]>(3)test_function_2()->None\n    -> x = 2\n    (Pdb) next\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[1]>(4)test_function()\n    -> test_function_2()\n    (Pdb) continue\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[0]>(2)test_function_2()\n    -> x = 1\n    (Pdb) return\n    --Return--\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[0]>(3)test_function_2()->None\n    -> x = 2\n    (Pdb) until\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[1]>(5)test_function()\n    -> test_function_2()\n    (Pdb) continue\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[0]>(2)test_function_2()\n    -> x = 1\n    (Pdb) return\n    --Return--\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[0]>(3)test_function_2()->None\n    -> x = 2\n    (Pdb) return\n    > <doctest test.test_pdb.test_next_until_return_at_return_event[1]>(6)test_function()\n    -> end = 1\n    (Pdb) continue\n    "


def test_pdb_next_command_for_generator():
    "Testing skip unwindng stack on yield for generators for \"next\" command\n\n    >>> def test_gen():\n    ...     yield 0\n    ...     return 1\n    ...     yield 2\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     it = test_gen()\n    ...     try:\n    ...         if next(it) != 0:\n    ...             raise AssertionError\n    ...         next(it)\n    ...     except StopIteration as ex:\n    ...         if ex.value != 1:\n    ...             raise AssertionError\n    ...     print(\"finished\")\n\n    >>> with PdbTestInput(['step',\n    ...                    'step',\n    ...                    'step',\n    ...                    'next',\n    ...                    'next',\n    ...                    'step',\n    ...                    'step',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_next_command_for_generator[1]>(3)test_function()\n    -> it = test_gen()\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_next_command_for_generator[1]>(4)test_function()\n    -> try:\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_next_command_for_generator[1]>(5)test_function()\n    -> if next(it) != 0:\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_next_command_for_generator[0]>(1)test_gen()\n    -> def test_gen():\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_next_command_for_generator[0]>(2)test_gen()\n    -> yield 0\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_next_command_for_generator[0]>(3)test_gen()\n    -> return 1\n    (Pdb) step\n    --Return--\n    > <doctest test.test_pdb.test_pdb_next_command_for_generator[0]>(3)test_gen()->1\n    -> return 1\n    (Pdb) step\n    StopIteration: 1\n    > <doctest test.test_pdb.test_pdb_next_command_for_generator[1]>(7)test_function()\n    -> next(it)\n    (Pdb) continue\n    finished\n    "


def test_pdb_next_command_for_coroutine():
    "Testing skip unwindng stack on yield for coroutines for \"next\" command\n\n    >>> import asyncio\n\n    >>> async def test_coro():\n    ...     await asyncio.sleep(0)\n    ...     await asyncio.sleep(0)\n    ...     await asyncio.sleep(0)\n\n    >>> async def test_main():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     await test_coro()\n\n    >>> def test_function():\n    ...     loop = asyncio.new_event_loop()\n    ...     loop.run_until_complete(test_main())\n    ...     loop.close()\n    ...     asyncio.set_event_loop_policy(None)\n    ...     print(\"finished\")\n\n    >>> with PdbTestInput(['step',\n    ...                    'step',\n    ...                    'next',\n    ...                    'next',\n    ...                    'next',\n    ...                    'step',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_next_command_for_coroutine[2]>(3)test_main()\n    -> await test_coro()\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_next_command_for_coroutine[1]>(1)test_coro()\n    -> async def test_coro():\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_next_command_for_coroutine[1]>(2)test_coro()\n    -> await asyncio.sleep(0)\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_next_command_for_coroutine[1]>(3)test_coro()\n    -> await asyncio.sleep(0)\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_next_command_for_coroutine[1]>(4)test_coro()\n    -> await asyncio.sleep(0)\n    (Pdb) next\n    Internal StopIteration\n    > <doctest test.test_pdb.test_pdb_next_command_for_coroutine[2]>(3)test_main()\n    -> await test_coro()\n    (Pdb) step\n    --Return--\n    > <doctest test.test_pdb.test_pdb_next_command_for_coroutine[2]>(3)test_main()->None\n    -> await test_coro()\n    (Pdb) continue\n    finished\n    "


def test_pdb_next_command_for_asyncgen():
    "Testing skip unwindng stack on yield for coroutines for \"next\" command\n\n    >>> import asyncio\n\n    >>> async def agen():\n    ...     yield 1\n    ...     await asyncio.sleep(0)\n    ...     yield 2\n\n    >>> async def test_coro():\n    ...     async for x in agen():\n    ...         print(x)\n\n    >>> async def test_main():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     await test_coro()\n\n    >>> def test_function():\n    ...     loop = asyncio.new_event_loop()\n    ...     loop.run_until_complete(test_main())\n    ...     loop.close()\n    ...     asyncio.set_event_loop_policy(None)\n    ...     print(\"finished\")\n\n    >>> with PdbTestInput(['step',\n    ...                    'step',\n    ...                    'next',\n    ...                    'next',\n    ...                    'step',\n    ...                    'next',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_next_command_for_asyncgen[3]>(3)test_main()\n    -> await test_coro()\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_next_command_for_asyncgen[2]>(1)test_coro()\n    -> async def test_coro():\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_next_command_for_asyncgen[2]>(2)test_coro()\n    -> async for x in agen():\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_next_command_for_asyncgen[2]>(3)test_coro()\n    -> print(x)\n    (Pdb) next\n    1\n    > <doctest test.test_pdb.test_pdb_next_command_for_asyncgen[2]>(2)test_coro()\n    -> async for x in agen():\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_next_command_for_asyncgen[1]>(2)agen()\n    -> yield 1\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_next_command_for_asyncgen[1]>(3)agen()\n    -> await asyncio.sleep(0)\n    (Pdb) continue\n    2\n    finished\n    "


def test_pdb_return_command_for_generator():
    "Testing no unwindng stack on yield for generators\n       for \"return\" command\n\n    >>> def test_gen():\n    ...     yield 0\n    ...     return 1\n    ...     yield 2\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     it = test_gen()\n    ...     try:\n    ...         if next(it) != 0:\n    ...             raise AssertionError\n    ...         next(it)\n    ...     except StopIteration as ex:\n    ...         if ex.value != 1:\n    ...             raise AssertionError\n    ...     print(\"finished\")\n\n    >>> with PdbTestInput(['step',\n    ...                    'step',\n    ...                    'step',\n    ...                    'return',\n    ...                    'step',\n    ...                    'step',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_return_command_for_generator[1]>(3)test_function()\n    -> it = test_gen()\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_return_command_for_generator[1]>(4)test_function()\n    -> try:\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_return_command_for_generator[1]>(5)test_function()\n    -> if next(it) != 0:\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_return_command_for_generator[0]>(1)test_gen()\n    -> def test_gen():\n    (Pdb) return\n    StopIteration: 1\n    > <doctest test.test_pdb.test_pdb_return_command_for_generator[1]>(7)test_function()\n    -> next(it)\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_return_command_for_generator[1]>(8)test_function()\n    -> except StopIteration as ex:\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_return_command_for_generator[1]>(9)test_function()\n    -> if ex.value != 1:\n    (Pdb) continue\n    finished\n    "


def test_pdb_return_command_for_coroutine():
    "Testing no unwindng stack on yield for coroutines for \"return\" command\n\n    >>> import asyncio\n\n    >>> async def test_coro():\n    ...     await asyncio.sleep(0)\n    ...     await asyncio.sleep(0)\n    ...     await asyncio.sleep(0)\n\n    >>> async def test_main():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     await test_coro()\n\n    >>> def test_function():\n    ...     loop = asyncio.new_event_loop()\n    ...     loop.run_until_complete(test_main())\n    ...     loop.close()\n    ...     asyncio.set_event_loop_policy(None)\n    ...     print(\"finished\")\n\n    >>> with PdbTestInput(['step',\n    ...                    'step',\n    ...                    'next',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_return_command_for_coroutine[2]>(3)test_main()\n    -> await test_coro()\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_return_command_for_coroutine[1]>(1)test_coro()\n    -> async def test_coro():\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_return_command_for_coroutine[1]>(2)test_coro()\n    -> await asyncio.sleep(0)\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_return_command_for_coroutine[1]>(3)test_coro()\n    -> await asyncio.sleep(0)\n    (Pdb) continue\n    finished\n    "


def test_pdb_until_command_for_generator():
    "Testing no unwindng stack on yield for generators\n       for \"until\" command if target breakpoint is not reached\n\n    >>> def test_gen():\n    ...     yield 0\n    ...     yield 1\n    ...     yield 2\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     for i in test_gen():\n    ...         print(i)\n    ...     print(\"finished\")\n\n    >>> with PdbTestInput(['step',\n    ...                    'until 4',\n    ...                    'step',\n    ...                    'step',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_until_command_for_generator[1]>(3)test_function()\n    -> for i in test_gen():\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_until_command_for_generator[0]>(1)test_gen()\n    -> def test_gen():\n    (Pdb) until 4\n    0\n    1\n    > <doctest test.test_pdb.test_pdb_until_command_for_generator[0]>(4)test_gen()\n    -> yield 2\n    (Pdb) step\n    --Return--\n    > <doctest test.test_pdb.test_pdb_until_command_for_generator[0]>(4)test_gen()->2\n    -> yield 2\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_until_command_for_generator[1]>(4)test_function()\n    -> print(i)\n    (Pdb) continue\n    2\n    finished\n    "


def test_pdb_until_command_for_coroutine():
    "Testing no unwindng stack for coroutines\n       for \"until\" command if target breakpoint is not reached\n\n    >>> import asyncio\n\n    >>> async def test_coro():\n    ...     print(0)\n    ...     await asyncio.sleep(0)\n    ...     print(1)\n    ...     await asyncio.sleep(0)\n    ...     print(2)\n    ...     await asyncio.sleep(0)\n    ...     print(3)\n\n    >>> async def test_main():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     await test_coro()\n\n    >>> def test_function():\n    ...     loop = asyncio.new_event_loop()\n    ...     loop.run_until_complete(test_main())\n    ...     loop.close()\n    ...     asyncio.set_event_loop_policy(None)\n    ...     print(\"finished\")\n\n    >>> with PdbTestInput(['step',\n    ...                    'until 8',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_until_command_for_coroutine[2]>(3)test_main()\n    -> await test_coro()\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_until_command_for_coroutine[1]>(1)test_coro()\n    -> async def test_coro():\n    (Pdb) until 8\n    0\n    1\n    2\n    > <doctest test.test_pdb.test_pdb_until_command_for_coroutine[1]>(8)test_coro()\n    -> print(3)\n    (Pdb) continue\n    3\n    finished\n    "


def test_pdb_next_command_in_generator_for_loop():
    "The next command on returning from a generator controlled by a for loop.\n\n    >>> def test_gen():\n    ...     yield 0\n    ...     return 1\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     for i in test_gen():\n    ...         print('value', i)\n    ...     x = 123\n\n    >>> with PdbTestInput(['break test_gen',\n    ...                    'continue',\n    ...                    'next',\n    ...                    'next',\n    ...                    'next',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_next_command_in_generator_for_loop[1]>(3)test_function()\n    -> for i in test_gen():\n    (Pdb) break test_gen\n    Breakpoint 1 at <doctest test.test_pdb.test_pdb_next_command_in_generator_for_loop[0]>:1\n    (Pdb) continue\n    > <doctest test.test_pdb.test_pdb_next_command_in_generator_for_loop[0]>(2)test_gen()\n    -> yield 0\n    (Pdb) next\n    value 0\n    > <doctest test.test_pdb.test_pdb_next_command_in_generator_for_loop[0]>(3)test_gen()\n    -> return 1\n    (Pdb) next\n    Internal StopIteration: 1\n    > <doctest test.test_pdb.test_pdb_next_command_in_generator_for_loop[1]>(3)test_function()\n    -> for i in test_gen():\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_next_command_in_generator_for_loop[1]>(5)test_function()\n    -> x = 123\n    (Pdb) continue\n    "


def test_pdb_next_command_subiterator():
    "The next command in a generator with a subiterator.\n\n    >>> def test_subgenerator():\n    ...     yield 0\n    ...     return 1\n\n    >>> def test_gen():\n    ...     x = yield from test_subgenerator()\n    ...     return x\n\n    >>> def test_function():\n    ...     import pdb; pdb.Pdb(nosigint=True, readrc=False).set_trace()\n    ...     for i in test_gen():\n    ...         print('value', i)\n    ...     x = 123\n\n    >>> with PdbTestInput(['step',\n    ...                    'step',\n    ...                    'next',\n    ...                    'next',\n    ...                    'next',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_next_command_subiterator[2]>(3)test_function()\n    -> for i in test_gen():\n    (Pdb) step\n    --Call--\n    > <doctest test.test_pdb.test_pdb_next_command_subiterator[1]>(1)test_gen()\n    -> def test_gen():\n    (Pdb) step\n    > <doctest test.test_pdb.test_pdb_next_command_subiterator[1]>(2)test_gen()\n    -> x = yield from test_subgenerator()\n    (Pdb) next\n    value 0\n    > <doctest test.test_pdb.test_pdb_next_command_subiterator[1]>(3)test_gen()\n    -> return x\n    (Pdb) next\n    Internal StopIteration: 1\n    > <doctest test.test_pdb.test_pdb_next_command_subiterator[2]>(3)test_function()\n    -> for i in test_gen():\n    (Pdb) next\n    > <doctest test.test_pdb.test_pdb_next_command_subiterator[2]>(5)test_function()\n    -> x = 123\n    (Pdb) continue\n    "


def test_pdb_issue_20766():
    "Test for reference leaks when the SIGINT handler is set.\n\n    >>> def test_function():\n    ...     i = 1\n    ...     while i <= 2:\n    ...         sess = pdb.Pdb()\n    ...         sess.set_trace(sys._getframe())\n    ...         print('pdb %d: %s' % (i, sess._previous_sigint_handler))\n    ...         i += 1\n\n    >>> reset_Breakpoint()\n    >>> with PdbTestInput(['continue',\n    ...                    'continue']):\n    ...     test_function()\n    > <doctest test.test_pdb.test_pdb_issue_20766[0]>(6)test_function()\n    -> print('pdb %d: %s' % (i, sess._previous_sigint_handler))\n    (Pdb) continue\n    pdb 1: <built-in function default_int_handler>\n    > <doctest test.test_pdb.test_pdb_issue_20766[0]>(5)test_function()\n    -> sess.set_trace(sys._getframe())\n    (Pdb) continue\n    pdb 2: <built-in function default_int_handler>\n    "


class PdbTestCase(unittest.TestCase):
    def tearDown(self):
        os_helper.unlink(os_helper.TESTFN)

    def _run_pdb(self, pdb_args, commands):
        self.addCleanup(os_helper.rmtree, "__pycache__")
        cmd = [sys.executable, "-m", "pdb"] + pdb_args
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        ) as proc:
            (stdout, stderr) = proc.communicate(str.encode(commands))
        stdout = stdout and bytes.decode(stdout)
        stderr = stderr and bytes.decode(stderr)
        return (stdout, stderr)

    def run_pdb_script(self, script, commands):
        "Run 'script' lines with pdb and the pdb 'commands'."
        filename = "main.py"
        with open(filename, "w") as f:
            f.write(textwrap.dedent(script))
        self.addCleanup(os_helper.unlink, filename)
        return self._run_pdb([filename], commands)

    def run_pdb_module(self, script, commands):
        "Runs the script code as part of a module"
        self.module_name = "t_main"
        os_helper.rmtree(self.module_name)
        main_file = self.module_name + "/__main__.py"
        init_file = self.module_name + "/__init__.py"
        os.mkdir(self.module_name)
        with open(init_file, "w") as f:
            pass
        with open(main_file, "w") as f:
            f.write(textwrap.dedent(script))
        self.addCleanup(os_helper.rmtree, self.module_name)
        return self._run_pdb(["-m", self.module_name], commands)

    def _assert_find_function(self, file_content, func_name, expected):
        with open(os_helper.TESTFN, "wb") as f:
            f.write(file_content)
        expected = (
            None if (not expected) else (expected[0], os_helper.TESTFN, expected[1])
        )
        self.assertEqual(expected, pdb.find_function(func_name, os_helper.TESTFN))

    def test_find_function_empty_file(self):
        self._assert_find_function(b"", "foo", None)

    def test_find_function_found(self):
        self._assert_find_function(
            "def foo():\n    pass\n\ndef bœr():\n    pass\n\ndef quux():\n    pass\n".encode(),
            "bœr",
            ("bœr", 4),
        )

    def test_find_function_found_with_encoding_cookie(self):
        self._assert_find_function(
            "# coding: iso-8859-15\ndef foo():\n    pass\n\ndef bœr():\n    pass\n\ndef quux():\n    pass\n".encode(
                "iso-8859-15"
            ),
            "bœr",
            ("bœr", 5),
        )

    def test_find_function_found_with_bom(self):
        self._assert_find_function(
            (codecs.BOM_UTF8 + "def bœr():\n    pass\n".encode()), "bœr", ("bœr", 1)
        )

    def test_issue7964(self):
        with open(os_helper.TESTFN, "wb") as f:
            f.write(b'print("testing my pdb")\r\n')
        cmd = [sys.executable, "-m", "pdb", os_helper.TESTFN]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        self.addCleanup(proc.stdout.close)
        (stdout, stderr) = proc.communicate(b"quit\n")
        self.assertNotIn(
            b"SyntaxError", stdout, "Got a syntax error running test script under PDB"
        )

    def test_issue13183(self):
        script = "\n            from bar import bar\n\n            def foo():\n                bar()\n\n            def nope():\n                pass\n\n            def foobar():\n                foo()\n                nope()\n\n            foobar()\n        "
        commands = "\n            from bar import bar\n            break bar\n            continue\n            step\n            step\n            quit\n        "
        bar = "\n            def bar():\n                pass\n        "
        with open("bar.py", "w") as f:
            f.write(textwrap.dedent(bar))
        self.addCleanup(os_helper.unlink, "bar.py")
        (stdout, stderr) = self.run_pdb_script(script, commands)
        self.assertTrue(
            any((("main.py(5)foo()->None" in l) for l in stdout.splitlines())),
            "Fail to step into the caller after a return",
        )

    def test_issue13120(self):
        with open(os_helper.TESTFN, "wb") as f:
            f.write(
                textwrap.dedent(
                    "\n                import threading\n                import pdb\n\n                def start_pdb():\n                    pdb.Pdb(readrc=False).set_trace()\n                    x = 1\n                    y = 1\n\n                t = threading.Thread(target=start_pdb)\n                t.start()"
                ).encode("ascii")
            )
        cmd = [sys.executable, "-u", os_helper.TESTFN]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.addCleanup(proc.stdout.close)
        (stdout, stderr) = proc.communicate(b"cont\n")
        self.assertNotIn(b"Error", stdout, "Got an error running test script under PDB")

    def test_issue36250(self):
        with open(os_helper.TESTFN, "wb") as f:
            f.write(
                textwrap.dedent(
                    "\n                import threading\n                import pdb\n\n                evt = threading.Event()\n\n                def start_pdb():\n                    evt.wait()\n                    pdb.Pdb(readrc=False).set_trace()\n\n                t = threading.Thread(target=start_pdb)\n                t.start()\n                pdb.Pdb(readrc=False).set_trace()\n                evt.set()\n                t.join()"
                ).encode("ascii")
            )
        cmd = [sys.executable, "-u", os_helper.TESTFN]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.addCleanup(proc.stdout.close)
        (stdout, stderr) = proc.communicate(b"cont\ncont\n")
        self.assertNotIn(b"Error", stdout, "Got an error running test script under PDB")

    def test_issue16180(self):
        script = "def f: pass\n"
        commands = ""
        expected = "SyntaxError:"
        (stdout, stderr) = self.run_pdb_script(script, commands)
        self.assertIn(
            expected,
            stdout,
            "\n\nExpected:\n{}\nGot:\n{}\nFail to handle a syntax error in the debuggee.".format(
                expected, stdout
            ),
        )

    def test_issue26053(self):
        script = "print('hello')"
        commands = "\n            continue\n            run a b c\n            run d e f\n            quit\n        "
        (stdout, stderr) = self.run_pdb_script(script, commands)
        res = "\n".join([x.strip() for x in stdout.splitlines()])
        self.assertRegex(res, "Restarting .* with arguments:\na b c")
        self.assertRegex(res, "Restarting .* with arguments:\nd e f")

    def test_readrc_kwarg(self):
        script = textwrap.dedent(
            "\n            import pdb; pdb.Pdb(readrc=False).set_trace()\n\n            print('hello')\n        "
        )
        save_home = os.environ.pop("HOME", None)
        try:
            with os_helper.temp_cwd():
                with open(".pdbrc", "w") as f:
                    f.write("invalid\n")
                with open("main.py", "w") as f:
                    f.write(script)
                cmd = [sys.executable, "main.py"]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                with proc:
                    (stdout, stderr) = proc.communicate(b"q\n")
                    self.assertNotIn(
                        b"NameError: name 'invalid' is not defined", stdout
                    )
        finally:
            if save_home is not None:
                os.environ["HOME"] = save_home

    def test_readrc_homedir(self):
        save_home = os.environ.pop("HOME", None)
        with os_helper.temp_dir() as temp_dir, patch("os.path.expanduser"):
            rc_path = os.path.join(temp_dir, ".pdbrc")
            os.path.expanduser.return_value = rc_path
            try:
                with open(rc_path, "w") as f:
                    f.write("invalid")
                self.assertEqual(pdb.Pdb().rcLines[0], "invalid")
            finally:
                if save_home is not None:
                    os.environ["HOME"] = save_home

    def test_header(self):
        stdout = StringIO()
        header = "Nobody expects... blah, blah, blah"
        with ExitStack() as resources:
            resources.enter_context(patch("sys.stdout", stdout))
            resources.enter_context(patch.object(pdb.Pdb, "set_trace"))
            pdb.set_trace(header=header)
        self.assertEqual(stdout.getvalue(), (header + "\n"))

    def test_run_module(self):
        script = 'print("SUCCESS")'
        commands = "\n            continue\n            quit\n        "
        (stdout, stderr) = self.run_pdb_module(script, commands)
        self.assertTrue(any((("SUCCESS" in l) for l in stdout.splitlines())), stdout)

    def test_module_is_run_as_main(self):
        script = "\n            if __name__ == '__main__':\n                print(\"SUCCESS\")\n        "
        commands = "\n            continue\n            quit\n        "
        (stdout, stderr) = self.run_pdb_module(script, commands)
        self.assertTrue(any((("SUCCESS" in l) for l in stdout.splitlines())), stdout)

    def test_breakpoint(self):
        script = "\n            if __name__ == '__main__':\n                pass\n                print(\"SUCCESS\")\n                pass\n        "
        commands = "\n            b 3\n            quit\n        "
        (stdout, stderr) = self.run_pdb_module(script, commands)
        self.assertTrue(
            any((("Breakpoint 1 at" in l) for l in stdout.splitlines())), stdout
        )
        self.assertTrue(
            all((("SUCCESS" not in l) for l in stdout.splitlines())), stdout
        )

    def test_run_pdb_with_pdb(self):
        commands = "\n            c\n            quit\n        "
        (stdout, stderr) = self._run_pdb(["-m", "pdb"], commands)
        self.assertIn(pdb._usage, stdout.replace("\r", ""))

    def test_module_without_a_main(self):
        module_name = "t_main"
        os_helper.rmtree(module_name)
        init_file = module_name + "/__init__.py"
        os.mkdir(module_name)
        with open(init_file, "w") as f:
            pass
        self.addCleanup(os_helper.rmtree, module_name)
        (stdout, stderr) = self._run_pdb(["-m", module_name], "")
        self.assertIn(
            "ImportError: No module named t_main.__main__", stdout.splitlines()
        )

    def test_blocks_at_first_code_line(self):
        script = '\n                #This is a comment, on line 2\n\n                print("SUCCESS")\n        '
        commands = "\n            quit\n        "
        (stdout, stderr) = self.run_pdb_module(script, commands)
        self.assertTrue(
            any((("__main__.py(4)<module>()" in l) for l in stdout.splitlines())),
            stdout,
        )

    def test_relative_imports(self):
        self.module_name = "t_main"
        os_helper.rmtree(self.module_name)
        main_file = self.module_name + "/__main__.py"
        init_file = self.module_name + "/__init__.py"
        module_file = self.module_name + "/module.py"
        self.addCleanup(os_helper.rmtree, self.module_name)
        os.mkdir(self.module_name)
        with open(init_file, "w") as f:
            f.write(
                textwrap.dedent(
                    '\n                top_var = "VAR from top"\n            '
                )
            )
        with open(main_file, "w") as f:
            f.write(
                textwrap.dedent(
                    "\n                from . import top_var\n                from .module import var\n                from . import module\n                pass # We'll stop here and print the vars\n            "
                )
            )
        with open(module_file, "w") as f:
            f.write(
                textwrap.dedent(
                    '\n                var = "VAR from module"\n                var2 = "second var"\n            '
                )
            )
        commands = "\n            b 5\n            c\n            p top_var\n            p var\n            p module.var2\n            quit\n        "
        (stdout, _) = self._run_pdb(["-m", self.module_name], commands)
        self.assertTrue(
            any((("VAR from module" in l) for l in stdout.splitlines())), stdout
        )
        self.assertTrue(any((("VAR from top" in l) for l in stdout.splitlines())))
        self.assertTrue(any((("second var" in l) for l in stdout.splitlines())))

    def test_relative_imports_on_plain_module(self):
        self.module_name = "t_main"
        os_helper.rmtree(self.module_name)
        main_file = self.module_name + "/runme.py"
        init_file = self.module_name + "/__init__.py"
        module_file = self.module_name + "/module.py"
        self.addCleanup(os_helper.rmtree, self.module_name)
        os.mkdir(self.module_name)
        with open(init_file, "w") as f:
            f.write(
                textwrap.dedent(
                    '\n                top_var = "VAR from top"\n            '
                )
            )
        with open(main_file, "w") as f:
            f.write(
                textwrap.dedent(
                    "\n                from . import module\n                pass # We'll stop here and print the vars\n            "
                )
            )
        with open(module_file, "w") as f:
            f.write(
                textwrap.dedent(
                    '\n                var = "VAR from module"\n            '
                )
            )
        commands = "\n            b 3\n            c\n            p module.var\n            quit\n        "
        (stdout, _) = self._run_pdb(["-m", (self.module_name + ".runme")], commands)
        self.assertTrue(
            any((("VAR from module" in l) for l in stdout.splitlines())), stdout
        )

    def test_errors_in_command(self):
        commands = "\n".join(["print(", "debug print(", "debug doesnotexist", "c"])
        (stdout, _) = self.run_pdb_script("pass", (commands + "\n"))
        self.assertEqual(
            stdout.splitlines()[1:],
            [
                "-> pass",
                "(Pdb) *** SyntaxError: '(' was never closed",
                "(Pdb) ENTERING RECURSIVE DEBUGGER",
                "*** SyntaxError: '(' was never closed",
                "LEAVING RECURSIVE DEBUGGER",
                "(Pdb) ENTERING RECURSIVE DEBUGGER",
                "> <string>(1)<module>()",
                "((Pdb)) *** NameError: name 'doesnotexist' is not defined",
                "LEAVING RECURSIVE DEBUGGER",
                "(Pdb) ",
            ],
        )

    def test_issue42384(self):
        "When running `python foo.py` sys.path[0] is an absolute path. `python -m pdb foo.py` should behave the same"
        script = textwrap.dedent(
            "\n            import sys\n            print('sys.path[0] is', sys.path[0])\n        "
        )
        commands = "c\nq"
        with os_helper.temp_cwd() as cwd:
            expected = f"(Pdb) sys.path[0] is {os.path.realpath(cwd)}"
            (stdout, stderr) = self.run_pdb_script(script, commands)
            self.assertEqual(stdout.split("\n")[2].rstrip("\r"), expected)

    @os_helper.skip_unless_symlink
    def test_issue42384_symlink(self):
        "When running `python foo.py` sys.path[0] resolves symlinks. `python -m pdb foo.py` should behave the same"
        script = textwrap.dedent(
            "\n            import sys\n            print('sys.path[0] is', sys.path[0])\n        "
        )
        commands = "c\nq"
        with os_helper.temp_cwd() as cwd:
            cwd = os.path.realpath(cwd)
            dir_one = os.path.join(cwd, "dir_one")
            dir_two = os.path.join(cwd, "dir_two")
            expected = f"(Pdb) sys.path[0] is {dir_one}"
            os.mkdir(dir_one)
            with open(os.path.join(dir_one, "foo.py"), "w") as f:
                f.write(script)
            os.mkdir(dir_two)
            os.symlink(os.path.join(dir_one, "foo.py"), os.path.join(dir_two, "foo.py"))
            (stdout, stderr) = self._run_pdb(
                [os.path.join("dir_two", "foo.py")], commands
            )
            self.assertEqual(stdout.split("\n")[2].rstrip("\r"), expected)

    def test_issue42383(self):
        with os_helper.temp_cwd() as cwd:
            with open("foo.py", "w") as f:
                s = textwrap.dedent(
                    "\n                    print('The correct file was executed')\n\n                    import os\n                    os.chdir(\"subdir\")\n                "
                )
                f.write(s)
            subdir = os.path.join(cwd, "subdir")
            os.mkdir(subdir)
            os.mkdir(os.path.join(subdir, "subdir"))
            wrong_file = os.path.join(subdir, "foo.py")
            with open(wrong_file, "w") as f:
                f.write('print("The wrong file was executed")')
            (stdout, stderr) = self._run_pdb(["foo.py"], "c\nc\nq")
            expected = "(Pdb) The correct file was executed"
            self.assertEqual(stdout.split("\n")[6].rstrip("\r"), expected)


def load_tests(*args):
    from test import test_pdb

    suites = [unittest.makeSuite(PdbTestCase), doctest.DocTestSuite(test_pdb)]
    return unittest.TestSuite(suites)


if __name__ == "__main__":
    unittest.main()
