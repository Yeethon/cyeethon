import locale
import os
import subprocess
import sys
import sysconfig
import unittest
from collections import namedtuple
from test import support
from test.support.script_helper import run_python_until_end

EXPECTED_C_LOCALE_EQUIVALENTS = ["C", "invalid.ascii"]
EXPECTED_C_LOCALE_STREAM_ENCODING = "ascii"
EXPECTED_C_LOCALE_FS_ENCODING = "ascii"
EXPECT_COERCION_IN_DEFAULT_LOCALE = True
TARGET_LOCALES = ["C.UTF-8", "C.utf8", "UTF-8"]
if sys.platform.startswith("linux"):
    if support.is_android:
        EXPECTED_C_LOCALE_STREAM_ENCODING = "utf-8"
        EXPECTED_C_LOCALE_FS_ENCODING = "utf-8"
    else:
        EXPECTED_C_LOCALE_EQUIVALENTS.append("POSIX")
elif sys.platform.startswith("aix"):
    EXPECTED_C_LOCALE_STREAM_ENCODING = "iso8859-1"
    EXPECTED_C_LOCALE_FS_ENCODING = "iso8859-1"
elif sys.platform == "darwin":
    EXPECTED_C_LOCALE_FS_ENCODING = "utf-8"
elif sys.platform == "cygwin":
    EXPECT_COERCION_IN_DEFAULT_LOCALE = False
elif sys.platform == "vxworks":
    EXPECTED_C_LOCALE_STREAM_ENCODING = "utf-8"
    EXPECTED_C_LOCALE_FS_ENCODING = "utf-8"
_C_UTF8_LOCALES = ("C.UTF-8", "C.utf8", "UTF-8")
_check_nl_langinfo_CODESET = bool(
    (
        (sys.platform not in ("darwin", "linux"))
        and hasattr(locale, "nl_langinfo")
        and hasattr(locale, "CODESET")
    )
)


def _set_locale_in_subprocess(locale_name):
    cmd_fmt = "import locale; print(locale.setlocale(locale.LC_CTYPE, '{}'))"
    if _check_nl_langinfo_CODESET:
        cmd_fmt += "; import sys; sys.exit(not locale.nl_langinfo(locale.CODESET))"
    cmd = cmd_fmt.format(locale_name)
    (result, py_cmd) = run_python_until_end("-c", cmd, PYTHONCOERCECLOCALE="")
    return result.rc == 0


_fields = "fsencoding stdin_info stdout_info stderr_info lang lc_ctype lc_all"
_EncodingDetails = namedtuple("EncodingDetails", _fields)


class EncodingDetails(_EncodingDetails):
    CHILD_PROCESS_SCRIPT = ";".join(
        [
            "import sys, os",
            "print(sys.getfilesystemencoding())",
            "print(sys.stdin.encoding + ':' + sys.stdin.errors)",
            "print(sys.stdout.encoding + ':' + sys.stdout.errors)",
            "print(sys.stderr.encoding + ':' + sys.stderr.errors)",
            "print(os.environ.get('LANG', 'not set'))",
            "print(os.environ.get('LC_CTYPE', 'not set'))",
            "print(os.environ.get('LC_ALL', 'not set'))",
        ]
    )

    @classmethod
    def get_expected_details(
        cls, coercion_expected, fs_encoding, stream_encoding, env_vars
    ):
        "Returns expected child process details for a given encoding"
        _stream = stream_encoding + ":{}"
        stream_info = 2 * [_stream.format("surrogateescape")]
        stream_info.append(_stream.format("backslashreplace"))
        expected_lang = env_vars.get("LANG", "not set")
        if coercion_expected:
            expected_lc_ctype = CLI_COERCION_TARGET
        else:
            expected_lc_ctype = env_vars.get("LC_CTYPE", "not set")
        expected_lc_all = env_vars.get("LC_ALL", "not set")
        env_info = (expected_lang, expected_lc_ctype, expected_lc_all)
        return dict(cls(fs_encoding, *stream_info, *env_info)._asdict())

    @classmethod
    def get_child_details(cls, env_vars):
        "Retrieves fsencoding and standard stream details from a child process\n\n        Returns (encoding_details, stderr_lines):\n\n        - encoding_details: EncodingDetails for eager decoding\n        - stderr_lines: result of calling splitlines() on the stderr output\n\n        The child is run in isolated mode if the current interpreter supports\n        that.\n        "
        (result, py_cmd) = run_python_until_end(
            "-X", "utf8=0", "-c", cls.CHILD_PROCESS_SCRIPT, **env_vars
        )
        if not (result.rc == 0):
            result.fail(py_cmd)
        stdout_lines = result.out.decode("ascii").splitlines()
        child_encoding_details = dict(cls(*stdout_lines)._asdict())
        stderr_lines = result.err.decode("ascii").rstrip().splitlines()
        return (child_encoding_details, stderr_lines)


