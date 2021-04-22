"Tests for 'site'.\n\nTests assume the initial paths in sys.path once the interpreter has begun\nexecuting have not been removed.\n\n"
import unittest
import test.support
from test import support
from test.support import os_helper
from test.support import socket_helper
from test.support import captured_stderr
from test.support.os_helper import TESTFN, EnvironmentVarGuard, change_cwd
import builtins
import encodings
import glob
import io
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import urllib.error
import urllib.request
from unittest import mock
from copy import copy

if sys.flags.no_site:
    raise unittest.SkipTest("Python was invoked with -S")
import site

HAS_USER_SITE = site.USER_SITE is not None
OLD_SYS_PATH = None


def setUpModule():
    global OLD_SYS_PATH
    OLD_SYS_PATH = sys.path[:]
    if site.ENABLE_USER_SITE and (not os.path.isdir(site.USER_SITE)):
        try:
            os.makedirs(site.USER_SITE)
            site.addsitedir(site.USER_SITE)
        except PermissionError as exc:
            raise unittest.SkipTest(
                (
                    "unable to create user site directory (%r): %s"
                    % (site.USER_SITE, exc)
                )
            )


def tearDownModule():
    sys.path[:] = OLD_SYS_PATH


class HelperFunctionsTests(unittest.TestCase):
    "Tests for helper functions.\n    "

    def setUp(self):
        "Save a copy of sys.path"
        self.sys_path = sys.path[:]
        self.old_base = site.USER_BASE
        self.old_site = site.USER_SITE
        self.old_prefixes = site.PREFIXES
        self.original_vars = sysconfig._CONFIG_VARS
        self.old_vars = copy(sysconfig._CONFIG_VARS)

    def tearDown(self):
        "Restore sys.path"
        sys.path[:] = self.sys_path
        site.USER_BASE = self.old_base
        site.USER_SITE = self.old_site
        site.PREFIXES = self.old_prefixes
        sysconfig._CONFIG_VARS = self.original_vars
        sysconfig._CONFIG_VARS.clear()
        sysconfig._CONFIG_VARS.update(self.old_vars)

    def test_makepath(self):
        path_parts = ("Beginning", "End")
        original_dir = os.path.join(*path_parts)
        (abs_dir, norm_dir) = site.makepath(*path_parts)
        self.assertEqual(os.path.abspath(original_dir), abs_dir)
        if original_dir == os.path.normcase(original_dir):
            self.assertEqual(abs_dir, norm_dir)
        else:
            self.assertEqual(os.path.normcase(abs_dir), norm_dir)

    def test_init_pathinfo(self):
        dir_set = site._init_pathinfo()
        for entry in [
            site.makepath(path)[1]
            for path in sys.path
            if (path and os.path.exists(path))
        ]:
            self.assertIn(
                entry,
                dir_set,
                (
                    "%s from sys.path not found in set returned by _init_pathinfo(): %s"
                    % (entry, dir_set)
                ),
            )

    def pth_file_tests(self, pth_file):
        "Contain common code for testing results of reading a .pth file"
        self.assertIn(
            pth_file.imported,
            sys.modules,
            ("%s not in sys.modules" % pth_file.imported),
        )
        self.assertIn(site.makepath(pth_file.good_dir_path)[0], sys.path)
        self.assertFalse(os.path.exists(pth_file.bad_dir_path))

    def test_addpackage(self):
        pth_file = PthFile()
        pth_file.cleanup(prep=True)
        try:
            pth_file.create()
            site.addpackage(pth_file.base_dir, pth_file.filename, set())
            self.pth_file_tests(pth_file)
        finally:
            pth_file.cleanup()

    def make_pth(self, contents, pth_dir=".", pth_name=TESTFN):
        pth_dir = os.path.abspath(pth_dir)
        pth_basename = pth_name + ".pth"
        pth_fn = os.path.join(pth_dir, pth_basename)
        with open(pth_fn, "w", encoding="utf-8") as pth_file:
            self.addCleanup((lambda: os.remove(pth_fn)))
            pth_file.write(contents)
        return (pth_dir, pth_basename)

    def test_addpackage_import_bad_syntax(self):
        (pth_dir, pth_fn) = self.make_pth("import bad-syntax\n")
        with captured_stderr() as err_out:
            site.addpackage(pth_dir, pth_fn, set())
        self.assertRegex(err_out.getvalue(), "line 1")
        self.assertRegex(err_out.getvalue(), re.escape(os.path.join(pth_dir, pth_fn)))
        self.assertRegex(err_out.getvalue(), "Traceback")
        self.assertRegex(err_out.getvalue(), "import bad-syntax")
        self.assertRegex(err_out.getvalue(), "SyntaxError")

    def test_addpackage_import_bad_exec(self):
        (pth_dir, pth_fn) = self.make_pth("randompath\nimport nosuchmodule\n")
        with captured_stderr() as err_out:
            site.addpackage(pth_dir, pth_fn, set())
        self.assertRegex(err_out.getvalue(), "line 2")
        self.assertRegex(err_out.getvalue(), re.escape(os.path.join(pth_dir, pth_fn)))
        self.assertRegex(err_out.getvalue(), "Traceback")
        self.assertRegex(err_out.getvalue(), "ModuleNotFoundError")

    def test_addpackage_empty_lines(self):
        (pth_dir, pth_fn) = self.make_pth("\n\n  \n\n")
        known_paths = site.addpackage(pth_dir, pth_fn, set())
        self.assertEqual(known_paths, set())

    def test_addpackage_import_bad_pth_file(self):
        (pth_dir, pth_fn) = self.make_pth("abc\x00def\n")
        with captured_stderr() as err_out:
            self.assertFalse(site.addpackage(pth_dir, pth_fn, set()))
        self.maxDiff = None
        self.assertEqual(err_out.getvalue(), "")
        for path in sys.path:
            if isinstance(path, str):
                self.assertNotIn("abc\x00def", path)

    def test_addsitedir(self):
        pth_file = PthFile()
        pth_file.cleanup(prep=True)
        try:
            pth_file.create()
            site.addsitedir(pth_file.base_dir, set())
            self.pth_file_tests(pth_file)
        finally:
            pth_file.cleanup()

    def test__getuserbase(self):
        self.assertEqual(site._getuserbase(), sysconfig._getuserbase())

    @unittest.skipUnless(HAS_USER_SITE, "need user site")
    def test_get_path(self):
        if (sys.platform == "darwin") and sys._framework:
            scheme = "osx_framework_user"
        else:
            scheme = os.name + "_user"
        self.assertEqual(
            site._get_path(site._getuserbase()), sysconfig.get_path("purelib", scheme)
        )

    @unittest.skipUnless(
        site.ENABLE_USER_SITE,
        "requires access to PEP 370 user-site (site.ENABLE_USER_SITE)",
    )
    def test_s_option(self):
        usersite = site.USER_SITE
        self.assertIn(usersite, sys.path)
        env = os.environ.copy()
        rc = subprocess.call(
            [sys.executable, "-c", ("import sys; sys.exit(%r in sys.path)" % usersite)],
            env=env,
        )
        self.assertEqual(rc, 1)
        env = os.environ.copy()
        rc = subprocess.call(
            [
                sys.executable,
                "-s",
                "-c",
                ("import sys; sys.exit(%r in sys.path)" % usersite),
            ],
            env=env,
        )
        if usersite == site.getsitepackages()[0]:
            self.assertEqual(rc, 1)
        else:
            self.assertEqual(rc, 0, "User site still added to path with -s")
        env = os.environ.copy()
        env["PYTHONNOUSERSITE"] = "1"
        rc = subprocess.call(
            [sys.executable, "-c", ("import sys; sys.exit(%r in sys.path)" % usersite)],
            env=env,
        )
        if usersite == site.getsitepackages()[0]:
            self.assertEqual(rc, 1)
        else:
            self.assertEqual(
                rc, 0, "User site still added to path with PYTHONNOUSERSITE"
            )
        env = os.environ.copy()
        env["PYTHONUSERBASE"] = "/tmp"
        rc = subprocess.call(
            [
                sys.executable,
                "-c",
                'import sys, site; sys.exit(site.USER_BASE.startswith("/tmp"))',
            ],
            env=env,
        )
        self.assertEqual(rc, 1, "User base not set by PYTHONUSERBASE")

    @unittest.skipUnless(HAS_USER_SITE, "need user site")
    def test_getuserbase(self):
        site.USER_BASE = None
        user_base = site.getuserbase()
        self.assertEqual(site.USER_BASE, user_base)
        site.USER_BASE = None
        import sysconfig

        sysconfig._CONFIG_VARS = None
        with EnvironmentVarGuard() as environ:
            environ["PYTHONUSERBASE"] = "xoxo"
            self.assertTrue(site.getuserbase().startswith("xoxo"), site.getuserbase())

    @unittest.skipUnless(HAS_USER_SITE, "need user site")
    def test_getusersitepackages(self):
        site.USER_SITE = None
        site.USER_BASE = None
        user_site = site.getusersitepackages()
        self.assertEqual(site.USER_SITE, user_site)
        self.assertTrue(user_site.startswith(site.USER_BASE), user_site)
        self.assertEqual(site.USER_BASE, site.getuserbase())

    def test_getsitepackages(self):
        site.PREFIXES = ["xoxo"]
        dirs = site.getsitepackages()
        if os.sep == "/":
            if sys.platlibdir != "lib":
                self.assertEqual(len(dirs), 2)
                wanted = os.path.join(
                    "xoxo",
                    sys.platlibdir,
                    ("python%d.%d" % sys.version_info[:2]),
                    "site-packages",
                )
                self.assertEqual(dirs[0], wanted)
            else:
                self.assertEqual(len(dirs), 1)
            wanted = os.path.join(
                "xoxo", "lib", ("python%d.%d" % sys.version_info[:2]), "site-packages"
            )
            self.assertEqual(dirs[(-1)], wanted)
        else:
            self.assertEqual(len(dirs), 2)
            self.assertEqual(dirs[0], "xoxo")
            wanted = os.path.join("xoxo", "lib", "site-packages")
            self.assertEqual(dirs[1], wanted)

    @unittest.skipUnless(HAS_USER_SITE, "need user site")
    def test_no_home_directory(self):
        site.USER_SITE = None
        site.USER_BASE = None
        with EnvironmentVarGuard() as environ, mock.patch(
            "os.path.expanduser", (lambda path: path)
        ):
            del environ["PYTHONUSERBASE"]
            del environ["APPDATA"]
            user_base = site.getuserbase()
            self.assertTrue(user_base.startswith(("~" + os.sep)), user_base)
            user_site = site.getusersitepackages()
            self.assertTrue(user_site.startswith(user_base), user_site)
        with mock.patch(
            "os.path.isdir", return_value=False
        ) as mock_isdir, mock.patch.object(
            site, "addsitedir"
        ) as mock_addsitedir, support.swap_attr(
            site, "ENABLE_USER_SITE", True
        ):
            known_paths = set()
            site.addusersitepackages(known_paths)
            mock_isdir.assert_called_once_with(user_site)
            mock_addsitedir.assert_not_called()
            self.assertFalse(known_paths)

    def test_trace(self):
        message = "bla-bla-bla"
        for (verbose, out) in ((True, (message + "\n")), (False, "")):
            with mock.patch("sys.flags", mock.Mock(verbose=verbose)), mock.patch(
                "sys.stderr", io.StringIO()
            ):
                site._trace(message)
                self.assertEqual(sys.stderr.getvalue(), out)


