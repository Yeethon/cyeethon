import collections
import faulthandler
import functools
import gc
import importlib
import io
import os
import sys
import time
import traceback
import unittest
from test import support
from test.support import os_helper
from test.libregrtest.utils import clear_caches
from test.libregrtest.save_env import saved_test_environment
from test.libregrtest.utils import format_duration, print_warning

PASSED = 1
FAILED = 0
ENV_CHANGED = -1
SKIPPED = -2
RESOURCE_DENIED = -3
INTERRUPTED = -4
CHILD_ERROR = -5
TEST_DID_NOT_RUN = -6
TIMEOUT = -7
_FORMAT_TEST_RESULT = {
    PASSED: "%s passed",
    FAILED: "%s failed",
    ENV_CHANGED: "%s failed (env changed)",
    SKIPPED: "%s skipped",
    RESOURCE_DENIED: "%s skipped (resource denied)",
    INTERRUPTED: "%s interrupted",
    CHILD_ERROR: "%s crashed",
    TEST_DID_NOT_RUN: "%s run no tests",
    TIMEOUT: "%s timed out",
}
PROGRESS_MIN_TIME = 30.0
STDTESTS = [
    "test_grammar",
    "test_opcodes",
    "test_dict",
    "test_builtin",
    "test_exceptions",
    "test_types",
    "test_unittest",
    "test_doctest",
    "test_doctest2",
    "test_support",
]
NOTTESTS = set()
FOUND_GARBAGE = []


def is_failed(result, ns):
    ok = result.result
    if ok in (PASSED, RESOURCE_DENIED, SKIPPED, TEST_DID_NOT_RUN):
        return False
    if ok == ENV_CHANGED:
        return ns.fail_env_changed
    return True


def format_test_result(result):
    fmt = _FORMAT_TEST_RESULT.get(result.result, "%s")
    text = fmt % result.test_name
    if result.result == TIMEOUT:
        text = "%s (%s)" % (text, format_duration(result.test_time))
    return text


def findtestdir(path=None):
    return path or os.path.dirname(os.path.dirname(__file__)) or os.curdir


def findtests(testdir=None, stdtests=STDTESTS, nottests=NOTTESTS):
    "Return a list of all applicable test modules."
    testdir = findtestdir(testdir)
    names = os.listdir(testdir)
    tests = []
    others = set(stdtests) | nottests
    for name in names:
        (mod, ext) = os.path.splitext(name)
        if (mod[:5] == "test_") and (ext in (".py", "")) and (mod not in others):
            tests.append(mod)
    return stdtests + sorted(tests)


def get_abs_module(ns, test_name):
    if test_name.startswith("test.") or ns.testdir:
        return test_name
    else:
        return "test." + test_name


TestResult = collections.namedtuple("TestResult", "test_name result test_time xml_data")


def _runtest(ns, test_name):
    output_on_failure = ns.verbose3
    use_timeout = ns.timeout is not None
    if use_timeout:
        faulthandler.dump_traceback_later(ns.timeout, exit=True)
    start_time = time.perf_counter()
    try:
        support.set_match_tests(ns.match_tests, ns.ignore_tests)
        support.junit_xml_list = xml_list = [] if ns.xmlpath else None
        if ns.failfast:
            support.failfast = True
        if output_on_failure:
            support.verbose = True
            stream = io.StringIO()
            orig_stdout = sys.stdout
            orig_stderr = sys.stderr
            try:
                sys.stdout = stream
                sys.stderr = stream
                result = _runtest_inner(ns, test_name, display_failure=False)
                if result != PASSED:
                    output = stream.getvalue()
                    orig_stderr.write(output)
                    orig_stderr.flush()
            finally:
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
        else:
            support.verbose = ns.verbose
            result = _runtest_inner(ns, test_name, display_failure=(not ns.verbose))
        if xml_list:
            import xml.etree.ElementTree as ET

            xml_data = [ET.tostring(x).decode("us-ascii") for x in xml_list]
        else:
            xml_data = None
        test_time = time.perf_counter() - start_time
        return TestResult(test_name, result, test_time, xml_data)
    finally:
        if use_timeout:
            faulthandler.cancel_dump_traceback_later()
        support.junit_xml_list = None


