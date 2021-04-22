" Test the bdb module.\n\n    A test defines a list of tuples that may be seen as paired tuples, each\n    pair being defined by 'expect_tuple, set_tuple' as follows:\n\n        ([event, [lineno[, co_name[, eargs]]]]), (set_type, [sargs])\n\n    * 'expect_tuple' describes the expected current state of the Bdb instance.\n      It may be the empty tuple and no check is done in that case.\n    * 'set_tuple' defines the set_*() method to be invoked when the Bdb\n      instance reaches this state.\n\n    Example of an 'expect_tuple, set_tuple' pair:\n\n        ('line', 2, 'tfunc_main'), ('step', )\n\n    Definitions of the members of the 'expect_tuple':\n        event:\n            Name of the trace event. The set methods that do not give back\n            control to the tracer [1] do not trigger a tracer event and in\n            that case the next 'event' may be 'None' by convention, its value\n            is not checked.\n            [1] Methods that trigger a trace event are set_step(), set_next(),\n            set_return(), set_until() and set_continue().\n        lineno:\n            Line number. Line numbers are relative to the start of the\n            function when tracing a function in the test_bdb module (i.e. this\n            module).\n        co_name:\n            Name of the function being currently traced.\n        eargs:\n            A tuple:\n            * On an 'exception' event the tuple holds a class object, the\n              current exception must be an instance of this class.\n            * On a 'line' event, the tuple holds a dictionary and a list. The\n              dictionary maps each breakpoint number that has been hit on this\n              line to its hits count. The list holds the list of breakpoint\n              number temporaries that are being deleted.\n\n    Definitions of the members of the 'set_tuple':\n        set_type:\n            The type of the set method to be invoked. This may\n            be the type of one of the Bdb set methods: 'step', 'next',\n            'until', 'return', 'continue', 'break', 'quit', or the type of one\n            of the set methods added by test_bdb.Bdb: 'ignore', 'enable',\n            'disable', 'clear', 'up', 'down'.\n        sargs:\n            The arguments of the set method if any, packed in a tuple.\n"
import bdb as _bdb
import sys
import os
import unittest
import textwrap
import importlib
import linecache
from contextlib import contextmanager
from itertools import islice, repeat
import test.support
from test.support import import_helper
from test.support import os_helper


class BdbException(Exception):
    pass


class BdbError(BdbException):
    "Error raised by the Bdb instance."


class BdbSyntaxError(BdbException):
    "Syntax error in the test case."


class BdbNotExpectedError(BdbException):
    "Unexpected result."


dry_run = 0


def reset_Breakpoint():
    _bdb.Breakpoint.clearBreakpoints()


def info_breakpoints():
    bp_list = [bp for bp in _bdb.Breakpoint.bpbynumber if bp]
    if not bp_list:
        return ""
    header_added = False
    for bp in bp_list:
        if not header_added:
            info = "BpNum Temp Enb Hits Ignore Where\n"
            header_added = True
        disp = "yes " if bp.temporary else "no  "
        enab = "yes" if bp.enabled else "no "
        info += "%-5d %s %s %-4d %-6d at %s:%d" % (
            bp.number,
            disp,
            enab,
            bp.hits,
            bp.ignore,
            os.path.basename(bp.file),
            bp.line,
        )
        if bp.cond:
            info += "\n\tstop only if %s" % (bp.cond,)
        info += "\n"
    return info