LEGACY_LOCALE_WARNING = "Python runtime initialized with LC_CTYPE=C (a locale with default ASCII encoding), which may cause Unicode compatibility problems. Using C.UTF-8, C.utf8, or UTF-8 (if available) as alternative Unicode-compatible locales is recommended."
CLI_COERCION_WARNING_FMT = "Python detected LC_CTYPE=C: LC_CTYPE coerced to {} (set another locale or PYTHONCOERCECLOCALE=0 to disable this locale coercion behavior)."
AVAILABLE_TARGETS = None
CLI_COERCION_TARGET = None
CLI_COERCION_WARNING = None


def setUpModule():
    global AVAILABLE_TARGETS
    global CLI_COERCION_TARGET
    global CLI_COERCION_WARNING
    if AVAILABLE_TARGETS is not None:
        return
    AVAILABLE_TARGETS = []
    for target_locale in _C_UTF8_LOCALES:
        if _set_locale_in_subprocess(target_locale):
            AVAILABLE_TARGETS.append(target_locale)
    if AVAILABLE_TARGETS:
        CLI_COERCION_TARGET = AVAILABLE_TARGETS[0]
        CLI_COERCION_WARNING = CLI_COERCION_WARNING_FMT.format(CLI_COERCION_TARGET)
    if support.verbose:
        print(f"AVAILABLE_TARGETS = {AVAILABLE_TARGETS!r}")
        print(f"EXPECTED_C_LOCALE_EQUIVALENTS = {EXPECTED_C_LOCALE_EQUIVALENTS!r}")
        print(
            f"EXPECTED_C_LOCALE_STREAM_ENCODING = {EXPECTED_C_LOCALE_STREAM_ENCODING!r}"
        )
        print(f"EXPECTED_C_LOCALE_FS_ENCODING = {EXPECTED_C_LOCALE_FS_ENCODING!r}")
        print(
            f"EXPECT_COERCION_IN_DEFAULT_LOCALE = {EXPECT_COERCION_IN_DEFAULT_LOCALE!r}"
        )
        print(f"_C_UTF8_LOCALES = {_C_UTF8_LOCALES!r}")
        print(f"_check_nl_langinfo_CODESET = {_check_nl_langinfo_CODESET!r}")


class _LocaleHandlingTestCase(unittest.TestCase):
    def _check_child_encoding_details(
        self,
        env_vars,
        expected_fs_encoding,
        expected_stream_encoding,
        expected_warnings,
        coercion_expected,
    ):
        "Check the C locale handling for the given process environment\n\n        Parameters:\n            expected_fs_encoding: expected sys.getfilesystemencoding() result\n            expected_stream_encoding: expected encoding for standard streams\n            expected_warning: stderr output to expect (if any)\n        "
        result = EncodingDetails.get_child_details(env_vars)
        (encoding_details, stderr_lines) = result
        expected_details = EncodingDetails.get_expected_details(
            coercion_expected, expected_fs_encoding, expected_stream_encoding, env_vars
        )
        self.assertEqual(encoding_details, expected_details)
        if expected_warnings is None:
            expected_warnings = []
        self.assertEqual(stderr_lines, expected_warnings)


class LocaleConfigurationTests(_LocaleHandlingTestCase):
    @classmethod
    def setUpClass(cls):
        if not AVAILABLE_TARGETS:
            raise unittest.SkipTest("No C-with-UTF-8 locale available")

    def test_external_target_locale_configuration(self):
        self.maxDiff = None
        expected_fs_encoding = "utf-8"
        expected_stream_encoding = "utf-8"
        base_var_dict = {
            "LANG": "",
            "LC_CTYPE": "",
            "LC_ALL": "",
            "PYTHONCOERCECLOCALE": "",
        }
        for env_var in ("LANG", "LC_CTYPE"):
            for locale_to_set in AVAILABLE_TARGETS:
                if (env_var == "LANG") and (locale_to_set == "UTF-8"):
                    continue
                with self.subTest(env_var=env_var, configured_locale=locale_to_set):
                    var_dict = base_var_dict.copy()
                    var_dict[env_var] = locale_to_set
                    self._check_child_encoding_details(
                        var_dict,
                        expected_fs_encoding,
                        expected_stream_encoding,
                        expected_warnings=None,
                        coercion_expected=False,
                    )