class PthFile(object):
    "Helper class for handling testing of .pth files"

    def __init__(
        self,
        filename_base=TESTFN,
        imported="time",
        good_dirname="__testdir__",
        bad_dirname="__bad",
    ):
        "Initialize instance variables"
        self.filename = filename_base + ".pth"
        self.base_dir = os.path.abspath("")
        self.file_path = os.path.join(self.base_dir, self.filename)
        self.imported = imported
        self.good_dirname = good_dirname
        self.bad_dirname = bad_dirname
        self.good_dir_path = os.path.join(self.base_dir, self.good_dirname)
        self.bad_dir_path = os.path.join(self.base_dir, self.bad_dirname)

    def create(self):
        "Create a .pth file with a comment, blank lines, an ``import\n        <self.imported>``, a line with self.good_dirname, and a line with\n        self.bad_dirname.\n\n        Creation of the directory for self.good_dir_path (based off of\n        self.good_dirname) is also performed.\n\n        Make sure to call self.cleanup() to undo anything done by this method.\n\n        "
        FILE = open(self.file_path, "w")
        try:
            print("#import @bad module name", file=FILE)
            print("\n", file=FILE)
            print(("import %s" % self.imported), file=FILE)
            print(self.good_dirname, file=FILE)
            print(self.bad_dirname, file=FILE)
        finally:
            FILE.close()
        os.mkdir(self.good_dir_path)

    def cleanup(self, prep=False):
        "Make sure that the .pth file is deleted, self.imported is not in\n        sys.modules, and that both self.good_dirname and self.bad_dirname are\n        not existing directories."
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        if prep:
            self.imported_module = sys.modules.get(self.imported)
            if self.imported_module:
                del sys.modules[self.imported]
        elif self.imported_module:
            sys.modules[self.imported] = self.imported_module
        if os.path.exists(self.good_dir_path):
            os.rmdir(self.good_dir_path)
        if os.path.exists(self.bad_dir_path):
            os.rmdir(self.bad_dir_path)


