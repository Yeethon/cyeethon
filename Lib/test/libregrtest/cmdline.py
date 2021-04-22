import argparse
import os
import sys
from test import support
from test.support import os_helper

USAGE = "python -m test [options] [test_name1 [test_name2 ...]]\npython path/to/Lib/test/regrtest.py [options] [test_name1 [test_name2 ...]]\n"
DESCRIPTION = 'Run Python regression tests.\n\nIf no arguments or options are provided, finds all files matching\nthe pattern "test_*" in the Lib/test subdirectory and runs\nthem in alphabetical order (but see -M and -u, below, for exceptions).\n\nFor more rigorous testing, it is useful to use the following\ncommand line:\n\npython -E -Wd -m test [options] [test_name1 ...]\n'
EPILOG = "Additional option details:\n\n-r randomizes test execution order. You can use --randseed=int to provide an\nint seed value for the randomizer; this is useful for reproducing troublesome\ntest orders.\n\n-s On the first invocation of regrtest using -s, the first test file found\nor the first test file given on the command line is run, and the name of\nthe next test is recorded in a file named pynexttest.  If run from the\nPython build directory, pynexttest is located in the 'build' subdirectory,\notherwise it is located in tempfile.gettempdir().  On subsequent runs,\nthe test in pynexttest is run, and the next test is written to pynexttest.\nWhen the last test has been run, pynexttest is deleted.  In this way it\nis possible to single step through the test files.  This is useful when\ndoing memory analysis on the Python interpreter, which process tends to\nconsume too many resources to run the full regression test non-stop.\n\n-S is used to continue running tests after an aborted run.  It will\nmaintain the order a standard run (ie, this assumes -r is not used).\nThis is useful after the tests have prematurely stopped for some external\nreason and you want to start running from where you left off rather\nthan starting from the beginning.\n\n-f reads the names of tests from the file given as f's argument, one\nor more test names per line.  Whitespace is ignored.  Blank lines and\nlines beginning with '#' are ignored.  This is especially useful for\nwhittling down failures involving interactions among tests.\n\n-L causes the leaks(1) command to be run just before exit if it exists.\nleaks(1) is available on Mac OS X and presumably on some other\nFreeBSD-derived systems.\n\n-R runs each test several times and examines sys.gettotalrefcount() to\nsee if the test appears to be leaking references.  The argument should\nbe of the form stab:run:fname where 'stab' is the number of times the\ntest is run to let gettotalrefcount settle down, 'run' is the number\nof times further it is run and 'fname' is the name of the file the\nreports are written to.  These parameters all have defaults (5, 4 and\n\"reflog.txt\" respectively), and the minimal invocation is '-R :'.\n\n-M runs tests that require an exorbitant amount of memory. These tests\ntypically try to ascertain containers keep working when containing more than\n2 billion objects, which only works on 64-bit systems. There are also some\ntests that try to exhaust the address space of the process, which only makes\nsense on 32-bit systems with at least 2Gb of memory. The passed-in memlimit,\nwhich is a string in the form of '2.5Gb', determines how much memory the\ntests will limit themselves to (but they may go slightly over.) The number\nshouldn't be more memory than the machine has (including swap memory). You\nshould also keep in mind that swap memory is generally much, much slower\nthan RAM, and setting memlimit to all available RAM or higher will heavily\ntax the machine. On the other hand, it is no use running these tests with a\nlimit of less than 2.5Gb, and many require more than 20Gb. Tests that expect\nto use more than memlimit memory will be skipped. The big-memory tests\ngenerally run very, very long.\n\n-u is used to specify which special resource intensive tests to run,\nsuch as those requiring large file support or network connectivity.\nThe argument is a comma-separated list of words indicating the\nresources to test.  Currently only the following are defined:\n\n    all -       Enable all special resources.\n\n    none -      Disable all special resources (this is the default).\n\n    audio -     Tests that use the audio device.  (There are known\n                cases of broken audio drivers that can crash Python or\n                even the Linux kernel.)\n\n    curses -    Tests that use curses and will modify the terminal's\n                state and output modes.\n\n    largefile - It is okay to run some test that may create huge\n                files.  These tests can take a long time and may\n                consume >2 GiB of disk space temporarily.\n\n    network -   It is okay to run tests that use external network\n                resource, e.g. testing SSL support for sockets.\n\n    decimal -   Test the decimal module against a large suite that\n                verifies compliance with standards.\n\n    cpu -       Used for certain CPU-heavy tests.\n\n    subprocess  Run all tests for the subprocess module.\n\n    urlfetch -  It is okay to download files required on testing.\n\n    gui -       Run tests that require a running GUI.\n\n    tzdata -    Run tests that require timezone data.\n\nTo enable all resources except one, use '-uall,-<resource>'.  For\nexample, to run all the tests except for the gui tests, give the\noption '-uall,-gui'.\n\n--matchfile filters tests using a text file, one pattern per line.\nPattern examples:\n\n- test method: test_stat_attributes\n- test class: FileTests\n- test identifier: test_os.FileTests.test_stat_attributes\n"
ALL_RESOURCES = (
    "audio",
    "curses",
    "largefile",
    "network",
    "decimal",
    "cpu",
    "subprocess",
    "urlfetch",
    "gui",
)
RESOURCE_NAMES = ALL_RESOURCES + ("extralargefile", "tzdata")


