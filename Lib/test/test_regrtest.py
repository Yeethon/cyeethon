"\nTests of regrtest.py.\n\nNote: test_regrtest cannot be run twice in parallel.\n"
import contextlib
import glob
import io
import os.path
import platform
import re
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
import unittest
from test import libregrtest
from test import support
from test.support import os_helper
from test.libregrtest import utils

Py_DEBUG = hasattr(sys, "gettotalrefcount")
ROOT_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
ROOT_DIR = os.path.abspath(os.path.normpath(ROOT_DIR))
LOG_PREFIX = "[0-9]+:[0-9]+:[0-9]+ (?:load avg: [0-9]+\\.[0-9]{2} )?"
TEST_INTERRUPTED = textwrap.dedent(
    "\n    from signal import SIGINT, raise_signal\n    try:\n        raise_signal(SIGINT)\n    except ImportError:\n        import os\n        os.kill(os.getpid(), SIGINT)\n    "
)


class ParseArgsTestCase(unittest.TestCase):
    "\n    Test regrtest's argument parsing, function _parse_args().\n    "

    def checkError(self, args, msg):
        with support.captured_stderr() as err, self.assertRaises(SystemExit):
            libregrtest._parse_args(args)
        self.assertIn(msg, err.getvalue())

    def test_help(self):
        for opt in ("-h", "--help"):
            with self.subTest(opt=opt):
                with support.captured_stdout() as out, self.assertRaises(SystemExit):
                    libregrtest._parse_args([opt])
                self.assertIn("Run Python regression tests.", out.getvalue())

    def test_timeout(self):
        ns = libregrtest._parse_args(["--timeout", "4.2"])
        self.assertEqual(ns.timeout, 4.2)
        self.checkError(["--timeout"], "expected one argument")
        self.checkError(["--timeout", "foo"], "invalid float value")

    def test_wait(self):
        ns = libregrtest._parse_args(["--wait"])
        self.assertTrue(ns.wait)

    def test_worker_args(self):
        ns = libregrtest._parse_args(["--worker-args", "[[], {}]"])
        self.assertEqual(ns.worker_args, "[[], {}]")
        self.checkError(["--worker-args"], "expected one argument")

    def test_start(self):
        for opt in ("-S", "--start"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "foo"])
                self.assertEqual(ns.start, "foo")
                self.checkError([opt], "expected one argument")

    def test_verbose(self):
        ns = libregrtest._parse_args(["-v"])
        self.assertEqual(ns.verbose, 1)
        ns = libregrtest._parse_args(["-vvv"])
        self.assertEqual(ns.verbose, 3)
        ns = libregrtest._parse_args(["--verbose"])
        self.assertEqual(ns.verbose, 1)
        ns = libregrtest._parse_args((["--verbose"] * 3))
        self.assertEqual(ns.verbose, 3)
        ns = libregrtest._parse_args([])
        self.assertEqual(ns.verbose, 0)

    def test_verbose2(self):
        for opt in ("-w", "--verbose2"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.verbose2)

    def test_verbose3(self):
        for opt in ("-W", "--verbose3"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.verbose3)

    def test_quiet(self):
        for opt in ("-q", "--quiet"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.quiet)
                self.assertEqual(ns.verbose, 0)

    def test_slowest(self):
        for opt in ("-o", "--slowest"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.print_slow)

    def test_header(self):
        ns = libregrtest._parse_args(["--header"])
        self.assertTrue(ns.header)
        ns = libregrtest._parse_args(["--verbose"])
        self.assertTrue(ns.header)

    def test_randomize(self):
        for opt in ("-r", "--randomize"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.randomize)

    def test_randseed(self):
        ns = libregrtest._parse_args(["--randseed", "12345"])
        self.assertEqual(ns.random_seed, 12345)
        self.assertTrue(ns.randomize)
        self.checkError(["--randseed"], "expected one argument")
        self.checkError(["--randseed", "foo"], "invalid int value")

    def test_fromfile(self):
        for opt in ("-f", "--fromfile"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "foo"])
                self.assertEqual(ns.fromfile, "foo")
                self.checkError([opt], "expected one argument")
                self.checkError([opt, "foo", "-s"], "don't go together")

    def test_exclude(self):
        for opt in ("-x", "--exclude"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.exclude)

    def test_single(self):
        for opt in ("-s", "--single"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.single)
                self.checkError([opt, "-f", "foo"], "don't go together")

    def test_ignore(self):
        for opt in ("-i", "--ignore"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "pattern"])
                self.assertEqual(ns.ignore_tests, ["pattern"])
                self.checkError([opt], "expected one argument")
        self.addCleanup(os_helper.unlink, os_helper.TESTFN)
        with open(os_helper.TESTFN, "w") as fp:
            print("matchfile1", file=fp)
            print("matchfile2", file=fp)
        filename = os.path.abspath(os_helper.TESTFN)
        ns = libregrtest._parse_args(["-m", "match", "--ignorefile", filename])
        self.assertEqual(ns.ignore_tests, ["matchfile1", "matchfile2"])

    def test_match(self):
        for opt in ("-m", "--match"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "pattern"])
                self.assertEqual(ns.match_tests, ["pattern"])
                self.checkError([opt], "expected one argument")
        ns = libregrtest._parse_args(["-m", "pattern1", "-m", "pattern2"])
        self.assertEqual(ns.match_tests, ["pattern1", "pattern2"])
        self.addCleanup(os_helper.unlink, os_helper.TESTFN)
        with open(os_helper.TESTFN, "w") as fp:
            print("matchfile1", file=fp)
            print("matchfile2", file=fp)
        filename = os.path.abspath(os_helper.TESTFN)
        ns = libregrtest._parse_args(["-m", "match", "--matchfile", filename])
        self.assertEqual(ns.match_tests, ["match", "matchfile1", "matchfile2"])

    def test_failfast(self):
        for opt in ("-G", "--failfast"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "-v"])
                self.assertTrue(ns.failfast)
                ns = libregrtest._parse_args([opt, "-W"])
                self.assertTrue(ns.failfast)
                self.checkError([opt], "-G/--failfast needs either -v or -W")

    def test_use(self):
        for opt in ("-u", "--use"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "gui,network"])
                self.assertEqual(ns.use_resources, ["gui", "network"])
                ns = libregrtest._parse_args([opt, "gui,none,network"])
                self.assertEqual(ns.use_resources, ["network"])
                expected = list(libregrtest.ALL_RESOURCES)
                expected.remove("gui")
                ns = libregrtest._parse_args([opt, "all,-gui"])
                self.assertEqual(ns.use_resources, expected)
                self.checkError([opt], "expected one argument")
                self.checkError([opt, "foo"], "invalid resource")
                ns = libregrtest._parse_args([opt, "all,tzdata"])
                self.assertEqual(
                    ns.use_resources, (list(libregrtest.ALL_RESOURCES) + ["tzdata"])
                )
                ns = libregrtest._parse_args([opt, "extralargefile"])
                self.assertEqual(ns.use_resources, ["extralargefile"])

    def test_memlimit(self):
        for opt in ("-M", "--memlimit"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "4G"])
                self.assertEqual(ns.memlimit, "4G")
                self.checkError([opt], "expected one argument")

    def test_testdir(self):
        ns = libregrtest._parse_args(["--testdir", "foo"])
        self.assertEqual(ns.testdir, os.path.join(os_helper.SAVEDCWD, "foo"))
        self.checkError(["--testdir"], "expected one argument")

    def test_runleaks(self):
        for opt in ("-L", "--runleaks"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.runleaks)

    def test_huntrleaks(self):
        for opt in ("-R", "--huntrleaks"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, ":"])
                self.assertEqual(ns.huntrleaks, (5, 4, "reflog.txt"))
                ns = libregrtest._parse_args([opt, "6:"])
                self.assertEqual(ns.huntrleaks, (6, 4, "reflog.txt"))
                ns = libregrtest._parse_args([opt, ":3"])
                self.assertEqual(ns.huntrleaks, (5, 3, "reflog.txt"))
                ns = libregrtest._parse_args([opt, "6:3:leaks.log"])
                self.assertEqual(ns.huntrleaks, (6, 3, "leaks.log"))
                self.checkError([opt], "expected one argument")
                self.checkError([opt, "6"], "needs 2 or 3 colon-separated arguments")
                self.checkError([opt, "foo:"], "invalid huntrleaks value")
                self.checkError([opt, "6:foo"], "invalid huntrleaks value")

    def test_multiprocess(self):
        for opt in ("-j", "--multiprocess"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "2"])
                self.assertEqual(ns.use_mp, 2)
                self.checkError([opt], "expected one argument")
                self.checkError([opt, "foo"], "invalid int value")
                self.checkError([opt, "2", "-T"], "don't go together")
                self.checkError([opt, "0", "-T"], "don't go together")

    def test_coverage(self):
        for opt in ("-T", "--coverage"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.trace)

    def test_coverdir(self):
        for opt in ("-D", "--coverdir"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "foo"])
                self.assertEqual(ns.coverdir, os.path.join(os_helper.SAVEDCWD, "foo"))
                self.checkError([opt], "expected one argument")

    def test_nocoverdir(self):
        for opt in ("-N", "--nocoverdir"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertIsNone(ns.coverdir)

    def test_threshold(self):
        for opt in ("-t", "--threshold"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt, "1000"])
                self.assertEqual(ns.threshold, 1000)
                self.checkError([opt], "expected one argument")
                self.checkError([opt, "foo"], "invalid int value")

    def test_nowindows(self):
        for opt in ("-n", "--nowindows"):
            with self.subTest(opt=opt):
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.nowindows)
                err = stderr.getvalue()
                self.assertIn("the --nowindows (-n) option is deprecated", err)

    def test_forever(self):
        for opt in ("-F", "--forever"):
            with self.subTest(opt=opt):
                ns = libregrtest._parse_args([opt])
                self.assertTrue(ns.forever)

    def test_unrecognized_argument(self):
        self.checkError(["--xxx"], "usage:")

    def test_long_option__partial(self):
        ns = libregrtest._parse_args(["--qui"])
        self.assertTrue(ns.quiet)
        self.assertEqual(ns.verbose, 0)

    def test_two_options(self):
        ns = libregrtest._parse_args(["--quiet", "--exclude"])
        self.assertTrue(ns.quiet)
        self.assertEqual(ns.verbose, 0)
        self.assertTrue(ns.exclude)

    def test_option_with_empty_string_value(self):
        ns = libregrtest._parse_args(["--start", ""])
        self.assertEqual(ns.start, "")

    def test_arg(self):
        ns = libregrtest._parse_args(["foo"])
        self.assertEqual(ns.args, ["foo"])

    def test_option_and_arg(self):
        ns = libregrtest._parse_args(["--quiet", "foo"])
        self.assertTrue(ns.quiet)
        self.assertEqual(ns.verbose, 0)
        self.assertEqual(ns.args, ["foo"])

    def test_arg_option_arg(self):
        ns = libregrtest._parse_args(["test_unaryop", "-v", "test_binop"])
        self.assertEqual(ns.verbose, 1)
        self.assertEqual(ns.args, ["test_unaryop", "test_binop"])

    def test_unknown_option(self):
        self.checkError(
            ["--unknown-option"], "unrecognized arguments: --unknown-option"
        )