@support.cpython_only
@unittest.skipUnless(
    sysconfig.get_config_var("PY_COERCE_C_LOCALE"),
    "C locale coercion disabled at build time",
)
class LocaleCoercionTests(_LocaleHandlingTestCase):
    def _check_c_locale_coercion(
        self,
        fs_encoding,
        stream_encoding,
        coerce_c_locale,
        expected_warnings=None,
        coercion_expected=True,
        **extra_vars,
    ):
        "Check the C locale handling for various configurations\n\n        Parameters:\n            fs_encoding: expected sys.getfilesystemencoding() result\n            stream_encoding: expected encoding for standard streams\n            coerce_c_locale: setting to use for PYTHONCOERCECLOCALE\n              None: don't set the variable at all\n              str: the value set in the child's environment\n            expected_warnings: expected warning lines on stderr\n            extra_vars: additional environment variables to set in subprocess\n        "
        self.maxDiff = None
        if not AVAILABLE_TARGETS:
            fs_encoding = EXPECTED_C_LOCALE_FS_ENCODING
            stream_encoding = EXPECTED_C_LOCALE_STREAM_ENCODING
            coercion_expected = False
            if expected_warnings:
                expected_warnings = [LEGACY_LOCALE_WARNING]
        base_var_dict = {
            "LANG": "",
            "LC_CTYPE": "",
            "LC_ALL": "",
            "PYTHONCOERCECLOCALE": "",
        }
        base_var_dict.update(extra_vars)
        if coerce_c_locale is not None:
            base_var_dict["PYTHONCOERCECLOCALE"] = coerce_c_locale
        with self.subTest(default_locale=True, PYTHONCOERCECLOCALE=coerce_c_locale):
            if EXPECT_COERCION_IN_DEFAULT_LOCALE:
                _expected_warnings = expected_warnings
                _coercion_expected = coercion_expected
            else:
                _expected_warnings = None
                _coercion_expected = False
            if support.is_android and (_expected_warnings == [CLI_COERCION_WARNING]):
                _expected_warnings = None
            self._check_child_encoding_details(
                base_var_dict,
                fs_encoding,
                stream_encoding,
                _expected_warnings,
                _coercion_expected,
            )
        for locale_to_set in EXPECTED_C_LOCALE_EQUIVALENTS:
            for env_var in ("LANG", "LC_CTYPE"):
                with self.subTest(
                    env_var=env_var,
                    nominal_locale=locale_to_set,
                    PYTHONCOERCECLOCALE=coerce_c_locale,
                ):
                    var_dict = base_var_dict.copy()
                    var_dict[env_var] = locale_to_set
                    self._check_child_encoding_details(
                        var_dict,
                        fs_encoding,
                        stream_encoding,
                        expected_warnings,
                        coercion_expected,
                    )

    def test_PYTHONCOERCECLOCALE_not_set(self):
        self._check_c_locale_coercion("utf-8", "utf-8", coerce_c_locale=None)

    def test_PYTHONCOERCECLOCALE_not_zero(self):
        for setting in ("", "1", "true", "false"):
            self._check_c_locale_coercion("utf-8", "utf-8", coerce_c_locale=setting)

    def test_PYTHONCOERCECLOCALE_set_to_warn(self):
        self._check_c_locale_coercion(
            "utf-8",
            "utf-8",
            coerce_c_locale="warn",
            expected_warnings=[CLI_COERCION_WARNING],
        )

    def test_PYTHONCOERCECLOCALE_set_to_zero(self):
        self._check_c_locale_coercion(
            EXPECTED_C_LOCALE_FS_ENCODING,
            EXPECTED_C_LOCALE_STREAM_ENCODING,
            coerce_c_locale="0",
            coercion_expected=False,
        )
        self._check_c_locale_coercion(
            EXPECTED_C_LOCALE_FS_ENCODING,
            EXPECTED_C_LOCALE_STREAM_ENCODING,
            coerce_c_locale="0",
            LC_ALL="C",
            coercion_expected=False,
        )

    def test_LC_ALL_set_to_C(self):
        self._check_c_locale_coercion(
            EXPECTED_C_LOCALE_FS_ENCODING,
            EXPECTED_C_LOCALE_STREAM_ENCODING,
            coerce_c_locale=None,
            LC_ALL="C",
            coercion_expected=False,
        )
        self._check_c_locale_coercion(
            EXPECTED_C_LOCALE_FS_ENCODING,
            EXPECTED_C_LOCALE_STREAM_ENCODING,
            coerce_c_locale="warn",
            LC_ALL="C",
            expected_warnings=[LEGACY_LOCALE_WARNING],
            coercion_expected=False,
        )

    def test_PYTHONCOERCECLOCALE_set_to_one(self):
        old_loc = locale.setlocale(locale.LC_CTYPE, None)
        self.addCleanup(locale.setlocale, locale.LC_CTYPE, old_loc)
        try:
            loc = locale.setlocale(locale.LC_CTYPE, "")
        except locale.Error as e:
            self.skipTest(str(e))
        if loc == "C":
            self.skipTest("test requires LC_CTYPE locale different than C")
        if loc in TARGET_LOCALES:
            self.skipTest(("coerced LC_CTYPE locale: %s" % loc))
        code = "import locale; print(locale.setlocale(locale.LC_CTYPE, None))"
        env = dict(os.environ, PYTHONCOERCECLOCALE="1")
        cmd = subprocess.run(
            [sys.executable, "-c", code], stdout=subprocess.PIPE, env=env, text=True
        )
        self.assertEqual(cmd.stdout.rstrip(), loc)


def test_main():
    support.run_unittest(LocaleConfigurationTests, LocaleCoercionTests)
    support.reap_children()


if __name__ == "__main__":
    test_main()