class ImportSideEffectTests(unittest.TestCase):
    "Test side-effects from importing 'site'."

    def setUp(self):
        "Make a copy of sys.path"
        self.sys_path = sys.path[:]

    def tearDown(self):
        "Restore sys.path"
        sys.path[:] = self.sys_path

    def test_abs_paths_cached_None(self):
        "Test for __cached__ is None.\n\n        Regarding to PEP 3147, __cached__ can be None.\n\n        See also: https://bugs.python.org/issue30167\n        "
        sys.modules["test"].__cached__ = None
        site.abs_paths()
        self.assertIsNone(sys.modules["test"].__cached__)

    def test_no_duplicate_paths(self):
        site.removeduppaths()
        seen_paths = set()
        for path in sys.path:
            self.assertNotIn(path, seen_paths)
            seen_paths.add(path)

    @unittest.skip("test not implemented")
    def test_add_build_dir(self):
        pass

    def test_setting_quit(self):
        self.assertTrue(hasattr(builtins, "quit"))
        self.assertTrue(hasattr(builtins, "exit"))

    def test_setting_copyright(self):
        self.assertTrue(hasattr(builtins, "copyright"))
        self.assertTrue(hasattr(builtins, "credits"))
        self.assertTrue(hasattr(builtins, "license"))

    def test_setting_help(self):
        self.assertTrue(hasattr(builtins, "help"))

    def test_aliasing_mbcs(self):
        if sys.platform == "win32":
            import locale

            if locale.getdefaultlocale()[1].startswith("cp"):
                for value in encodings.aliases.aliases.values():
                    if value == "mbcs":
                        break
                else:
                    self.fail("did not alias mbcs")

    def test_sitecustomize_executed(self):
        if "sitecustomize" not in sys.modules:
            try:
                import sitecustomize
            except ImportError:
                pass
            else:
                self.fail("sitecustomize not imported automatically")

    @test.support.requires_resource("network")
    @test.support.system_must_validate_cert
    @unittest.skipUnless(
        hasattr(urllib.request, "HTTPSHandler"), "need SSL support to download license"
    )
    def test_license_exists_at_url(self):
        url = license._Printer__data.split()[1]
        req = urllib.request.Request(url, method="HEAD")
        self.addCleanup(urllib.request.urlcleanup)
        try:
            with socket_helper.transient_internet(url):
                with urllib.request.urlopen(req) as data:
                    code = data.getcode()
        except urllib.error.HTTPError as e:
            code = e.code
        self.assertEqual(code, 200, msg=("Can't find " + url))


