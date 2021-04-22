"Tool for measuring execution time of small code snippets.\n\nThis module avoids a number of common traps for measuring execution\ntimes.  See also Tim Peters' introduction to the Algorithms chapter in\nthe Python Cookbook, published by O'Reilly.\n\nLibrary usage: see the Timer class.\n\nCommand line usage:\n    python timeit.py [-n N] [-r N] [-s S] [-p] [-h] [--] [statement]\n\nOptions:\n  -n/--number N: how many times to execute 'statement' (default: see below)\n  -r/--repeat N: how many times to repeat the timer (default 5)\n  -s/--setup S: statement to be executed once initially (default 'pass').\n                Execution time of this setup statement is NOT timed.\n  -p/--process: use time.process_time() (default is time.perf_counter())\n  -v/--verbose: print raw timing results; repeat for more digits precision\n  -u/--unit: set the output time unit (nsec, usec, msec, or sec)\n  -h/--help: print this usage message and exit\n  --: separate options from statement, use when statement starts with -\n  statement: statement to be timed (default 'pass')\n\nA multi-line statement may be given by specifying each line as a\nseparate argument; indented lines are possible by enclosing an\nargument in quotes and using leading spaces.  Multiple -s options are\ntreated similarly.\n\nIf -n is not given, a suitable number of loops is calculated by trying\nincreasing numbers from the sequence 1, 2, 5, 10, 20, 50, ... until the\ntotal time is at least 0.2 seconds.\n\nNote: there is a certain baseline overhead associated with executing a\npass statement.  It differs between versions.  The code here doesn't try\nto hide it, but you should be aware of it.  The baseline overhead can be\nmeasured by invoking the program without arguments.\n\nClasses:\n\n    Timer\n\nFunctions:\n\n    timeit(string, string) -> float\n    repeat(string, string) -> list\n    default_timer() -> float\n\n"
import gc
import sys
import time
import itertools

__all__ = ["Timer", "timeit", "repeat", "default_timer"]
dummy_src_name = "<timeit-src>"
default_number = 1000000
default_repeat = 5
default_timer = time.perf_counter
_globals = globals
template = "\ndef inner(_it, _timer{init}):\n    {setup}\n    _t0 = _timer()\n    for _i in _it:\n        {stmt}\n        pass\n    _t1 = _timer()\n    return _t1 - _t0\n"


def reindent(src, indent):
    "Helper to reindent a multi-line statement."
    return src.replace("\n", ("\n" + (" " * indent)))