class Bdb(_bdb.Bdb):
    "Extend Bdb to enhance test coverage."

    def trace_dispatch(self, frame, event, arg):
        self.currentbp = None
        return super().trace_dispatch(frame, event, arg)

    def set_break(self, filename, lineno, temporary=False, cond=None, funcname=None):
        if isinstance(funcname, str):
            if filename == __file__:
                globals_ = globals()
            else:
                module = importlib.import_module(filename[:(-3)])
                globals_ = module.__dict__
            func = eval(funcname, globals_)
            code = func.__code__
            filename = code.co_filename
            lineno = code.co_firstlineno
            funcname = code.co_name
        res = super().set_break(
            filename, lineno, temporary=temporary, cond=cond, funcname=funcname
        )
        if isinstance(res, str):
            raise BdbError(res)
        return res

    def get_stack(self, f, t):
        (self.stack, self.index) = super().get_stack(f, t)
        self.frame = self.stack[self.index][0]
        return (self.stack, self.index)

    def set_ignore(self, bpnum):
        "Increment the ignore count of Breakpoint number 'bpnum'."
        bp = self.get_bpbynumber(bpnum)
        bp.ignore += 1

    def set_enable(self, bpnum):
        bp = self.get_bpbynumber(bpnum)
        bp.enabled = True

    def set_disable(self, bpnum):
        bp = self.get_bpbynumber(bpnum)
        bp.enabled = False

    def set_clear(self, fname, lineno):
        err = self.clear_break(fname, lineno)
        if err:
            raise BdbError(err)

    def set_up(self):
        "Move up in the frame stack."
        if not self.index:
            raise BdbError("Oldest frame")
        self.index -= 1
        self.frame = self.stack[self.index][0]

    def set_down(self):
        "Move down in the frame stack."
        if (self.index + 1) == len(self.stack):
            raise BdbError("Newest frame")
        self.index += 1
        self.frame = self.stack[self.index][0]