class StartupImportTests(unittest.TestCase):
    def test_startup_imports(self):
        popen = subprocess.Popen(
            [sys.executable, "-I", "-c", "import sys; print(repr(sys.path))"],
            stdout=subprocess.PIPE,
            encoding="utf-8",
        )
        stdout = popen.communicate()[0]
        self.assertEqual(popen.returncode, 0, repr(stdout))
        isolated_paths = eval(stdout)
        for path in isolated_paths:
            pth_files = glob.glob(os.path.join(glob.escape(path), "*.pth"))
            if pth_files:
                self.skipTest(f"found {len(pth_files)} .pth files in: {path}")
        popen = subprocess.Popen(
            [sys.executable, "-I", "-v", "-c", "import sys; print(set(sys.modules))"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        (stdout, stderr) = popen.communicate()
        self.assertEqual(popen.returncode, 0, (stdout, stderr))
        modules = eval(stdout)
        self.assertIn("site", modules)
        re_mods = {"re", "_sre", "sre_compile", "sre_constants", "sre_parse"}
        self.assertFalse(modules.intersection(re_mods), stderr)
        self.assertNotIn("locale", modules, stderr)
        self.assertNotIn("copyreg", modules, stderr)
        collection_mods = {
            "_collections",
            "collections",
            "functools",
            "heapq",
            "itertools",
            "keyword",
            "operator",
            "reprlib",
            "types",
            "weakref",
        }.difference(sys.builtin_module_names)
        self.assertFalse(modules.intersection(collection_mods), stderr)

    def test_startup_interactivehook(self):
        r = subprocess.Popen(
            [
                sys.executable,
                "-c",
                'import sys; sys.exit(hasattr(sys, "__interactivehook__"))',
            ]
        ).wait()
        self.assertTrue(r, "'__interactivehook__' not added by site")

    def test_startup_interactivehook_isolated(self):
        r = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-c",
                'import sys; sys.exit(hasattr(sys, "__interactivehook__"))',
            ]
        ).wait()
        self.assertFalse(r, "'__interactivehook__' added in isolated mode")

    def test_startup_interactivehook_isolated_explicit(self):
        r = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-c",
                'import site, sys; site.enablerlcompleter(); sys.exit(hasattr(sys, "__interactivehook__"))',
            ]
        ).wait()
        self.assertTrue(r, "'__interactivehook__' not added by enablerlcompleter()")


