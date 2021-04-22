"Class for profiling Python code."
import sys
import time
import marshal

__all__ = ["run", "runctx", "Profile"]


class _Utils:
    "Support class for utility functions which are shared by\n    profile.py and cProfile.py modules.\n    Not supposed to be used directly.\n    "

    def __init__(self, profiler):
        self.profiler = profiler

    def run(self, statement, filename, sort):
        prof = self.profiler()
        try:
            prof.run(statement)
        except SystemExit:
            pass
        finally:
            self._show(prof, filename, sort)

    def runctx(self, statement, globals, locals, filename, sort):
        prof = self.profiler()
        try:
            prof.runctx(statement, globals, locals)
        except SystemExit:
            pass
        finally:
            self._show(prof, filename, sort)

    def _show(self, prof, filename, sort):
        if filename is not None:
            prof.dump_stats(filename)
        else:
            prof.print_stats(sort)


def run(statement, filename=None, sort=(-1)):
    'Run statement under profiler optionally saving results in filename\n\n    This function takes a single argument that can be passed to the\n    "exec" statement, and an optional file name.  In all cases this\n    routine attempts to "exec" its first argument and gather profiling\n    statistics from the execution. If no file name is present, then this\n    function automatically prints a simple profiling report, sorted by the\n    standard name string (file/line/function-name) that is presented in\n    each line.\n    '
    return _Utils(Profile).run(statement, filename, sort)


def runctx(statement, globals, locals, filename=None, sort=(-1)):
    "Run statement under profiler, supplying your own globals and locals,\n    optionally saving results in filename.\n\n    statement and filename have the same semantics as profile.run\n    "
    return _Utils(Profile).runctx(statement, globals, locals, filename, sort)