class Tracer(Bdb):
    "A tracer for testing the bdb module."

    def __init__(self, expect_set, skip=None, dry_run=False, test_case=None):
        super().__init__(skip=skip)
        self.expect_set = expect_set
        self.dry_run = dry_run
        self.header = (
            ("Dry-run results for %s:" % test_case) if (test_case is not None) else None
        )
        self.init_test()

    def init_test(self):
        self.cur_except = None
        self.expect_set_no = 0
        self.breakpoint_hits = None
        self.expected_list = list(islice(self.expect_set, 0, None, 2))
        self.set_list = list(islice(self.expect_set, 1, None, 2))

    def trace_dispatch(self, frame, event, arg):
        if self.cur_except is not None:
            raise self.cur_except
        if event == "exception":
            try:
                res = super().trace_dispatch(frame, event, arg)
                return res
            except BdbException as e:
                self.cur_except = e
                return self.trace_dispatch
        else:
            return super().trace_dispatch(frame, event, arg)

    def user_call(self, frame, argument_list):
        if not self.stop_here(frame):
            return
        self.process_event("call", frame, argument_list)
        self.next_set_method()

    def user_line(self, frame):
        self.process_event("line", frame)
        if self.dry_run and self.breakpoint_hits:
            info = info_breakpoints().strip("\n")
            for line in info.split("\n"):
                print(("  " + line))
        self.delete_temporaries()
        self.breakpoint_hits = None
        self.next_set_method()

    def user_return(self, frame, return_value):
        self.process_event("return", frame, return_value)
        self.next_set_method()

    def user_exception(self, frame, exc_info):
        self.exc_info = exc_info
        self.process_event("exception", frame)
        self.next_set_method()

    def do_clear(self, arg):
        bp_list = [self.currentbp]
        self.breakpoint_hits = (bp_list, bp_list)

    def delete_temporaries(self):
        if self.breakpoint_hits:
            for n in self.breakpoint_hits[1]:
                self.clear_bpbynumber(n)

    def pop_next(self):
        self.expect_set_no += 1
        try:
            self.expect = self.expected_list.pop(0)
        except IndexError:
            raise BdbNotExpectedError(
                ("expect_set list exhausted, cannot pop item %d" % self.expect_set_no)
            )
        self.set_tuple = self.set_list.pop(0)

    def process_event(self, event, frame, *args):
        tb = None
        if event == "exception":
            tb = self.exc_info[2]
        self.get_stack(frame, tb)
        if (self.currentbp is not None) and (not self.breakpoint_hits):
            bp_list = [self.currentbp]
            self.breakpoint_hits = (bp_list, [])
        self.event = event
        self.pop_next()
        if self.dry_run:
            self.print_state(self.header)
            return
        if self.expect:
            self.check_equal(self.expect[0], event, "Wrong event type")
            self.check_lno_name()
        if event in ("call", "return"):
            self.check_expect_max_size(3)
        elif len(self.expect) > 3:
            if event == "line":
                (bps, temporaries) = self.expect[3]
                bpnums = sorted(bps.keys())
                if not self.breakpoint_hits:
                    self.raise_not_expected(
                        (
                            "No breakpoints hit at expect_set item %d"
                            % self.expect_set_no
                        )
                    )
                self.check_equal(
                    bpnums, self.breakpoint_hits[0], "Breakpoint numbers do not match"
                )
                self.check_equal(
                    [bps[n] for n in bpnums],
                    [self.get_bpbynumber(n).hits for n in self.breakpoint_hits[0]],
                    "Wrong breakpoint hit count",
                )
                self.check_equal(
                    sorted(temporaries),
                    self.breakpoint_hits[1],
                    "Wrong temporary breakpoints",
                )
            elif event == "exception":
                if not isinstance(self.exc_info[1], self.expect[3]):
                    self.raise_not_expected(
                        (
                            "Wrong exception at expect_set item %d, got '%s'"
                            % (self.expect_set_no, self.exc_info)
                        )
                    )

    def check_equal(self, expected, result, msg):
        if expected == result:
            return
        self.raise_not_expected(
            ("%s at expect_set item %d, got '%s'" % (msg, self.expect_set_no, result))
        )

    def check_lno_name(self):
        "Check the line number and function co_name."
        s = len(self.expect)
        if s > 1:
            lineno = self.lno_abs2rel()
            self.check_equal(self.expect[1], lineno, "Wrong line number")
        if s > 2:
            self.check_equal(
                self.expect[2], self.frame.f_code.co_name, "Wrong function name"
            )

    def check_expect_max_size(self, size):
        if len(self.expect) > size:
            raise BdbSyntaxError(
                ("Invalid size of the %s expect tuple: %s" % (self.event, self.expect))
            )

    def lno_abs2rel(self):
        fname = self.canonic(self.frame.f_code.co_filename)
        lineno = self.frame.f_lineno
        return (
            ((lineno - self.frame.f_code.co_firstlineno) + 1)
            if (fname == self.canonic(__file__))
            else lineno
        )

    def lno_rel2abs(self, fname, lineno):
        return (
            ((self.frame.f_code.co_firstlineno + lineno) - 1)
            if (lineno and (self.canonic(fname) == self.canonic(__file__)))
            else lineno
        )

    def get_state(self):
        lineno = self.lno_abs2rel()
        co_name = self.frame.f_code.co_name
        state = "('%s', %d, '%s'" % (self.event, lineno, co_name)
        if self.breakpoint_hits:
            bps = "{"
            for n in self.breakpoint_hits[0]:
                if bps != "{":
                    bps += ", "
                bps += "%s: %s" % (n, self.get_bpbynumber(n).hits)
            bps += "}"
            bps = ((("(" + bps) + ", ") + str(self.breakpoint_hits[1])) + ")"
            state += ", " + bps
        elif self.event == "exception":
            state += ", " + self.exc_info[0].__name__
        state += "), "
        return (state.ljust(32) + str(self.set_tuple)) + ","

    def print_state(self, header=None):
        if (header is not None) and (self.expect_set_no == 1):
            print()
            print(header)
        print(("%d: %s" % (self.expect_set_no, self.get_state())))

    def raise_not_expected(self, msg):
        msg += "\n"
        msg += "  Expected: %s\n" % str(self.expect)
        msg += "  Got:      " + self.get_state()
        raise BdbNotExpectedError(msg)

    def next_set_method(self):
        set_type = self.set_tuple[0]
        args = self.set_tuple[1] if (len(self.set_tuple) == 2) else None
        set_method = getattr(self, ("set_" + set_type))
        if set_type in ("step", "continue", "quit"):
            set_method()
            return
        elif set_type in ("next", "return"):
            set_method(self.frame)
            return
        elif set_type == "until":
            lineno = None
            if args:
                lineno = self.lno_rel2abs(self.frame.f_code.co_filename, args[0])
            set_method(self.frame, lineno)
            return
        if (
            args and (set_type in ("break", "clear", "ignore", "enable", "disable"))
        ) or (set_type in ("up", "down")):
            if set_type in ("break", "clear"):
                (fname, lineno, *remain) = args
                lineno = self.lno_rel2abs(fname, lineno)
                args = [fname, lineno]
                args.extend(remain)
                set_method(*args)
            elif set_type in ("ignore", "enable", "disable"):
                set_method(*args)
            elif set_type in ("up", "down"):
                set_method()
            self.event = None
            self.pop_next()
            if self.dry_run:
                self.print_state()
            else:
                if self.expect:
                    self.check_lno_name()
                self.check_expect_max_size(3)
            self.next_set_method()
        else:
            raise BdbSyntaxError(('"%s" is an invalid set_tuple' % self.set_tuple))