@unittest.skipUnless((sys.platform == "win32"), "only supported on Windows")
class _pthFileTests(unittest.TestCase):
    def _create_underpth_exe(self, lines, exe_pth=True):
        import _winapi

        temp_dir = tempfile.mkdtemp()
        self.addCleanup(os_helper.rmtree, temp_dir)
        exe_file = os.path.join(temp_dir, os.path.split(sys.executable)[1])
        dll_src_file = _winapi.GetModuleFileName(sys.dllhandle)
        dll_file = os.path.join(temp_dir, os.path.split(dll_src_file)[1])
        shutil.copy(sys.executable, exe_file)
        shutil.copy(dll_src_file, dll_file)
        if exe_pth:
            _pth_file = os.path.splitext(exe_file)[0] + "._pth"
        else:
            _pth_file = os.path.splitext(dll_file)[0] + "._pth"
        with open(_pth_file, "w") as f:
            for line in lines:
                print(line, file=f)
        return exe_file

    def _calc_sys_path_for_underpth_nosite(self, sys_prefix, lines):
        sys_path = []
        for line in lines:
            if (not line) or (line[0] == "#"):
                continue
            abs_path = os.path.abspath(os.path.join(sys_prefix, line))
            sys_path.append(abs_path)
        return sys_path

    def test_underpth_nosite_file(self):
        libpath = os.path.dirname(os.path.dirname(encodings.__file__))
        exe_prefix = os.path.dirname(sys.executable)
        pth_lines = ["fake-path-name", *[libpath for _ in range(200)], "", "# comment"]
        exe_file = self._create_underpth_exe(pth_lines)
        sys_path = self._calc_sys_path_for_underpth_nosite(
            os.path.dirname(exe_file), pth_lines
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = "from-env"
        env["PATH"] = "{};{}".format(exe_prefix, os.getenv("PATH"))
        output = subprocess.check_output(
            [
                exe_file,
                "-c",
                'import sys; print("\\n".join(sys.path) if sys.flags.no_site else "")',
            ],
            env=env,
            encoding="ansi",
        )
        actual_sys_path = output.rstrip().split("\n")
        self.assertTrue(actual_sys_path, "sys.flags.no_site was False")
        self.assertEqual(actual_sys_path, sys_path, "sys.path is incorrect")

    def test_underpth_file(self):
        libpath = os.path.dirname(os.path.dirname(encodings.__file__))
        exe_prefix = os.path.dirname(sys.executable)
        exe_file = self._create_underpth_exe(
            [
                "fake-path-name",
                *[libpath for _ in range(200)],
                "",
                "# comment",
                "import site",
            ]
        )
        sys_prefix = os.path.dirname(exe_file)
        env = os.environ.copy()
        env["PYTHONPATH"] = "from-env"
        env["PATH"] = "{};{}".format(exe_prefix, os.getenv("PATH"))
        rc = subprocess.call(
            [
                exe_file,
                "-c",
                (
                    'import sys; sys.exit(not sys.flags.no_site and %r in sys.path and %r in sys.path and %r not in sys.path and all("\\r" not in p and "\\n" not in p for p in sys.path))'
                    % (
                        os.path.join(sys_prefix, "fake-path-name"),
                        libpath,
                        os.path.join(sys_prefix, "from-env"),
                    )
                ),
            ],
            env=env,
        )
        self.assertTrue(rc, "sys.path is incorrect")

    def test_underpth_dll_file(self):
        libpath = os.path.dirname(os.path.dirname(encodings.__file__))
        exe_prefix = os.path.dirname(sys.executable)
        exe_file = self._create_underpth_exe(
            [
                "fake-path-name",
                *[libpath for _ in range(200)],
                "",
                "# comment",
                "import site",
            ],
            exe_pth=False,
        )
        sys_prefix = os.path.dirname(exe_file)
        env = os.environ.copy()
        env["PYTHONPATH"] = "from-env"
        env["PATH"] = "{};{}".format(exe_prefix, os.getenv("PATH"))
        rc = subprocess.call(
            [
                exe_file,
                "-c",
                (
                    'import sys; sys.exit(not sys.flags.no_site and %r in sys.path and %r in sys.path and %r not in sys.path and all("\\r" not in p and "\\n" not in p for p in sys.path))'
                    % (
                        os.path.join(sys_prefix, "fake-path-name"),
                        libpath,
                        os.path.join(sys_prefix, "from-env"),
                    )
                ),
            ],
            env=env,
        )
        self.assertTrue(rc, "sys.path is incorrect")


if __name__ == "__main__":
    unittest.main()