class Timer:
    "Class for timing execution speed of small code snippets.\n\n    The constructor takes a statement to be timed, an additional\n    statement used for setup, and a timer function.  Both statements\n    default to 'pass'; the timer function is platform-dependent (see\n    module doc string).  If 'globals' is specified, the code will be\n    executed within that namespace (as opposed to inside timeit's\n    namespace).\n\n    To measure the execution time of the first statement, use the\n    timeit() method.  The repeat() method is a convenience to call\n    timeit() multiple times and return a list of results.\n\n    The statements may contain newlines, as long as they don't contain\n    multi-line string literals.\n    "

    def __init__(self, stmt="pass", setup="pass", timer=default_timer, globals=None):
        "Constructor.  See class doc string."
        self.timer = timer
        local_ns = {}
        global_ns = _globals() if (globals is None) else globals
        init = ""
        if isinstance(setup, str):
            compile(setup, dummy_src_name, "exec")
            stmtprefix = setup + "\n"
            setup = reindent(setup, 4)
        elif callable(setup):
            local_ns["_setup"] = setup
            init += ", _setup=_setup"
            stmtprefix = ""
            setup = "_setup()"
        else:
            raise ValueError("setup is neither a string nor callable")
        if isinstance(stmt, str):
            compile((stmtprefix + stmt), dummy_src_name, "exec")
            stmt = reindent(stmt, 8)
        elif callable(stmt):
            local_ns["_stmt"] = stmt
            init += ", _stmt=_stmt"
            stmt = "_stmt()"
        else:
            raise ValueError("stmt is neither a string nor callable")
        src = template.format(stmt=stmt, setup=setup, init=init)
        self.src = src
        code = compile(src, dummy_src_name, "exec")
        exec(code, global_ns, local_ns)
        self.inner = local_ns["inner"]

    def print_exc(self, file=None):
        "Helper to print a traceback from the timed code.\n\n        Typical use:\n\n            t = Timer(...)       # outside the try/except\n            try:\n                t.timeit(...)    # or t.repeat(...)\n            except:\n                t.print_exc()\n\n        The advantage over the standard traceback is that source lines\n        in the compiled template will be displayed.\n\n        The optional file argument directs where the traceback is\n        sent; it defaults to sys.stderr.\n        "
        import linecache, traceback

        if self.src is not None:
            linecache.cache[dummy_src_name] = (
                len(self.src),
                None,
                self.src.split("\n"),
                dummy_src_name,
            )
        traceback.print_exc(file=file)

    def timeit(self, number=default_number):
        "Time 'number' executions of the main statement.\n\n        To be precise, this executes the setup statement once, and\n        then returns the time it takes to execute the main statement\n        a number of times, as a float measured in seconds.  The\n        argument is the number of times through the loop, defaulting\n        to one million.  The main statement, the setup statement and\n        the timer function to be used are passed to the constructor.\n        "
        it = itertools.repeat(None, number)
        gcold = gc.isenabled()
        gc.disable()
        try:
            timing = self.inner(it, self.timer)
        finally:
            if gcold:
                gc.enable()
        return timing

    def repeat(self, repeat=default_repeat, number=default_number):
        "Call timeit() a few times.\n\n        This is a convenience function that calls the timeit()\n        repeatedly, returning a list of results.  The first argument\n        specifies how many times to call timeit(), defaulting to 5;\n        the second argument specifies the timer argument, defaulting\n        to one million.\n\n        Note: it's tempting to calculate mean and standard deviation\n        from the result vector and report these.  However, this is not\n        very useful.  In a typical case, the lowest value gives a\n        lower bound for how fast your machine can run the given code\n        snippet; higher values in the result vector are typically not\n        caused by variability in Python's speed, but by other\n        processes interfering with your timing accuracy.  So the min()\n        of the result is probably the only number you should be\n        interested in.  After that, you should look at the entire\n        vector and apply common sense rather than statistics.\n        "
        r = []
        for i in range(repeat):
            t = self.timeit(number)
            r.append(t)
        return r

    def autorange(self, callback=None):
        "Return the number of loops and time taken so that total time >= 0.2.\n\n        Calls the timeit method with increasing numbers from the sequence\n        1, 2, 5, 10, 20, 50, ... until the time taken is at least 0.2\n        second.  Returns (number, time_taken).\n\n        If *callback* is given and is not None, it will be called after\n        each trial with two arguments: ``callback(number, time_taken)``.\n        "
        i = 1
        while True:
            for j in (1, 2, 5):
                number = i * j
                time_taken = self.timeit(number)
                if callback:
                    callback(number, time_taken)
                if time_taken >= 0.2:
                    return (number, time_taken)
            i *= 10


def timeit(
    stmt="pass", setup="pass", timer=default_timer, number=default_number, globals=None
):
    "Convenience function to create Timer object and call timeit method."
    return Timer(stmt, setup, timer, globals).timeit(number)


def repeat(
    stmt="pass",
    setup="pass",
    timer=default_timer,
    repeat=default_repeat,
    number=default_number,
    globals=None,
):
    "Convenience function to create Timer object and call repeat method."
    return Timer(stmt, setup, timer, globals).repeat(repeat, number)