class TracerRun:
    "Provide a context for running a Tracer instance with a test case."

    def __init__(self, test_case, skip=None):
        self.test_case = test_case
        self.dry_run = test_case.dry_run
        self.tracer = Tracer(
            test_case.expect_set,
            skip=skip,
            dry_run=self.dry_run,
            test_case=test_case.id(),
        )
        self._original_tracer = None

    def __enter__(self):
        reset_Breakpoint()
        self._original_tracer = sys.gettrace()
        return self.tracer

    def __exit__(self, type_=None, value=None, traceback=None):
        reset_Breakpoint()
        sys.settrace(self._original_tracer)
        not_empty = ""
        if self.tracer.set_list:
            not_empty += "All paired tuples have not been processed, "
            not_empty += "the last one was number %d" % self.tracer.expect_set_no
        if (type_ is not None) and issubclass(BdbNotExpectedError, type_):
            if isinstance(value, BaseException) and value.args:
                err_msg = value.args[0]
                if not_empty:
                    err_msg += "\n" + not_empty
                if self.dry_run:
                    print(err_msg)
                    return True
                else:
                    self.test_case.fail(err_msg)
            else:
                assert False, "BdbNotExpectedError with empty args"
        if not_empty:
            if self.dry_run:
                print(not_empty)
            else:
                self.test_case.fail(not_empty)


def run_test(modules, set_list, skip=None):
    "Run a test and print the dry-run results.\n\n    'modules':  A dictionary mapping module names to their source code as a\n                string. The dictionary MUST include one module named\n                'test_module' with a main() function.\n    'set_list': A list of set_type tuples to be run on the module.\n\n    For example, running the following script outputs the following results:\n\n    *****************************   SCRIPT   ********************************\n\n    from test.test_bdb import run_test, break_in_func\n\n    code = '''\n        def func():\n            lno = 3\n\n        def main():\n            func()\n            lno = 7\n    '''\n\n    set_list = [\n                break_in_func('func', 'test_module.py'),\n                ('continue', ),\n                ('step', ),\n                ('step', ),\n                ('step', ),\n                ('quit', ),\n            ]\n\n    modules = { 'test_module': code }\n    run_test(modules, set_list)\n\n    ****************************   results   ********************************\n\n    1: ('line', 2, 'tfunc_import'),    ('next',),\n    2: ('line', 3, 'tfunc_import'),    ('step',),\n    3: ('call', 5, 'main'),            ('break', ('test_module.py', None, False, None, 'func')),\n    4: ('None', 5, 'main'),            ('continue',),\n    5: ('line', 3, 'func', ({1: 1}, [])), ('step',),\n      BpNum Temp Enb Hits Ignore Where\n      1     no   yes 1    0      at test_module.py:2\n    6: ('return', 3, 'func'),          ('step',),\n    7: ('line', 7, 'main'),            ('step',),\n    8: ('return', 7, 'main'),          ('quit',),\n\n    *************************************************************************\n\n    "

    def gen(a, b):
        try:
            while 1:
                x = next(a)
                y = next(b)
                (yield x)
                (yield y)
        except StopIteration:
            return

    sl = [("next",), ("step",)]
    sl.extend(set_list)
    test = BaseTestCase()
    test.dry_run = True
    test.id = lambda: None
    test.expect_set = list(gen(repeat(()), iter(sl)))
    with create_modules(modules):
        with TracerRun(test, skip=skip) as tracer:
            tracer.runcall(tfunc_import)


@contextmanager
def create_modules(modules):
    with os_helper.temp_cwd():
        sys.path.append(os.getcwd())
        try:
            for m in modules:
                fname = m + ".py"
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(textwrap.dedent(modules[m]))
                linecache.checkcache(fname)
            importlib.invalidate_caches()
            (yield)
        finally:
            for m in modules:
                import_helper.forget(m)
            sys.path.pop()