class BaseTestCase(unittest.TestCase):
    TEST_UNIQUE_ID = 1
    TESTNAME_PREFIX = "test_regrtest_"
    TESTNAME_REGEX = "test_[a-zA-Z0-9_]+"

    def setUp(self):
        self.testdir = os.path.realpath(os.path.dirname(__file__))
        self.tmptestdir = tempfile.mkdtemp()
        self.addCleanup(os_helper.rmtree, self.tmptestdir)

    def create_test(self, name=None, code=None):
        if not name:
            name = "noop%s" % BaseTestCase.TEST_UNIQUE_ID
            BaseTestCase.TEST_UNIQUE_ID += 1
        if code is None:
            code = textwrap.dedent(
                "\n                    import unittest\n\n                    class Tests(unittest.TestCase):\n                        def test_empty_test(self):\n                            pass\n                "
            )
        name = self.TESTNAME_PREFIX + name
        path = os.path.join(self.tmptestdir, (name + ".py"))
        self.addCleanup(os_helper.unlink, path)
        try:
            with open(path, "x", encoding="utf-8") as fp:
                fp.write(code)
        except PermissionError as exc:
            if not sysconfig.is_python_build():
                self.skipTest(("cannot write %s: %s" % (path, exc)))
            raise
        return name

    def regex_search(self, regex, output):
        match = re.search(regex, output, re.MULTILINE)
        if not match:
            self.fail(("%r not found in %r" % (regex, output)))
        return match

    def check_line(self, output, regex):
        regex = re.compile(("^" + regex), re.MULTILINE)
        self.assertRegex(output, regex)

    def parse_executed_tests(self, output):
        regex = "^%s\\[ *[0-9]+(?:/ *[0-9]+)*\\] (%s)" % (
            LOG_PREFIX,
            self.TESTNAME_REGEX,
        )
        parser = re.finditer(regex, output, re.MULTILINE)
        return list((match.group(1) for match in parser))

    def check_executed_tests(
        self,
        output,
        tests,
        skipped=(),
        failed=(),
        env_changed=(),
        omitted=(),
        rerun=(),
        no_test_ran=(),
        randomize=False,
        interrupted=False,
        fail_env_changed=False,
    ):
        if isinstance(tests, str):
            tests = [tests]
        if isinstance(skipped, str):
            skipped = [skipped]
        if isinstance(failed, str):
            failed = [failed]
        if isinstance(env_changed, str):
            env_changed = [env_changed]
        if isinstance(omitted, str):
            omitted = [omitted]
        if isinstance(rerun, str):
            rerun = [rerun]
        if isinstance(no_test_ran, str):
            no_test_ran = [no_test_ran]
        executed = self.parse_executed_tests(output)
        if randomize:
            self.assertEqual(set(executed), set(tests), output)
        else:
            self.assertEqual(executed, tests, output)

        def plural(count):
            return "s" if (count != 1) else ""

        def list_regex(line_format, tests):
            count = len(tests)
            names = " ".join(sorted(tests))
            regex = line_format % (count, plural(count))
            regex = "%s:\\n    %s$" % (regex, names)
            return regex

        if skipped:
            regex = list_regex("%s test%s skipped", skipped)
            self.check_line(output, regex)
        if failed:
            regex = list_regex("%s test%s failed", failed)
            self.check_line(output, regex)
        if env_changed:
            regex = list_regex(
                "%s test%s altered the execution environment", env_changed
            )
            self.check_line(output, regex)
        if omitted:
            regex = list_regex("%s test%s omitted", omitted)
            self.check_line(output, regex)
        if rerun:
            regex = list_regex("%s re-run test%s", rerun)
            self.check_line(output, regex)
            regex = LOG_PREFIX + "Re-running failed tests in verbose mode"
            self.check_line(output, regex)
            for test_name in rerun:
                regex = LOG_PREFIX + f"Re-running {test_name} in verbose mode"
                self.check_line(output, regex)
        if no_test_ran:
            regex = list_regex("%s test%s run no tests", no_test_ran)
            self.check_line(output, regex)
        good = (
            (((len(tests) - len(skipped)) - len(failed)) - len(omitted))
            - len(env_changed)
        ) - len(no_test_ran)
        if good:
            regex = "%s test%s OK\\.$" % (good, plural(good))
            if (not skipped) and (not failed) and (good > 1):
                regex = "All %s" % regex
            self.check_line(output, regex)
        if interrupted:
            self.check_line(output, "Test suite interrupted by signal SIGINT.")
        result = []
        if failed:
            result.append("FAILURE")
        elif fail_env_changed and env_changed:
            result.append("ENV CHANGED")
        if interrupted:
            result.append("INTERRUPTED")
        if not any(
            (good, result, failed, interrupted, skipped, env_changed, fail_env_changed)
        ):
            result.append("NO TEST RUN")
        elif not result:
            result.append("SUCCESS")
        result = ", ".join(result)
        if rerun:
            self.check_line(output, "Tests result: FAILURE")
            result = "FAILURE then %s" % result
        self.check_line(output, ("Tests result: %s" % result))

    def parse_random_seed(self, output):
        match = self.regex_search("Using random seed ([0-9]+)", output)
        randseed = int(match.group(1))
        self.assertTrue((0 <= randseed <= 10000000), randseed)
        return randseed

    def run_command(self, args, input=None, exitcode=0, **kw):
        if not input:
            input = ""
        if "stderr" not in kw:
            kw["stderr"] = subprocess.STDOUT
        proc = subprocess.run(
            args, universal_newlines=True, input=input, stdout=subprocess.PIPE, **kw
        )
        if proc.returncode != exitcode:
            msg = "Command %s failed with exit code %s\n\nstdout:\n---\n%s\n---\n" % (
                str(args),
                proc.returncode,
                proc.stdout,
            )
            if proc.stderr:
                msg += "\nstderr:\n---\n%s---\n" % proc.stderr
            self.fail(msg)
        return proc

    def run_python(self, args, **kw):
        args = [sys.executable, "-X", "faulthandler", "-I", *args]
        proc = self.run_command(args, **kw)
        return proc.stdout