class _ArgParser(argparse.ArgumentParser):
    def error(self, message):
        super().error((message + "\nPass -h or --help for complete help."))


def _create_parser():
    parser = _ArgParser(
        prog="regrtest.py",
        usage=USAGE,
        description=DESCRIPTION,
        epilog=EPILOG,
        add_help=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    more_details = "  See the section at bottom for more details."
    group = parser.add_argument_group("General options")
    group.add_argument(
        "-h", "--help", action="help", help="show this help message and exit"
    )
    group.add_argument(
        "--timeout",
        metavar="TIMEOUT",
        type=float,
        help="dump the traceback and exit if a test takes more than TIMEOUT seconds; disabled if TIMEOUT is negative or equals to zero",
    )
    group.add_argument(
        "--wait",
        action="store_true",
        help="wait for user input, e.g., allow a debugger to be attached",
    )
    group.add_argument("--worker-args", metavar="ARGS")
    group.add_argument(
        "-S",
        "--start",
        metavar="START",
        help=("the name of the test at which to start." + more_details),
    )
    group = parser.add_argument_group("Verbosity")
    group.add_argument(
        "-v",
        "--verbose",
        action="count",
        help="run tests in verbose mode with output to stdout",
    )
    group.add_argument(
        "-w",
        "--verbose2",
        action="store_true",
        help="re-run failed tests in verbose mode",
    )
    group.add_argument(
        "-W", "--verbose3", action="store_true", help="display test output on failure"
    )
    group.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="no output unless one or more tests fail",
    )
    group.add_argument(
        "-o",
        "--slowest",
        action="store_true",
        dest="print_slow",
        help="print the slowest 10 tests",
    )
    group.add_argument(
        "--header", action="store_true", help="print header with interpreter info"
    )
    group = parser.add_argument_group("Selecting tests")
    group.add_argument(
        "-r",
        "--randomize",
        action="store_true",
        help=("randomize test execution order." + more_details),
    )
    group.add_argument(
        "--randseed",
        metavar="SEED",
        dest="random_seed",
        type=int,
        help="pass a random seed to reproduce a previous random run",
    )
    group.add_argument(
        "-f",
        "--fromfile",
        metavar="FILE",
        help=("read names of tests to run from a file." + more_details),
    )
    group.add_argument(
        "-x", "--exclude", action="store_true", help="arguments are tests to *exclude*"
    )
    group.add_argument(
        "-s",
        "--single",
        action="store_true",
        help=("single step through a set of tests." + more_details),
    )
    group.add_argument(
        "-m",
        "--match",
        metavar="PAT",
        dest="match_tests",
        action="append",
        help="match test cases and methods with glob pattern PAT",
    )
    group.add_argument(
        "-i",
        "--ignore",
        metavar="PAT",
        dest="ignore_tests",
        action="append",
        help="ignore test cases and methods with glob pattern PAT",
    )
    group.add_argument(
        "--matchfile",
        metavar="FILENAME",
        dest="match_filename",
        help="similar to --match but get patterns from a text file, one pattern per line",
    )
    group.add_argument(
        "--ignorefile",
        metavar="FILENAME",
        dest="ignore_filename",
        help="similar to --matchfile but it receives patterns from text file to ignore",
    )
    group.add_argument(
        "-G",
        "--failfast",
        action="store_true",
        help="fail as soon as a test fails (only with -v or -W)",
    )
    group.add_argument(
        "-u",
        "--use",
        metavar="RES1,RES2,...",
        action="append",
        type=resources_list,
        help=("specify which special resource intensive tests to run." + more_details),
    )
    group.add_argument(
        "-M",
        "--memlimit",
        metavar="LIMIT",
        help=("run very large memory-consuming tests." + more_details),
    )
    group.add_argument(
        "--testdir",
        metavar="DIR",
        type=relative_filename,
        help="execute test files in the specified directory (instead of the Python stdlib test suite)",
    )
    group = parser.add_argument_group("Special runs")
    group.add_argument(
        "-l",
        "--findleaks",
        action="store_const",
        const=2,
        default=1,
        help="deprecated alias to --fail-env-changed",
    )
    group.add_argument(
        "-L",
        "--runleaks",
        action="store_true",
        help=("run the leaks(1) command just before exit." + more_details),
    )
    group.add_argument(
        "-R",
        "--huntrleaks",
        metavar="RUNCOUNTS",
        type=huntrleaks,
        help=(
            "search for reference leaks (needs debug build, very slow)." + more_details
        ),
    )
    group.add_argument(
        "-j",
        "--multiprocess",
        metavar="PROCESSES",
        dest="use_mp",
        type=int,
        help="run PROCESSES processes at once",
    )
    group.add_argument(
        "-T",
        "--coverage",
        action="store_true",
        dest="trace",
        help="turn on code coverage tracing using the trace module",
    )
    group.add_argument(
        "-D",
        "--coverdir",
        metavar="DIR",
        type=relative_filename,
        help="directory where coverage files are put",
    )
    group.add_argument(
        "-N",
        "--nocoverdir",
        action="store_const",
        const=None,
        dest="coverdir",
        help="put coverage files alongside modules",
    )
    group.add_argument(
        "-t",
        "--threshold",
        metavar="THRESHOLD",
        type=int,
        help="call gc.set_threshold(THRESHOLD)",
    )
    group.add_argument(
        "-n",
        "--nowindows",
        action="store_true",
        help="suppress error message boxes on Windows",
    )
    group.add_argument(
        "-F",
        "--forever",
        action="store_true",
        help="run the specified tests in a loop, until an error happens; imply --failfast",
    )
    group.add_argument(
        "--list-tests",
        action="store_true",
        help="only write the name of tests that will be run, don't execute them",
    )
    group.add_argument(
        "--list-cases",
        action="store_true",
        help="only write the name of test cases that will be run , don't execute them",
    )
    group.add_argument(
        "-P",
        "--pgo",
        dest="pgo",
        action="store_true",
        help="enable Profile Guided Optimization (PGO) training",
    )
    group.add_argument(
        "--pgo-extended",
        action="store_true",
        help="enable extended PGO training (slower training)",
    )
    group.add_argument(
        "--fail-env-changed",
        action="store_true",
        help="if a test file alters the environment, mark the test as failed",
    )
    group.add_argument(
        "--junit-xml",
        dest="xmlpath",
        metavar="FILENAME",
        help="writes JUnit-style XML results to the specified file",
    )
    group.add_argument(
        "--tempdir",
        metavar="PATH",
        help="override the working directory for the test run",
    )
    group.add_argument(
        "--cleanup", action="store_true", help="remove old test_python_* directories"
    )
    return parser