class Profile:
    "Profiler class.\n\n    self.cur is always a tuple.  Each such tuple corresponds to a stack\n    frame that is currently active (self.cur[-2]).  The following are the\n    definitions of its members.  We use this external \"parallel stack\" to\n    avoid contaminating the program that we are profiling. (old profiler\n    used to write into the frames local dictionary!!) Derived classes\n    can change the definition of some entries, as long as they leave\n    [-2:] intact (frame and previous tuple).  In case an internal error is\n    detected, the -3 element is used as the function name.\n\n    [ 0] = Time that needs to be charged to the parent frame's function.\n           It is used so that a function call will not have to access the\n           timing data for the parent frame.\n    [ 1] = Total time spent in this frame's function, excluding time in\n           subfunctions (this latter is tallied in cur[2]).\n    [ 2] = Total time spent in subfunctions, excluding time executing the\n           frame's function (this latter is tallied in cur[1]).\n    [-3] = Name of the function that corresponds to this frame.\n    [-2] = Actual frame that we correspond to (used to sync exception handling).\n    [-1] = Our parent 6-tuple (corresponds to frame.f_back).\n\n    Timing data for each function is stored as a 5-tuple in the dictionary\n    self.timings[].  The index is always the name stored in self.cur[-3].\n    The following are the definitions of the members:\n\n    [0] = The number of times this function was called, not counting direct\n          or indirect recursion,\n    [1] = Number of times this function appears on the stack, minus one\n    [2] = Total time spent internal to this function\n    [3] = Cumulative time that this function was present on the stack.  In\n          non-recursive functions, this is the total execution time from start\n          to finish of each invocation of a function, including time spent in\n          all subfunctions.\n    [4] = A dictionary indicating for each function name, the number of times\n          it was called by us.\n    "
    bias = 0

    def __init__(self, timer=None, bias=None):
        self.timings = {}
        self.cur = None
        self.cmd = ""
        self.c_func_name = ""
        if bias is None:
            bias = self.bias
        self.bias = bias
        if not timer:
            self.timer = self.get_time = time.process_time
            self.dispatcher = self.trace_dispatch_i
        else:
            self.timer = timer
            t = self.timer()
            try:
                length = len(t)
            except TypeError:
                self.get_time = timer
                self.dispatcher = self.trace_dispatch_i
            else:
                if length == 2:
                    self.dispatcher = self.trace_dispatch
                else:
                    self.dispatcher = self.trace_dispatch_l

                def get_time_timer(timer=timer, sum=sum):
                    return sum(timer())

                self.get_time = get_time_timer
        self.t = self.get_time()
        self.simulate_call("profiler")

    def trace_dispatch(self, frame, event, arg):
        timer = self.timer
        t = timer()
        t = ((t[0] + t[1]) - self.t) - self.bias
        if event == "c_call":
            self.c_func_name = arg.__name__
        if self.dispatch[event](self, frame, t):
            t = timer()
            self.t = t[0] + t[1]
        else:
            r = timer()
            self.t = (r[0] + r[1]) - t

    def trace_dispatch_i(self, frame, event, arg):
        timer = self.timer
        t = (timer() - self.t) - self.bias
        if event == "c_call":
            self.c_func_name = arg.__name__
        if self.dispatch[event](self, frame, t):
            self.t = timer()
        else:
            self.t = timer() - t

    def trace_dispatch_mac(self, frame, event, arg):
        timer = self.timer
        t = ((timer() / 60.0) - self.t) - self.bias
        if event == "c_call":
            self.c_func_name = arg.__name__
        if self.dispatch[event](self, frame, t):
            self.t = timer() / 60.0
        else:
            self.t = (timer() / 60.0) - t

    def trace_dispatch_l(self, frame, event, arg):
        get_time = self.get_time
        t = (get_time() - self.t) - self.bias
        if event == "c_call":
            self.c_func_name = arg.__name__
        if self.dispatch[event](self, frame, t):
            self.t = get_time()
        else:
            self.t = get_time() - t

    def trace_dispatch_exception(self, frame, t):
        (rpt, rit, ret, rfn, rframe, rcur) = self.cur
        if (rframe is not frame) and rcur:
            return self.trace_dispatch_return(rframe, t)
        self.cur = (rpt, (rit + t), ret, rfn, rframe, rcur)
        return 1

    def trace_dispatch_call(self, frame, t):
        if self.cur and (frame.f_back is not self.cur[(-2)]):
            (rpt, rit, ret, rfn, rframe, rcur) = self.cur
            if not isinstance(rframe, Profile.fake_frame):
                assert rframe.f_back is frame.f_back, (
                    "Bad call",
                    rfn,
                    rframe,
                    rframe.f_back,
                    frame,
                    frame.f_back,
                )
                self.trace_dispatch_return(rframe, 0)
                assert (self.cur is None) or (frame.f_back is self.cur[(-2)]), (
                    "Bad call",
                    self.cur[(-3)],
                )
        fcode = frame.f_code
        fn = (fcode.co_filename, fcode.co_firstlineno, fcode.co_name)
        self.cur = (t, 0, 0, fn, frame, self.cur)
        timings = self.timings
        if fn in timings:
            (cc, ns, tt, ct, callers) = timings[fn]
            timings[fn] = (cc, (ns + 1), tt, ct, callers)
        else:
            timings[fn] = (0, 0, 0, 0, {})
        return 1

    def trace_dispatch_c_call(self, frame, t):
        fn = ("", 0, self.c_func_name)
        self.cur = (t, 0, 0, fn, frame, self.cur)
        timings = self.timings
        if fn in timings:
            (cc, ns, tt, ct, callers) = timings[fn]
            timings[fn] = (cc, (ns + 1), tt, ct, callers)
        else:
            timings[fn] = (0, 0, 0, 0, {})
        return 1

    def trace_dispatch_return(self, frame, t):
        if frame is not self.cur[(-2)]:
            assert frame is self.cur[(-2)].f_back, ("Bad return", self.cur[(-3)])
            self.trace_dispatch_return(self.cur[(-2)], 0)
        (rpt, rit, ret, rfn, frame, rcur) = self.cur
        rit = rit + t
        frame_total = rit + ret
        (ppt, pit, pet, pfn, pframe, pcur) = rcur
        self.cur = (ppt, (pit + rpt), (pet + frame_total), pfn, pframe, pcur)
        timings = self.timings
        (cc, ns, tt, ct, callers) = timings[rfn]
        if not ns:
            ct = ct + frame_total
            cc = cc + 1
        if pfn in callers:
            callers[pfn] = callers[pfn] + 1
        else:
            callers[pfn] = 1
        timings[rfn] = (cc, (ns - 1), (tt + rit), ct, callers)
        return 1

    dispatch = {
        "call": trace_dispatch_call,
        "exception": trace_dispatch_exception,
        "return": trace_dispatch_return,
        "c_call": trace_dispatch_c_call,
        "c_exception": trace_dispatch_return,
        "c_return": trace_dispatch_return,
    }

    def set_cmd(self, cmd):
        if self.cur[(-1)]:
            return
        self.cmd = cmd
        self.simulate_call(cmd)

    class fake_code:
        def __init__(self, filename, line, name):
            self.co_filename = filename
            self.co_line = line
            self.co_name = name
            self.co_firstlineno = 0

        def __repr__(self):
            return repr((self.co_filename, self.co_line, self.co_name))

    class fake_frame:
        def __init__(self, code, prior):
            self.f_code = code
            self.f_back = prior

    def simulate_call(self, name):
        code = self.fake_code("profile", 0, name)
        if self.cur:
            pframe = self.cur[(-2)]
        else:
            pframe = None
        frame = self.fake_frame(code, pframe)
        self.dispatch["call"](self, frame, 0)

    def simulate_cmd_complete(self):
        get_time = self.get_time
        t = get_time() - self.t
        while self.cur[(-1)]:
            self.dispatch["return"](self, self.cur[(-2)], t)
            t = 0
        self.t = get_time() - t

    def print_stats(self, sort=(-1)):
        import pstats

        pstats.Stats(self).strip_dirs().sort_stats(sort).print_stats()

    def dump_stats(self, file):
        with open(file, "wb") as f:
            self.create_stats()
            marshal.dump(self.stats, f)

    def create_stats(self):
        self.simulate_cmd_complete()
        self.snapshot_stats()

    def snapshot_stats(self):
        self.stats = {}
        for (func, (cc, ns, tt, ct, callers)) in self.timings.items():
            callers = callers.copy()
            nc = 0
            for callcnt in callers.values():
                nc += callcnt
            self.stats[func] = (cc, nc, tt, ct, callers)

    def run(self, cmd):
        import __main__

        dict = __main__.__dict__
        return self.runctx(cmd, dict, dict)

    def runctx(self, cmd, globals, locals):
        self.set_cmd(cmd)
        sys.setprofile(self.dispatcher)
        try:
            exec(cmd, globals, locals)
        finally:
            sys.setprofile(None)
        return self

    def runcall(self, func, /, *args, **kw):
        self.set_cmd(repr(func))
        sys.setprofile(self.dispatcher)
        try:
            return func(*args, **kw)
        finally:
            sys.setprofile(None)

    def calibrate(self, m, verbose=0):
        if self.__class__ is not Profile:
            raise TypeError("Subclasses must override .calibrate().")
        saved_bias = self.bias
        self.bias = 0
        try:
            return self._calibrate_inner(m, verbose)
        finally:
            self.bias = saved_bias

    def _calibrate_inner(self, m, verbose):
        get_time = self.get_time

        def f1(n):
            for i in range(n):
                x = 1

        def f(m, f1=f1):
            for i in range(m):
                f1(100)

        f(m)
        t0 = get_time()
        f(m)
        t1 = get_time()
        elapsed_noprofile = t1 - t0
        if verbose:
            print("elapsed time without profiling =", elapsed_noprofile)
        p = Profile()
        t0 = get_time()
        p.runctx("f(m)", globals(), locals())
        t1 = get_time()
        elapsed_profile = t1 - t0
        if verbose:
            print("elapsed time with profiling =", elapsed_profile)
        total_calls = 0.0
        reported_time = 0.0
        for (
            (filename, line, funcname),
            (cc, ns, tt, ct, callers),
        ) in p.timings.items():
            if funcname in ("f", "f1"):
                total_calls += cc
                reported_time += tt
        if verbose:
            print("'CPU seconds' profiler reported =", reported_time)
            print("total # calls =", total_calls)
        if total_calls != (m + 1):
            raise ValueError(("internal error: total calls = %d" % total_calls))
        mean = ((reported_time - elapsed_noprofile) / 2.0) / total_calls
        if verbose:
            print("mean stopwatch overhead per profile event =", mean)
        return mean