class CheckActualTests(BaseTestCase):
    "\n    Check that regrtest appears to find the expected set of tests.\n    "

    def test_finds_expected_number_of_tests(self):
        args = ["-Wd", "-E", "-bb", "-m", "test.regrtest", "--list-tests"]
        output = self.run_python(args)
        rough_number_of_tests_found = len(output.splitlines())
        actual_testsuite_glob = os.path.join(
            glob.escape(os.path.dirname(__file__)), "test*.py"
        )
        rough_counted_test_py_files = len(glob.glob(actual_testsuite_glob))
        self.assertGreater(
            rough_number_of_tests_found,
            ((rough_counted_test_py_files * 9) // 10),
            msg=f"""Unexpectedly low number of tests found in:
{', '.join(output.splitlines())}""",
        )


class ProgramsTestCase(BaseTestCase):
    "\n    Test various ways to run the Python test suite. Use options close\n    to options used on the buildbot.\n    "
    NTEST = 4

    def setUp(self):
        super().setUp()
        self.tests = [self.create_test() for index in range(self.NTEST)]
        self.python_args = ["-Wd", "-E", "-bb"]
        self.regrtest_args = ["-uall", "-rwW", ("--testdir=%s" % self.tmptestdir)]
        self.regrtest_args.extend(("--timeout", "3600", "-j4"))
        if sys.platform == "win32":
            self.regrtest_args.append("-n")

    def check_output(self, output):
        self.parse_random_seed(output)
        self.check_executed_tests(output, self.tests, randomize=True)

    def run_tests(self, args):
        output = self.run_python(args)
        self.check_output(output)

    def test_script_regrtest(self):
        script = os.path.join(self.testdir, "regrtest.py")
        args = [*self.python_args, script, *self.regrtest_args, *self.tests]
        self.run_tests(args)

    def test_module_test(self):
        args = [*self.python_args, "-m", "test", *self.regrtest_args, *self.tests]
        self.run_tests(args)

    def test_module_regrtest(self):
        args = [
            *self.python_args,
            "-m",
            "test.regrtest",
            *self.regrtest_args,
            *self.tests,
        ]
        self.run_tests(args)

    def test_module_autotest(self):
        args = [
            *self.python_args,
            "-m",
            "test.autotest",
            *self.regrtest_args,
            *self.tests,
        ]
        self.run_tests(args)

    def test_module_from_test_autotest(self):
        code = "from test import autotest"
        args = [*self.python_args, "-c", code, *self.regrtest_args, *self.tests]
        self.run_tests(args)

    def test_script_autotest(self):
        script = os.path.join(self.testdir, "autotest.py")
        args = [*self.python_args, script, *self.regrtest_args, *self.tests]
        self.run_tests(args)

    @unittest.skipUnless(
        sysconfig.is_python_build(), "run_tests.py script is not installed"
    )
    def test_tools_script_run_tests(self):
        script = os.path.join(ROOT_DIR, "Tools", "scripts", "run_tests.py")
        args = [script, *self.regrtest_args, *self.tests]
        self.run_tests(args)

    def run_batch(self, *args):
        proc = self.run_command(args)
        self.check_output(proc.stdout)

    @unittest.skipUnless(
        sysconfig.is_python_build(), "test.bat script is not installed"
    )
    @unittest.skipUnless((sys.platform == "win32"), "Windows only")
    def test_tools_buildbot_test(self):
        script = os.path.join(ROOT_DIR, "Tools", "buildbot", "test.bat")
        test_args = [("--testdir=%s" % self.tmptestdir)]
        if platform.machine() == "ARM64":
            test_args.append("-arm64")
        elif platform.machine() == "ARM":
            test_args.append("-arm32")
        elif platform.architecture()[0] == "64bit":
            test_args.append("-x64")
        if not Py_DEBUG:
            test_args.append("+d")
        self.run_batch(script, *test_args, *self.tests)

    @unittest.skipUnless((sys.platform == "win32"), "Windows only")
    def test_pcbuild_rt(self):
        script = os.path.join(ROOT_DIR, "PCbuild\\rt.bat")
        if not os.path.isfile(script):
            self.skipTest(f'File "{script}" does not exist')
        rt_args = ["-q"]
        if platform.machine() == "ARM64":
            rt_args.append("-arm64")
        elif platform.machine() == "ARM":
            rt_args.append("-arm32")
        elif platform.architecture()[0] == "64bit":
            rt_args.append("-x64")
        if Py_DEBUG:
            rt_args.append("-d")
        self.run_batch(script, *rt_args, *self.regrtest_args, *self.tests)


class ArgsTestCase(BaseTestCase):
    "\n    Test arguments of the Python test suite.\n    "

    def run_tests(self, *testargs, **kw):
        cmdargs = ["-m", "test", ("--testdir=%s" % self.tmptestdir), *testargs]
        return self.run_python(cmdargs, **kw)

    def test_failing_test(self):
        code = textwrap.dedent(
            '\n            import unittest\n\n            class FailingTest(unittest.TestCase):\n                def test_failing(self):\n                    self.fail("bug")\n        '
        )
        test_ok = self.create_test("ok")
        test_failing = self.create_test("failing", code=code)
        tests = [test_ok, test_failing]
        output = self.run_tests(*tests, exitcode=2)
        self.check_executed_tests(output, tests, failed=test_failing)

    def test_resources(self):
        tests = {}
        for resource in ("audio", "network"):
            code = textwrap.dedent(
                (
                    "\n                        from test import support; support.requires(%r)\n                        import unittest\n                        class PassingTest(unittest.TestCase):\n                            def test_pass(self):\n                                pass\n                    "
                    % resource
                )
            )
            tests[resource] = self.create_test(resource, code)
        test_names = sorted(tests.values())
        output = self.run_tests("-u", "all", *test_names)
        self.check_executed_tests(output, test_names)
        output = self.run_tests("-uaudio", *test_names)
        self.check_executed_tests(output, test_names, skipped=tests["network"])
        output = self.run_tests(*test_names)
        self.check_executed_tests(output, test_names, skipped=test_names)

    def test_random(self):
        code = textwrap.dedent(
            '\n            import random\n            print("TESTRANDOM: %s" % random.randint(1, 1000))\n        '
        )
        test = self.create_test("random", code)
        output = self.run_tests("-r", test)
        randseed = self.parse_random_seed(output)
        match = self.regex_search("TESTRANDOM: ([0-9]+)", output)
        test_random = int(match.group(1))
        output = self.run_tests("-r", ("--randseed=%s" % randseed), test)
        randseed2 = self.parse_random_seed(output)
        self.assertEqual(randseed2, randseed)
        match = self.regex_search("TESTRANDOM: ([0-9]+)", output)
        test_random2 = int(match.group(1))
        self.assertEqual(test_random2, test_random)

    def test_fromfile(self):
        tests = [self.create_test() for index in range(5)]
        filename = os_helper.TESTFN
        self.addCleanup(os_helper.unlink, filename)
        with open(filename, "w") as fp:
            previous = None
            for (index, name) in enumerate(tests, 1):
                line = "00:00:%02i [%s/%s] %s" % (index, index, len(tests), name)
                if previous:
                    line += " -- %s took 0 sec" % previous
                print(line, file=fp)
                previous = name
        output = self.run_tests("--fromfile", filename)
        self.check_executed_tests(output, tests)
        with open(filename, "w") as fp:
            for (index, name) in enumerate(tests, 1):
                print(("[%s/%s] %s" % (index, len(tests), name)), file=fp)
        output = self.run_tests("--fromfile", filename)
        self.check_executed_tests(output, tests)
        with open(filename, "w") as fp:
            for name in tests:
                print(name, file=fp)
        output = self.run_tests("--fromfile", filename)
        self.check_executed_tests(output, tests)
        with open(filename, "w") as fp:
            for name in tests:
                print(("Lib/test/%s.py" % name), file=fp)
        output = self.run_tests("--fromfile", filename)
        self.check_executed_tests(output, tests)

    def test_interrupted(self):
        code = TEST_INTERRUPTED
        test = self.create_test("sigint", code=code)
        output = self.run_tests(test, exitcode=130)
        self.check_executed_tests(output, test, omitted=test, interrupted=True)

    def test_slowest(self):
        tests = [self.create_test() for index in range(3)]
        output = self.run_tests("--slowest", *tests)
        self.check_executed_tests(output, tests)
        regex = "10 slowest tests:\n(?:- %s: .*\n){%s}" % (
            self.TESTNAME_REGEX,
            len(tests),
        )
        self.check_line(output, regex)

    def test_slowest_interrupted(self):
        code = TEST_INTERRUPTED
        test = self.create_test("sigint", code=code)
        for multiprocessing in (False, True):
            with self.subTest(multiprocessing=multiprocessing):
                if multiprocessing:
                    args = ("--slowest", "-j2", test)
                else:
                    args = ("--slowest", test)
                output = self.run_tests(*args, exitcode=130)
                self.check_executed_tests(output, test, omitted=test, interrupted=True)
                regex = "10 slowest tests:\n"
                self.check_line(output, regex)

    def test_coverage(self):
        test = self.create_test("coverage")
        output = self.run_tests("--coverage", test)
        self.check_executed_tests(output, [test])
        regex = "lines +cov% +module +\\(path\\)\\n(?: *[0-9]+ *[0-9]{1,2}% *[^ ]+ +\\([^)]+\\)+)+"
        self.check_line(output, regex)

    def test_wait(self):
        test = self.create_test("wait")
        output = self.run_tests("--wait", test, input="key")
        self.check_line(output, "Press any key to continue")

    def test_forever(self):
        code = textwrap.dedent(
            "\n            import builtins\n            import unittest\n\n            class ForeverTester(unittest.TestCase):\n                def test_run(self):\n                    # Store the state in the builtins module, because the test\n                    # module is reload at each run\n                    if 'RUN' in builtins.__dict__:\n                        builtins.__dict__['RUN'] += 1\n                        if builtins.__dict__['RUN'] >= 3:\n                            self.fail(\"fail at the 3rd runs\")\n                    else:\n                        builtins.__dict__['RUN'] = 1\n        "
        )
        test = self.create_test("forever", code=code)
        output = self.run_tests("--forever", test, exitcode=2)
        self.check_executed_tests(output, ([test] * 3), failed=test)

    def check_leak(self, code, what):
        test = self.create_test("huntrleaks", code=code)
        filename = "reflog.txt"
        self.addCleanup(os_helper.unlink, filename)
        output = self.run_tests(
            "--huntrleaks", "3:3:", test, exitcode=2, stderr=subprocess.STDOUT
        )
        self.check_executed_tests(output, [test], failed=test)
        line = "beginning 6 repetitions\n123456\n......\n"
        self.check_line(output, re.escape(line))
        line2 = "%s leaked [1, 1, 1] %s, sum=3\n" % (test, what)
        self.assertIn(line2, output)
        with open(filename) as fp:
            reflog = fp.read()
            self.assertIn(line2, reflog)

    @unittest.skipUnless(Py_DEBUG, "need a debug build")
    def test_huntrleaks(self):
        code = textwrap.dedent(
            "\n            import unittest\n\n            GLOBAL_LIST = []\n\n            class RefLeakTest(unittest.TestCase):\n                def test_leak(self):\n                    GLOBAL_LIST.append(object())\n        "
        )
        self.check_leak(code, "references")

    @unittest.skipUnless(Py_DEBUG, "need a debug build")
    def test_huntrleaks_fd_leak(self):
        code = textwrap.dedent(
            "\n            import os\n            import unittest\n\n            class FDLeakTest(unittest.TestCase):\n                def test_leak(self):\n                    fd = os.open(__file__, os.O_RDONLY)\n                    # bug: never close the file descriptor\n        "
        )
        self.check_leak(code, "file descriptors")

    def test_list_tests(self):
        tests = [self.create_test() for i in range(5)]
        output = self.run_tests("--list-tests", *tests)
        self.assertEqual(output.rstrip().splitlines(), tests)

    def test_list_cases(self):
        code = textwrap.dedent(
            "\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_method1(self):\n                    pass\n                def test_method2(self):\n                    pass\n        "
        )
        testname = self.create_test(code=code)
        all_methods = [
            ("%s.Tests.test_method1" % testname),
            ("%s.Tests.test_method2" % testname),
        ]
        output = self.run_tests("--list-cases", testname)
        self.assertEqual(output.splitlines(), all_methods)
        all_methods = [("%s.Tests.test_method1" % testname)]
        output = self.run_tests("--list-cases", "-m", "test_method1", testname)
        self.assertEqual(output.splitlines(), all_methods)

    @support.cpython_only
    def test_crashed(self):
        code = "import faulthandler; faulthandler._sigsegv()"
        crash_test = self.create_test(name="crash", code=code)
        tests = [crash_test]
        output = self.run_tests("-j2", *tests, exitcode=2)
        self.check_executed_tests(output, tests, failed=crash_test, randomize=True)

    def parse_methods(self, output):
        regex = re.compile("^(test[^ ]+).*ok$", flags=re.MULTILINE)
        return [match.group(1) for match in regex.finditer(output)]

    def test_ignorefile(self):
        code = textwrap.dedent(
            "\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_method1(self):\n                    pass\n                def test_method2(self):\n                    pass\n                def test_method3(self):\n                    pass\n                def test_method4(self):\n                    pass\n        "
        )
        all_methods = ["test_method1", "test_method2", "test_method3", "test_method4"]
        testname = self.create_test(code=code)
        filename = os_helper.TESTFN
        self.addCleanup(os_helper.unlink, filename)
        subset = ["test_method1", ("%s.Tests.test_method3" % testname)]
        with open(filename, "w") as fp:
            for name in subset:
                print(name, file=fp)
        output = self.run_tests("-v", "--ignorefile", filename, testname)
        methods = self.parse_methods(output)
        subset = ["test_method2", "test_method4"]
        self.assertEqual(methods, subset)

    def test_matchfile(self):
        code = textwrap.dedent(
            "\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_method1(self):\n                    pass\n                def test_method2(self):\n                    pass\n                def test_method3(self):\n                    pass\n                def test_method4(self):\n                    pass\n        "
        )
        all_methods = ["test_method1", "test_method2", "test_method3", "test_method4"]
        testname = self.create_test(code=code)
        output = self.run_tests("-v", testname)
        methods = self.parse_methods(output)
        self.assertEqual(methods, all_methods)
        filename = os_helper.TESTFN
        self.addCleanup(os_helper.unlink, filename)
        subset = ["test_method1", ("%s.Tests.test_method3" % testname)]
        with open(filename, "w") as fp:
            for name in subset:
                print(name, file=fp)
        output = self.run_tests("-v", "--matchfile", filename, testname)
        methods = self.parse_methods(output)
        subset = ["test_method1", "test_method3"]
        self.assertEqual(methods, subset)

    def test_env_changed(self):
        code = textwrap.dedent(
            '\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_env_changed(self):\n                    open("env_changed", "w").close()\n        '
        )
        testname = self.create_test(code=code)
        output = self.run_tests(testname)
        self.check_executed_tests(output, [testname], env_changed=testname)
        output = self.run_tests("--fail-env-changed", testname, exitcode=3)
        self.check_executed_tests(
            output, [testname], env_changed=testname, fail_env_changed=True
        )

    def test_rerun_fail(self):
        code = textwrap.dedent(
            '\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_bug(self):\n                    # test always fail\n                    self.fail("bug")\n        '
        )
        testname = self.create_test(code=code)
        output = self.run_tests("-w", testname, exitcode=2)
        self.check_executed_tests(output, [testname], failed=testname, rerun=testname)

    def test_rerun_success(self):
        code = textwrap.dedent(
            "\n            import builtins\n            import unittest\n\n            class Tests(unittest.TestCase):\n                failed = False\n\n                def test_fail_once(self):\n                    if not hasattr(builtins, '_test_failed'):\n                        builtins._test_failed = True\n                        self.fail(\"bug\")\n        "
        )
        testname = self.create_test(code=code)
        output = self.run_tests("-w", testname, exitcode=0)
        self.check_executed_tests(output, [testname], rerun=testname)

    def test_no_tests_ran(self):
        code = textwrap.dedent(
            "\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_bug(self):\n                    pass\n        "
        )
        testname = self.create_test(code=code)
        output = self.run_tests(testname, "-m", "nosuchtest", exitcode=0)
        self.check_executed_tests(output, [testname], no_test_ran=testname)

    def test_no_tests_ran_skip(self):
        code = textwrap.dedent(
            '\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_skipped(self):\n                    self.skipTest("because")\n        '
        )
        testname = self.create_test(code=code)
        output = self.run_tests(testname, exitcode=0)
        self.check_executed_tests(output, [testname])

    def test_no_tests_ran_multiple_tests_nonexistent(self):
        code = textwrap.dedent(
            "\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_bug(self):\n                    pass\n        "
        )
        testname = self.create_test(code=code)
        testname2 = self.create_test(code=code)
        output = self.run_tests(testname, testname2, "-m", "nosuchtest", exitcode=0)
        self.check_executed_tests(
            output, [testname, testname2], no_test_ran=[testname, testname2]
        )

    def test_no_test_ran_some_test_exist_some_not(self):
        code = textwrap.dedent(
            "\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_bug(self):\n                    pass\n        "
        )
        testname = self.create_test(code=code)
        other_code = textwrap.dedent(
            "\n            import unittest\n\n            class Tests(unittest.TestCase):\n                def test_other_bug(self):\n                    pass\n        "
        )
        testname2 = self.create_test(code=other_code)
        output = self.run_tests(
            testname, testname2, "-m", "nosuchtest", "-m", "test_other_bug", exitcode=0
        )
        self.check_executed_tests(output, [testname, testname2], no_test_ran=[testname])

    @support.cpython_only
    def test_findleaks(self):
        code = textwrap.dedent(
            "\n            import _testcapi\n            import gc\n            import unittest\n\n            @_testcapi.with_tp_del\n            class Garbage:\n                def __tp_del__(self):\n                    pass\n\n            class Tests(unittest.TestCase):\n                def test_garbage(self):\n                    # create an uncollectable object\n                    obj = Garbage()\n                    obj.ref_cycle = obj\n                    obj = None\n        "
        )
        testname = self.create_test(code=code)
        output = self.run_tests("--fail-env-changed", testname, exitcode=3)
        self.check_executed_tests(
            output, [testname], env_changed=[testname], fail_env_changed=True
        )
        output = self.run_tests("--findleaks", testname, exitcode=3)
        self.check_executed_tests(
            output, [testname], env_changed=[testname], fail_env_changed=True
        )

    def test_multiprocessing_timeout(self):
        code = textwrap.dedent(
            "\n            import time\n            import unittest\n            try:\n                import faulthandler\n            except ImportError:\n                faulthandler = None\n\n            class Tests(unittest.TestCase):\n                # test hangs and so should be stopped by the timeout\n                def test_sleep(self):\n                    # we want to test regrtest multiprocessing timeout,\n                    # not faulthandler timeout\n                    if faulthandler is not None:\n                        faulthandler.cancel_dump_traceback_later()\n\n                    time.sleep(60 * 5)\n        "
        )
        testname = self.create_test(code=code)
        output = self.run_tests("-j2", "--timeout=1.0", testname, exitcode=2)
        self.check_executed_tests(output, [testname], failed=testname)
        self.assertRegex(output, re.compile(("%s timed out" % testname), re.MULTILINE))

    def test_unraisable_exc(self):
        code = textwrap.dedent(
            "\n            import unittest\n            import weakref\n            from test.support import captured_stderr\n\n            class MyObject:\n                pass\n\n            def weakref_callback(obj):\n                raise Exception(\"weakref callback bug\")\n\n            class Tests(unittest.TestCase):\n                def test_unraisable_exc(self):\n                    obj = MyObject()\n                    ref = weakref.ref(obj, weakref_callback)\n                    with captured_stderr() as stderr:\n                        # call weakref_callback() which logs\n                        # an unraisable exception\n                        obj = None\n                    self.assertEqual(stderr.getvalue(), '')\n        "
        )
        testname = self.create_test(code=code)
        output = self.run_tests("--fail-env-changed", "-v", testname, exitcode=3)
        self.check_executed_tests(
            output, [testname], env_changed=[testname], fail_env_changed=True
        )
        self.assertIn("Warning -- Unraisable exception", output)
        self.assertIn("Exception: weakref callback bug", output)

    def test_threading_excepthook(self):
        code = textwrap.dedent(
            "\n            import threading\n            import unittest\n            from test.support import captured_stderr\n\n            class MyObject:\n                pass\n\n            def func_bug():\n                raise Exception(\"bug in thread\")\n\n            class Tests(unittest.TestCase):\n                def test_threading_excepthook(self):\n                    with captured_stderr() as stderr:\n                        thread = threading.Thread(target=func_bug)\n                        thread.start()\n                        thread.join()\n                    self.assertEqual(stderr.getvalue(), '')\n        "
        )
        testname = self.create_test(code=code)
        output = self.run_tests("--fail-env-changed", "-v", testname, exitcode=3)
        self.check_executed_tests(
            output, [testname], env_changed=[testname], fail_env_changed=True
        )
        self.assertIn("Warning -- Uncaught thread exception", output)
        self.assertIn("Exception: bug in thread", output)

    def test_cleanup(self):
        dirname = os.path.join(self.tmptestdir, "test_python_123")
        os.mkdir(dirname)
        filename = os.path.join(self.tmptestdir, "test_python_456")
        open(filename, "wb").close()
        names = [dirname, filename]
        cmdargs = ["-m", "test", ("--tempdir=%s" % self.tmptestdir), "--cleanup"]
        self.run_python(cmdargs)
        for name in names:
            self.assertFalse(os.path.exists(name), name)


class TestUtils(unittest.TestCase):
    def test_format_duration(self):
        self.assertEqual(utils.format_duration(0), "0 ms")
        self.assertEqual(utils.format_duration(1e-09), "1 ms")
        self.assertEqual(utils.format_duration(0.01), "10 ms")
        self.assertEqual(utils.format_duration(1.5), "1.5 sec")
        self.assertEqual(utils.format_duration(1), "1.0 sec")
        self.assertEqual(utils.format_duration((2 * 60)), "2 min")
        self.assertEqual(utils.format_duration(((2 * 60) + 1)), "2 min 1 sec")
        self.assertEqual(utils.format_duration((3 * 3600)), "3 hour")
        self.assertEqual(
            utils.format_duration((((3 * 3600) + (2 * 60)) + 1)), "3 hour 2 min"
        )
        self.assertEqual(utils.format_duration(((3 * 3600) + 1)), "3 hour 1 sec")


if __name__ == "__main__":
    unittest.main()