def break_in_func(funcname, fname=__file__, temporary=False, cond=None):
    return ("break", (fname, None, temporary, cond, funcname))


TEST_MODULE = "test_module_for_bdb"
TEST_MODULE_FNAME = TEST_MODULE + ".py"


def tfunc_import():
    import test_module_for_bdb

    test_module_for_bdb.main()


def tfunc_main():
    lno = 2
    tfunc_first()
    tfunc_second()
    lno = 5
    lno = 6
    lno = 7


def tfunc_first():
    lno = 2
    lno = 3
    lno = 4


def tfunc_second():
    lno = 2


class BaseTestCase(unittest.TestCase):
    "Base class for all tests."
    dry_run = dry_run

    def fail(self, msg=None):
        raise self.failureException(msg) from None


class StateTestCase(BaseTestCase):
    "Test the step, next, return, until and quit 'set_' methods."

    def test_step(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            ("step",),
            ("line", 3, "tfunc_main"),
            ("step",),
            ("call", 1, "tfunc_first"),
            ("step",),
            ("line", 2, "tfunc_first"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)

    def test_step_next_on_last_statement(self):
        for set_type in ("step", "next"):
            with self.subTest(set_type=set_type):
                self.expect_set = [
                    ("line", 2, "tfunc_main"),
                    ("step",),
                    ("line", 3, "tfunc_main"),
                    ("step",),
                    ("call", 1, "tfunc_first"),
                    ("break", (__file__, 3)),
                    ("None", 1, "tfunc_first"),
                    ("continue",),
                    ("line", 3, "tfunc_first", ({1: 1}, [])),
                    (set_type,),
                    ("line", 4, "tfunc_first"),
                    ("quit",),
                ]
                with TracerRun(self) as tracer:
                    tracer.runcall(tfunc_main)

    def test_next(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            ("step",),
            ("line", 3, "tfunc_main"),
            ("next",),
            ("line", 4, "tfunc_main"),
            ("step",),
            ("call", 1, "tfunc_second"),
            ("step",),
            ("line", 2, "tfunc_second"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)

    def test_next_over_import(self):
        code = "\n            def main():\n                lno = 3\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                ("next",),
                ("line", 3, "tfunc_import"),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_next_on_plain_statement(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            ("step",),
            ("line", 3, "tfunc_main"),
            ("step",),
            ("call", 1, "tfunc_first"),
            ("next",),
            ("line", 2, "tfunc_first"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)

    def test_next_in_caller_frame(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            ("step",),
            ("line", 3, "tfunc_main"),
            ("step",),
            ("call", 1, "tfunc_first"),
            ("up",),
            ("None", 3, "tfunc_main"),
            ("next",),
            ("line", 4, "tfunc_main"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)

    def test_return(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            ("step",),
            ("line", 3, "tfunc_main"),
            ("step",),
            ("call", 1, "tfunc_first"),
            ("step",),
            ("line", 2, "tfunc_first"),
            ("return",),
            ("return", 4, "tfunc_first"),
            ("step",),
            ("line", 4, "tfunc_main"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)

    def test_return_in_caller_frame(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            ("step",),
            ("line", 3, "tfunc_main"),
            ("step",),
            ("call", 1, "tfunc_first"),
            ("up",),
            ("None", 3, "tfunc_main"),
            ("return",),
            ("return", 7, "tfunc_main"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)

    def test_until(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            ("step",),
            ("line", 3, "tfunc_main"),
            ("step",),
            ("call", 1, "tfunc_first"),
            ("step",),
            ("line", 2, "tfunc_first"),
            ("until", (4,)),
            ("line", 4, "tfunc_first"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)

    def test_until_with_too_large_count(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            break_in_func("tfunc_first"),
            ("None", 2, "tfunc_main"),
            ("continue",),
            ("line", 2, "tfunc_first", ({1: 1}, [])),
            ("until", (9999,)),
            ("return", 4, "tfunc_first"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)

    def test_until_in_caller_frame(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            ("step",),
            ("line", 3, "tfunc_main"),
            ("step",),
            ("call", 1, "tfunc_first"),
            ("up",),
            ("None", 3, "tfunc_main"),
            ("until", (6,)),
            ("line", 6, "tfunc_main"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)

    def test_skip(self):
        code = "\n            def main():\n                lno = 3\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                ("step",),
                ("line", 3, "tfunc_import"),
                ("quit",),
            ]
            skip = ("importlib*", "zipimport", "encodings.*", TEST_MODULE)
            with TracerRun(self, skip=skip) as tracer:
                tracer.runcall(tfunc_import)

    def test_skip_with_no_name_module(self):
        bdb = Bdb(skip=["anything*"])
        self.assertIs(bdb.is_skipped_module(None), False)

    def test_down(self):
        self.expect_set = [("line", 2, "tfunc_main"), ("down",)]
        with TracerRun(self) as tracer:
            self.assertRaises(BdbError, tracer.runcall, tfunc_main)

    def test_up(self):
        self.expect_set = [
            ("line", 2, "tfunc_main"),
            ("step",),
            ("line", 3, "tfunc_main"),
            ("step",),
            ("call", 1, "tfunc_first"),
            ("up",),
            ("None", 3, "tfunc_main"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.runcall(tfunc_main)


class BreakpointTestCase(BaseTestCase):
    "Test the breakpoint set method."

    def test_bp_on_non_existent_module(self):
        self.expect_set = [
            ("line", 2, "tfunc_import"),
            ("break", ("/non/existent/module.py", 1)),
        ]
        with TracerRun(self) as tracer:
            self.assertRaises(BdbError, tracer.runcall, tfunc_import)

    def test_bp_after_last_statement(self):
        code = "\n            def main():\n                lno = 3\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                ("break", (TEST_MODULE_FNAME, 4)),
            ]
            with TracerRun(self) as tracer:
                self.assertRaises(BdbError, tracer.runcall, tfunc_import)

    def test_temporary_bp(self):
        code = "\n            def func():\n                lno = 3\n\n            def main():\n                for i in range(2):\n                    func()\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("func", TEST_MODULE_FNAME, True),
                ("None", 2, "tfunc_import"),
                break_in_func("func", TEST_MODULE_FNAME, True),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "func", ({1: 1}, [1])),
                ("continue",),
                ("line", 3, "func", ({2: 1}, [2])),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_disabled_temporary_bp(self):
        code = "\n            def func():\n                lno = 3\n\n            def main():\n                for i in range(3):\n                    func()\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("func", TEST_MODULE_FNAME),
                ("None", 2, "tfunc_import"),
                break_in_func("func", TEST_MODULE_FNAME, True),
                ("None", 2, "tfunc_import"),
                ("disable", (2,)),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "func", ({1: 1}, [])),
                ("enable", (2,)),
                ("None", 3, "func"),
                ("disable", (1,)),
                ("None", 3, "func"),
                ("continue",),
                ("line", 3, "func", ({2: 1}, [2])),
                ("enable", (1,)),
                ("None", 3, "func"),
                ("continue",),
                ("line", 3, "func", ({1: 2}, [])),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_bp_condition(self):
        code = "\n            def func(a):\n                lno = 3\n\n            def main():\n                for i in range(3):\n                    func(i)\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("func", TEST_MODULE_FNAME, False, "a == 2"),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "func", ({1: 3}, [])),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_bp_exception_on_condition_evaluation(self):
        code = "\n            def func(a):\n                lno = 3\n\n            def main():\n                func(0)\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("func", TEST_MODULE_FNAME, False, "1 / 0"),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "func", ({1: 1}, [])),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_bp_ignore_count(self):
        code = "\n            def func():\n                lno = 3\n\n            def main():\n                for i in range(2):\n                    func()\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("func", TEST_MODULE_FNAME),
                ("None", 2, "tfunc_import"),
                ("ignore", (1,)),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "func", ({1: 2}, [])),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_ignore_count_on_disabled_bp(self):
        code = "\n            def func():\n                lno = 3\n\n            def main():\n                for i in range(3):\n                    func()\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("func", TEST_MODULE_FNAME),
                ("None", 2, "tfunc_import"),
                break_in_func("func", TEST_MODULE_FNAME),
                ("None", 2, "tfunc_import"),
                ("ignore", (1,)),
                ("None", 2, "tfunc_import"),
                ("disable", (1,)),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "func", ({2: 1}, [])),
                ("enable", (1,)),
                ("None", 3, "func"),
                ("continue",),
                ("line", 3, "func", ({2: 2}, [])),
                ("continue",),
                ("line", 3, "func", ({1: 2}, [])),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_clear_two_bp_on_same_line(self):
        code = "\n            def func():\n                lno = 3\n                lno = 4\n\n            def main():\n                for i in range(3):\n                    func()\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                ("break", (TEST_MODULE_FNAME, 3)),
                ("None", 2, "tfunc_import"),
                ("break", (TEST_MODULE_FNAME, 3)),
                ("None", 2, "tfunc_import"),
                ("break", (TEST_MODULE_FNAME, 4)),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "func", ({1: 1}, [])),
                ("continue",),
                ("line", 4, "func", ({3: 1}, [])),
                ("clear", (TEST_MODULE_FNAME, 3)),
                ("None", 4, "func"),
                ("continue",),
                ("line", 4, "func", ({3: 2}, [])),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_clear_at_no_bp(self):
        self.expect_set = [("line", 2, "tfunc_import"), ("clear", (__file__, 1))]
        with TracerRun(self) as tracer:
            self.assertRaises(BdbError, tracer.runcall, tfunc_import)

    def test_load_bps_from_previous_Bdb_instance(self):
        reset_Breakpoint()
        db1 = Bdb()
        fname = db1.canonic(__file__)
        db1.set_break(__file__, 1)
        self.assertEqual(db1.get_all_breaks(), {fname: [1]})
        db2 = Bdb()
        db2.set_break(__file__, 2)
        db2.set_break(__file__, 3)
        db2.set_break(__file__, 4)
        self.assertEqual(db1.get_all_breaks(), {fname: [1]})
        self.assertEqual(db2.get_all_breaks(), {fname: [1, 2, 3, 4]})
        db2.clear_break(__file__, 1)
        self.assertEqual(db1.get_all_breaks(), {fname: [1]})
        self.assertEqual(db2.get_all_breaks(), {fname: [2, 3, 4]})
        db3 = Bdb()
        self.assertEqual(db1.get_all_breaks(), {fname: [1]})
        self.assertEqual(db2.get_all_breaks(), {fname: [2, 3, 4]})
        self.assertEqual(db3.get_all_breaks(), {fname: [2, 3, 4]})
        db2.clear_break(__file__, 2)
        self.assertEqual(db1.get_all_breaks(), {fname: [1]})
        self.assertEqual(db2.get_all_breaks(), {fname: [3, 4]})
        self.assertEqual(db3.get_all_breaks(), {fname: [2, 3, 4]})
        db4 = Bdb()
        db4.set_break(__file__, 5)
        self.assertEqual(db1.get_all_breaks(), {fname: [1]})
        self.assertEqual(db2.get_all_breaks(), {fname: [3, 4]})
        self.assertEqual(db3.get_all_breaks(), {fname: [2, 3, 4]})
        self.assertEqual(db4.get_all_breaks(), {fname: [3, 4, 5]})
        reset_Breakpoint()
        db5 = Bdb()
        db5.set_break(__file__, 6)
        self.assertEqual(db1.get_all_breaks(), {fname: [1]})
        self.assertEqual(db2.get_all_breaks(), {fname: [3, 4]})
        self.assertEqual(db3.get_all_breaks(), {fname: [2, 3, 4]})
        self.assertEqual(db4.get_all_breaks(), {fname: [3, 4, 5]})
        self.assertEqual(db5.get_all_breaks(), {fname: [6]})


class RunTestCase(BaseTestCase):
    "Test run, runeval and set_trace."

    def test_run_step(self):
        code = "\n            lno = 2\n        "
        self.expect_set = [
            ("line", 2, "<module>"),
            ("step",),
            ("return", 2, "<module>"),
            ("quit",),
        ]
        with TracerRun(self) as tracer:
            tracer.run(compile(textwrap.dedent(code), "<string>", "exec"))

    def test_runeval_step(self):
        code = "\n            def main():\n                lno = 3\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 1, "<module>"),
                ("step",),
                ("call", 2, "main"),
                ("step",),
                ("line", 3, "main"),
                ("step",),
                ("return", 3, "main"),
                ("step",),
                ("return", 1, "<module>"),
                ("quit",),
            ]
            import test_module_for_bdb

            with TracerRun(self) as tracer:
                tracer.runeval("test_module_for_bdb.main()", globals(), locals())


class IssuesTestCase(BaseTestCase):
    "Test fixed bdb issues."

    def test_step_at_return_with_no_trace_in_caller(self):
        code_1 = "\n            from test_module_for_bdb_2 import func\n            def main():\n                func()\n                lno = 5\n        "
        code_2 = "\n            def func():\n                lno = 3\n        "
        modules = {TEST_MODULE: code_1, "test_module_for_bdb_2": code_2}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("func", "test_module_for_bdb_2.py"),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "func", ({1: 1}, [])),
                ("step",),
                ("return", 3, "func"),
                ("step",),
                ("line", 5, "main"),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_next_until_return_in_generator(self):
        code = "\n            def test_gen():\n                yield 0\n                lno = 4\n                return 123\n\n            def main():\n                it = test_gen()\n                next(it)\n                next(it)\n                lno = 11\n        "
        modules = {TEST_MODULE: code}
        for set_type in ("next", "until", "return"):
            with self.subTest(set_type=set_type):
                with create_modules(modules):
                    self.expect_set = [
                        ("line", 2, "tfunc_import"),
                        break_in_func("test_gen", TEST_MODULE_FNAME),
                        ("None", 2, "tfunc_import"),
                        ("continue",),
                        ("line", 3, "test_gen", ({1: 1}, [])),
                        (set_type,),
                    ]
                    if set_type == "return":
                        self.expect_set.extend(
                            [
                                ("exception", 10, "main", StopIteration),
                                ("step",),
                                ("return", 10, "main"),
                                ("quit",),
                            ]
                        )
                    else:
                        self.expect_set.extend([("line", 4, "test_gen"), ("quit",)])
                    with TracerRun(self) as tracer:
                        tracer.runcall(tfunc_import)

    def test_next_command_in_generator_for_loop(self):
        code = "\n            def test_gen():\n                yield 0\n                lno = 4\n                yield 1\n                return 123\n\n            def main():\n                for i in test_gen():\n                    lno = 10\n                lno = 11\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("test_gen", TEST_MODULE_FNAME),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "test_gen", ({1: 1}, [])),
                ("next",),
                ("line", 4, "test_gen"),
                ("next",),
                ("line", 5, "test_gen"),
                ("next",),
                ("line", 6, "test_gen"),
                ("next",),
                ("exception", 9, "main", StopIteration),
                ("step",),
                ("line", 11, "main"),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_next_command_in_generator_with_subiterator(self):
        code = "\n            def test_subgen():\n                yield 0\n                return 123\n\n            def test_gen():\n                x = yield from test_subgen()\n                return 456\n\n            def main():\n                for i in test_gen():\n                    lno = 12\n                lno = 13\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("test_gen", TEST_MODULE_FNAME),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 7, "test_gen", ({1: 1}, [])),
                ("next",),
                ("line", 8, "test_gen"),
                ("next",),
                ("exception", 11, "main", StopIteration),
                ("step",),
                ("line", 13, "main"),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)

    def test_return_command_in_generator_with_subiterator(self):
        code = "\n            def test_subgen():\n                yield 0\n                return 123\n\n            def test_gen():\n                x = yield from test_subgen()\n                return 456\n\n            def main():\n                for i in test_gen():\n                    lno = 12\n                lno = 13\n        "
        modules = {TEST_MODULE: code}
        with create_modules(modules):
            self.expect_set = [
                ("line", 2, "tfunc_import"),
                break_in_func("test_subgen", TEST_MODULE_FNAME),
                ("None", 2, "tfunc_import"),
                ("continue",),
                ("line", 3, "test_subgen", ({1: 1}, [])),
                ("return",),
                ("exception", 7, "test_gen", StopIteration),
                ("return",),
                ("exception", 11, "main", StopIteration),
                ("step",),
                ("line", 13, "main"),
                ("quit",),
            ]
            with TracerRun(self) as tracer:
                tracer.runcall(tfunc_import)


def test_main():
    test.support.run_unittest(
        StateTestCase, RunTestCase, BreakpointTestCase, IssuesTestCase
    )


if __name__ == "__main__":
    test_main()