def runtest(ns, test_name):
    "Run a single test.\n\n    ns -- regrtest namespace of options\n    test_name -- the name of the test\n\n    Returns the tuple (result, test_time, xml_data), where result is one\n    of the constants:\n\n        INTERRUPTED      KeyboardInterrupt\n        RESOURCE_DENIED  test skipped because resource denied\n        SKIPPED          test skipped for some other reason\n        ENV_CHANGED      test failed because it changed the execution environment\n        FAILED           test failed\n        PASSED           test passed\n        EMPTY_TEST_SUITE test ran no subtests.\n        TIMEOUT          test timed out.\n\n    If ns.xmlpath is not None, xml_data is a list containing each\n    generated testsuite element.\n    "
    try:
        return _runtest(ns, test_name)
    except:
        if not ns.pgo:
            msg = traceback.format_exc()
            print(f"test {test_name} crashed -- {msg}", file=sys.stderr, flush=True)
        return TestResult(test_name, FAILED, 0.0, None)


def _test_module(the_module):
    loader = unittest.TestLoader()
    tests = loader.loadTestsFromModule(the_module)
    for error in loader.errors:
        print(error, file=sys.stderr)
    if loader.errors:
        raise Exception("errors while loading tests")
    support.run_unittest(tests)


def save_env(ns, test_name):
    return saved_test_environment(test_name, ns.verbose, ns.quiet, pgo=ns.pgo)


def _runtest_inner2(ns, test_name):
    abstest = get_abs_module(ns, test_name)
    try:
        del sys.modules[abstest]
    except KeyError:
        pass
    the_module = importlib.import_module(abstest)
    if ns.huntrleaks:
        from test.libregrtest.refleak import dash_R
    test_runner = getattr(the_module, "test_main", None)
    if test_runner is None:
        test_runner = functools.partial(_test_module, the_module)
    try:
        with save_env(ns, test_name):
            if ns.huntrleaks:
                refleak = dash_R(ns, test_name, test_runner)
            else:
                test_runner()
                refleak = False
    finally:
        cleanup_test_droppings(test_name, ns.verbose)
    support.gc_collect()
    if gc.garbage:
        support.environment_altered = True
        print_warning(f"{test_name} created {len(gc.garbage)} uncollectable object(s).")
        FOUND_GARBAGE.extend(gc.garbage)
        gc.garbage.clear()
    support.reap_children()
    return refleak


def _runtest_inner(ns, test_name, display_failure=True):
    support.environment_altered = False
    if ns.pgo:
        display_failure = False
    try:
        clear_caches()
        with save_env(ns, test_name):
            refleak = _runtest_inner2(ns, test_name)
    except support.ResourceDenied as msg:
        if (not ns.quiet) and (not ns.pgo):
            print(f"{test_name} skipped -- {msg}", flush=True)
        return RESOURCE_DENIED
    except unittest.SkipTest as msg:
        if (not ns.quiet) and (not ns.pgo):
            print(f"{test_name} skipped -- {msg}", flush=True)
        return SKIPPED
    except support.TestFailed as exc:
        msg = f"test {test_name} failed"
        if display_failure:
            msg = f"{msg} -- {exc}"
        print(msg, file=sys.stderr, flush=True)
        return FAILED
    except support.TestDidNotRun:
        return TEST_DID_NOT_RUN
    except KeyboardInterrupt:
        print()
        return INTERRUPTED
    except:
        if not ns.pgo:
            msg = traceback.format_exc()
            print(f"test {test_name} crashed -- {msg}", file=sys.stderr, flush=True)
        return FAILED
    if refleak:
        return FAILED
    if support.environment_altered:
        return ENV_CHANGED
    return PASSED


def cleanup_test_droppings(test_name, verbose):
    support.gc_collect()
    for name in (os_helper.TESTFN,):
        if not os.path.exists(name):
            continue
        if os.path.isdir(name):
            import shutil

            (kind, nuker) = ("directory", shutil.rmtree)
        elif os.path.isfile(name):
            (kind, nuker) = ("file", os.unlink)
        else:
            raise RuntimeError(
                f"os.path says {name!r} exists but is neither directory nor file"
            )
        if verbose:
            print_warning(f"{test_name} left behind {kind} {name!r}")
            support.environment_altered = True
        try:
            import stat

            os.chmod(name, ((stat.S_IRWXU | stat.S_IRWXG) | stat.S_IRWXO))
            nuker(name)
        except Exception as exc:
            print_warning(
                f"{test_name} left behind {kind} {name!r} and it couldn't be removed: {exc}"
            )