def main(args=None, *, _wrap_timer=None):
    "Main program, used when run as a script.\n\n    The optional 'args' argument specifies the command line to be parsed,\n    defaulting to sys.argv[1:].\n\n    The return value is an exit code to be passed to sys.exit(); it\n    may be None to indicate success.\n\n    When an exception happens during timing, a traceback is printed to\n    stderr and the return value is 1.  Exceptions at other times\n    (including the template compilation) are not caught.\n\n    '_wrap_timer' is an internal interface used for unit testing.  If it\n    is not None, it must be a callable that accepts a timer function\n    and returns another timer function (used for unit testing).\n    "
    if args is None:
        args = sys.argv[1:]
    import getopt

    try:
        (opts, args) = getopt.getopt(
            args,
            "n:u:s:r:tcpvh",
            [
                "number=",
                "setup=",
                "repeat=",
                "time",
                "clock",
                "process",
                "verbose",
                "unit=",
                "help",
            ],
        )
    except getopt.error as err:
        print(err)
        print("use -h/--help for command line help")
        return 2
    timer = default_timer
    stmt = "\n".join(args) or "pass"
    number = 0
    setup = []
    repeat = default_repeat
    verbose = 0
    time_unit = None
    units = {"nsec": 1e-09, "usec": 1e-06, "msec": 0.001, "sec": 1.0}
    precision = 3
    for (o, a) in opts:
        if o in ("-n", "--number"):
            number = int(a)
        if o in ("-s", "--setup"):
            setup.append(a)
        if o in ("-u", "--unit"):
            if a in units:
                time_unit = a
            else:
                print(
                    "Unrecognized unit. Please select nsec, usec, msec, or sec.",
                    file=sys.stderr,
                )
                return 2
        if o in ("-r", "--repeat"):
            repeat = int(a)
            if repeat <= 0:
                repeat = 1
        if o in ("-p", "--process"):
            timer = time.process_time
        if o in ("-v", "--verbose"):
            if verbose:
                precision += 1
            verbose += 1
        if o in ("-h", "--help"):
            print(__doc__, end=" ")
            return 0
    setup = "\n".join(setup) or "pass"
    import os

    sys.path.insert(0, os.curdir)
    if _wrap_timer is not None:
        timer = _wrap_timer(timer)
    t = Timer(stmt, setup, timer)
    if number == 0:
        callback = None
        if verbose:

            def callback(number, time_taken):
                msg = "{num} loop{s} -> {secs:.{prec}g} secs"
                plural = number != 1
                print(
                    msg.format(
                        num=number,
                        s=("s" if plural else ""),
                        secs=time_taken,
                        prec=precision,
                    )
                )

        try:
            (number, _) = t.autorange(callback)
        except:
            t.print_exc()
            return 1
        if verbose:
            print()
    try:
        raw_timings = t.repeat(repeat, number)
    except:
        t.print_exc()
        return 1

    def format_time(dt):
        unit = time_unit
        if unit is not None:
            scale = units[unit]
        else:
            scales = [(scale, unit) for (unit, scale) in units.items()]
            scales.sort(reverse=True)
            for (scale, unit) in scales:
                if dt >= scale:
                    break
        return "%.*g %s" % (precision, (dt / scale), unit)

    if verbose:
        print(("raw times: %s" % ", ".join(map(format_time, raw_timings))))
        print()
    timings = [(dt / number) for dt in raw_timings]
    best = min(timings)
    print(
        (
            "%d loop%s, best of %d: %s per loop"
            % (number, ("s" if (number != 1) else ""), repeat, format_time(best))
        )
    )
    best = min(timings)
    worst = max(timings)
    if worst >= (best * 4):
        import warnings

        warnings.warn_explicit(
            (
                "The test results are likely unreliable. The worst time (%s) was more than four times slower than the best time (%s)."
                % (format_time(worst), format_time(best))
            ),
            UserWarning,
            "",
            0,
        )
    return None


if __name__ == "__main__":
    sys.exit(main())