def main():
    import os
    from optparse import OptionParser

    usage = (
        "profile.py [-o output_file_path] [-s sort] [-m module | scriptfile] [arg] ..."
    )
    parser = OptionParser(usage=usage)
    parser.allow_interspersed_args = False
    parser.add_option(
        "-o", "--outfile", dest="outfile", help="Save stats to <outfile>", default=None
    )
    parser.add_option(
        "-m",
        dest="module",
        action="store_true",
        help="Profile a library module.",
        default=False,
    )
    parser.add_option(
        "-s",
        "--sort",
        dest="sort",
        help="Sort order when printing to stdout, based on pstats.Stats class",
        default=(-1),
    )
    if not sys.argv[1:]:
        parser.print_usage()
        sys.exit(2)
    (options, args) = parser.parse_args()
    sys.argv[:] = args
    if options.outfile is not None:
        options.outfile = os.path.abspath(options.outfile)
    if len(args) > 0:
        if options.module:
            import runpy

            code = "run_module(modname, run_name='__main__')"
            globs = {"run_module": runpy.run_module, "modname": args[0]}
        else:
            progname = args[0]
            sys.path.insert(0, os.path.dirname(progname))
            with open(progname, "rb") as fp:
                code = compile(fp.read(), progname, "exec")
            globs = {
                "__file__": progname,
                "__name__": "__main__",
                "__package__": None,
                "__cached__": None,
            }
        try:
            runctx(code, globs, None, options.outfile, options.sort)
        except BrokenPipeError as exc:
            sys.stdout = None
            sys.exit(exc.errno)
    else:
        parser.print_usage()
    return parser


if __name__ == "__main__":
    main()