def relative_filename(string):
    return os.path.join(os_helper.SAVEDCWD, string)


def huntrleaks(string):
    args = string.split(":")
    if len(args) not in (2, 3):
        raise argparse.ArgumentTypeError("needs 2 or 3 colon-separated arguments")
    nwarmup = int(args[0]) if args[0] else 5
    ntracked = int(args[1]) if args[1] else 4
    fname = args[2] if ((len(args) > 2) and args[2]) else "reflog.txt"
    return (nwarmup, ntracked, fname)


def resources_list(string):
    u = [x.lower() for x in string.split(",")]
    for r in u:
        if (r == "all") or (r == "none"):
            continue
        if r[0] == "-":
            r = r[1:]
        if r not in RESOURCE_NAMES:
            raise argparse.ArgumentTypeError(("invalid resource: " + r))
    return u


def _parse_args(args, **kwargs):
    ns = argparse.Namespace(
        testdir=None,
        verbose=0,
        quiet=False,
        exclude=False,
        single=False,
        randomize=False,
        fromfile=None,
        findleaks=1,
        use_resources=None,
        trace=False,
        coverdir="coverage",
        runleaks=False,
        huntrleaks=False,
        verbose2=False,
        print_slow=False,
        random_seed=None,
        use_mp=None,
        verbose3=False,
        forever=False,
        header=False,
        failfast=False,
        match_tests=None,
        ignore_tests=None,
        pgo=False,
    )
    for (k, v) in kwargs.items():
        if not hasattr(ns, k):
            raise TypeError(("%r is an invalid keyword argument for this function" % k))
        setattr(ns, k, v)
    if ns.use_resources is None:
        ns.use_resources = []
    parser = _create_parser()
    ns.args = parser.parse_known_args(args=args, namespace=ns)[1]
    for arg in ns.args:
        if arg.startswith("-"):
            parser.error(("unrecognized arguments: %s" % arg))
            sys.exit(1)
    if ns.findleaks > 1:
        ns.fail_env_changed = True
    if ns.single and ns.fromfile:
        parser.error("-s and -f don't go together!")
    if (ns.use_mp is not None) and ns.trace:
        parser.error("-T and -j don't go together!")
    if ns.failfast and (not (ns.verbose or ns.verbose3)):
        parser.error("-G/--failfast needs either -v or -W")
    if ns.pgo and (ns.verbose or ns.verbose2 or ns.verbose3):
        parser.error("--pgo/-v don't go together!")
    if ns.pgo_extended:
        ns.pgo = True
    if ns.nowindows:
        print(
            "Warning: the --nowindows (-n) option is deprecated. Use -vv to display assertions in stderr.",
            file=sys.stderr,
        )
    if ns.quiet:
        ns.verbose = 0
    if ns.timeout is not None:
        if ns.timeout <= 0:
            ns.timeout = None
    if ns.use_mp is not None:
        if ns.use_mp <= 0:
            ns.use_mp = 2 + (os.cpu_count() or 1)
    if ns.use:
        for a in ns.use:
            for r in a:
                if r == "all":
                    ns.use_resources[:] = ALL_RESOURCES
                    continue
                if r == "none":
                    del ns.use_resources[:]
                    continue
                remove = False
                if r[0] == "-":
                    remove = True
                    r = r[1:]
                if remove:
                    if r in ns.use_resources:
                        ns.use_resources.remove(r)
                elif r not in ns.use_resources:
                    ns.use_resources.append(r)
    if ns.random_seed is not None:
        ns.randomize = True
    if ns.verbose:
        ns.header = True
    if ns.huntrleaks and ns.verbose3:
        ns.verbose3 = False
        print(
            "WARNING: Disable --verbose3 because it's incompatible with --huntrleaks: see http://bugs.python.org/issue27103",
            file=sys.stderr,
        )
    if ns.match_filename:
        if ns.match_tests is None:
            ns.match_tests = []
        with open(ns.match_filename) as fp:
            for line in fp:
                ns.match_tests.append(line.strip())
    if ns.ignore_filename:
        if ns.ignore_tests is None:
            ns.ignore_tests = []
        with open(ns.ignore_filename) as fp:
            for line in fp:
                ns.ignore_tests.append(line.strip())
    if ns.forever:
        ns.failfast = True
    return ns
