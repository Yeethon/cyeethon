from test import support, test_tools
from test.support import os_helper
from unittest import TestCase
import collections
import inspect
import os.path
import sys
import unittest

test_tools.skip_if_missing("clinic")
with test_tools.imports_under_tool("clinic"):
    import clinic
    from clinic import DSLParser


class FakeConverter:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class FakeConverterFactory:
    def __init__(self, name):
        self.name = name

    def __call__(self, name, default, **kwargs):
        return FakeConverter(self.name, kwargs)


class FakeConvertersDict:
    def __init__(self):
        self.used_converters = {}

    def get(self, name, default):
        return self.used_converters.setdefault(name, FakeConverterFactory(name))


c = clinic.Clinic(language="C", filename="file")


class FakeClinic:
    def __init__(self):
        self.converters = FakeConvertersDict()
        self.legacy_converters = FakeConvertersDict()
        self.language = clinic.CLanguage(None)
        self.filename = None
        self.destination_buffers = {}
        self.block_parser = clinic.BlockParser("", self.language)
        self.modules = collections.OrderedDict()
        self.classes = collections.OrderedDict()
        clinic.clinic = self
        self.name = "FakeClinic"
        self.line_prefix = self.line_suffix = ""
        self.destinations = {}
        self.add_destination("block", "buffer")
        self.add_destination("file", "buffer")
        self.add_destination("suppress", "suppress")
        d = self.destinations.get
        self.field_destinations = collections.OrderedDict(
            (
                ("docstring_prototype", d("suppress")),
                ("docstring_definition", d("block")),
                ("methoddef_define", d("block")),
                ("impl_prototype", d("block")),
                ("parser_prototype", d("suppress")),
                ("parser_definition", d("block")),
                ("impl_definition", d("block")),
            )
        )

    def get_destination(self, name):
        d = self.destinations.get(name)
        if not d:
            sys.exit(("Destination does not exist: " + repr(name)))
        return d

    def add_destination(self, name, type, *args):
        if name in self.destinations:
            sys.exit(("Destination already exists: " + repr(name)))
        self.destinations[name] = clinic.Destination(name, type, self, *args)

    def is_directive(self, name):
        return name == "module"

    def directive(self, name, args):
        self.called_directives[name] = args

    _module_and_class = clinic.Clinic._module_and_class


class ClinicWholeFileTest(TestCase):
    def test_eol(self):
        c = clinic.Clinic(clinic.CLanguage(None), filename="file")
        raw = "/*[clinic]\nfoo\n[clinic]*/"
        cooked = c.parse(raw).splitlines()
        end_line = cooked[2].rstrip()
        self.assertNotEqual(end_line, "[clinic]*/[clinic]*/")
        self.assertEqual(end_line, "[clinic]*/")


class ClinicGroupPermuterTest(TestCase):
    def _test(self, l, m, r, output):
        computed = clinic.permute_optional_groups(l, m, r)
        self.assertEqual(output, computed)

    def test_range(self):
        self._test(
            [["start"]],
            ["stop"],
            [["step"]],
            (("stop",), ("start", "stop"), ("start", "stop", "step")),
        )

    def test_add_window(self):
        self._test(
            [["x", "y"]],
            ["ch"],
            [["attr"]],
            (("ch",), ("ch", "attr"), ("x", "y", "ch"), ("x", "y", "ch", "attr")),
        )

    def test_ludicrous(self):
        self._test(
            [["a1", "a2", "a3"], ["b1", "b2"]],
            ["c1"],
            [["d1", "d2"], ["e1", "e2", "e3"]],
            (
                ("c1",),
                ("b1", "b2", "c1"),
                ("b1", "b2", "c1", "d1", "d2"),
                ("a1", "a2", "a3", "b1", "b2", "c1"),
                ("a1", "a2", "a3", "b1", "b2", "c1", "d1", "d2"),
                ("a1", "a2", "a3", "b1", "b2", "c1", "d1", "d2", "e1", "e2", "e3"),
            ),
        )

    def test_right_only(self):
        self._test(
            [], [], [["a"], ["b"], ["c"]], ((), ("a",), ("a", "b"), ("a", "b", "c"))
        )

    def test_have_left_options_but_required_is_empty(self):
        def fn():
            clinic.permute_optional_groups(["a"], [], [])

        self.assertRaises(AssertionError, fn)


class ClinicLinearFormatTest(TestCase):
    def _test(self, input, output, **kwargs):
        computed = clinic.linear_format(input, **kwargs)
        self.assertEqual(output, computed)

    def test_empty_strings(self):
        self._test("", "")

    def test_solo_newline(self):
        self._test("\n", "\n")

    def test_no_substitution(self):
        self._test("\n          abc\n          ", "\n          abc\n          ")

    def test_empty_substitution(self):
        self._test(
            "\n          abc\n          {name}\n          def\n          ",
            "\n          abc\n          def\n          ",
            name="",
        )

    def test_single_line_substitution(self):
        self._test(
            "\n          abc\n          {name}\n          def\n          ",
            "\n          abc\n          GARGLE\n          def\n          ",
            name="GARGLE",
        )

    def test_multiline_substitution(self):
        self._test(
            "\n          abc\n          {name}\n          def\n          ",
            "\n          abc\n          bingle\n          bungle\n\n          def\n          ",
            name="bingle\nbungle\n",
        )


class InertParser:
    def __init__(self, clinic):
        pass

    def parse(self, block):
        pass


class CopyParser:
    def __init__(self, clinic):
        pass

    def parse(self, block):
        block.output = block.input


class ClinicBlockParserTest(TestCase):
    def _test(self, input, output):
        language = clinic.CLanguage(None)
        blocks = list(clinic.BlockParser(input, language))
        writer = clinic.BlockPrinter(language)
        for block in blocks:
            writer.print_block(block)
        output = writer.f.getvalue()
        assert output == input, (
            ("output != input!\n\noutput " + repr(output)) + "\n\n input "
        ) + repr(input)

    def round_trip(self, input):
        return self._test(input, input)

    def test_round_trip_1(self):
        self.round_trip("\n    verbatim text here\n    lah dee dah\n")

    def test_round_trip_2(self):
        self.round_trip(
            "\n    verbatim text here\n    lah dee dah\n/*[inert]\nabc\n[inert]*/\ndef\n/*[inert checksum: 7b18d017f89f61cf17d47f92749ea6930a3f1deb]*/\nxyz\n"
        )

    def _test_clinic(self, input, output):
        language = clinic.CLanguage(None)
        c = clinic.Clinic(language, filename="file")
        c.parsers["inert"] = InertParser(c)
        c.parsers["copy"] = CopyParser(c)
        computed = c.parse(input)
        self.assertEqual(output, computed)

    def test_clinic_1(self):
        self._test_clinic(
            "\n    verbatim text here\n    lah dee dah\n/*[copy input]\ndef\n[copy start generated code]*/\nabc\n/*[copy end generated code: output=03cfd743661f0797 input=7b18d017f89f61cf]*/\nxyz\n",
            "\n    verbatim text here\n    lah dee dah\n/*[copy input]\ndef\n[copy start generated code]*/\ndef\n/*[copy end generated code: output=7b18d017f89f61cf input=7b18d017f89f61cf]*/\nxyz\n",
        )


class ClinicParserTest(TestCase):
    def test_trivial(self):
        parser = DSLParser(FakeClinic())
        block = clinic.Block("module os\nos.access")
        parser.parse(block)
        (module, function) = block.signatures
        self.assertEqual("access", function.name)
        self.assertEqual("os", module.name)

    def test_ignore_line(self):
        block = self.parse("#\nmodule os\nos.access")
        (module, function) = block.signatures
        self.assertEqual("access", function.name)
        self.assertEqual("os", module.name)

    def test_param(self):
        function = self.parse_function("module os\nos.access\n   path: int")
        self.assertEqual("access", function.name)
        self.assertEqual(2, len(function.parameters))
        p = function.parameters["path"]
        self.assertEqual("path", p.name)
        self.assertIsInstance(p.converter, clinic.int_converter)

    def test_param_default(self):
        function = self.parse_function(
            "module os\nos.access\n    follow_symlinks: bool = True"
        )
        p = function.parameters["follow_symlinks"]
        self.assertEqual(True, p.default)

    def test_param_with_continuations(self):
        function = self.parse_function(
            "module os\nos.access\n    follow_symlinks: \\\n   bool \\\n   =\\\n    True"
        )
        p = function.parameters["follow_symlinks"]
        self.assertEqual(True, p.default)

    def test_param_default_expression(self):
        function = self.parse_function(
            "module os\nos.access\n    follow_symlinks: int(c_default='MAXSIZE') = sys.maxsize"
        )
        p = function.parameters["follow_symlinks"]
        self.assertEqual(sys.maxsize, p.default)
        self.assertEqual("MAXSIZE", p.converter.c_default)
        s = self.parse_function_should_fail(
            "module os\nos.access\n    follow_symlinks: int = sys.maxsize"
        )
        self.assertEqual(
            s,
            "Error on line 0:\nWhen you specify a named constant ('sys.maxsize') as your default value,\nyou MUST specify a valid c_default.\n",
        )

    def test_param_no_docstring(self):
        function = self.parse_function(
            "\nmodule os\nos.access\n    follow_symlinks: bool = True\n    something_else: str = ''"
        )
        p = function.parameters["follow_symlinks"]
        self.assertEqual(3, len(function.parameters))
        self.assertIsInstance(
            function.parameters["something_else"].converter, clinic.str_converter
        )

    def test_param_default_parameters_out_of_order(self):
        s = self.parse_function_should_fail(
            "\nmodule os\nos.access\n    follow_symlinks: bool = True\n    something_else: str"
        )
        self.assertEqual(
            s,
            "Error on line 0:\nCan't have a parameter without a default ('something_else')\nafter a parameter with a default!\n",
        )

    def disabled_test_converter_arguments(self):
        function = self.parse_function(
            "module os\nos.access\n    path: path_t(allow_fd=1)"
        )
        p = function.parameters["path"]
        self.assertEqual(1, p.converter.args["allow_fd"])

    def test_function_docstring(self):
        function = self.parse_function(
            "\nmodule os\nos.stat as os_stat_fn\n\n   path: str\n       Path to be examined\n\nPerform a stat system call on the given path."
        )
        self.assertEqual(
            "\nstat($module, /, path)\n--\n\nPerform a stat system call on the given path.\n\n  path\n    Path to be examined\n".strip(),
            function.docstring,
        )

    def test_explicit_parameters_in_docstring(self):
        function = self.parse_function(
            "\nmodule foo\nfoo.bar\n  x: int\n     Documentation for x.\n  y: int\n\nThis is the documentation for foo.\n\nOkay, we're done here.\n"
        )
        self.assertEqual(
            "\nbar($module, /, x, y)\n--\n\nThis is the documentation for foo.\n\n  x\n    Documentation for x.\n\nOkay, we're done here.\n".strip(),
            function.docstring,
        )

    def test_parser_regression_special_character_in_parameter_column_of_docstring_first_line(
        self,
    ):
        function = self.parse_function(
            "\nmodule os\nos.stat\n    path: str\nThis/used to break Clinic!\n"
        )
        self.assertEqual(
            "stat($module, /, path)\n--\n\nThis/used to break Clinic!",
            function.docstring,
        )

    def test_c_name(self):
        function = self.parse_function("module os\nos.stat as os_stat_fn")
        self.assertEqual("os_stat_fn", function.c_basename)

    def test_return_converter(self):
        function = self.parse_function("module os\nos.stat -> int")
        self.assertIsInstance(function.return_converter, clinic.int_return_converter)

    def test_star(self):
        function = self.parse_function(
            "module os\nos.access\n    *\n    follow_symlinks: bool = True"
        )
        p = function.parameters["follow_symlinks"]
        self.assertEqual(inspect.Parameter.KEYWORD_ONLY, p.kind)
        self.assertEqual(0, p.group)

    def test_group(self):
        function = self.parse_function(
            "module window\nwindow.border\n [\n ls : int\n ]\n /\n"
        )
        p = function.parameters["ls"]
        self.assertEqual(1, p.group)

    def test_left_group(self):
        function = self.parse_function(
            "\nmodule curses\ncurses.addch\n   [\n   y: int\n     Y-coordinate.\n   x: int\n     X-coordinate.\n   ]\n   ch: char\n     Character to add.\n   [\n   attr: long\n     Attributes for the character.\n   ]\n   /\n"
        )
        for (name, group) in (("y", (-1)), ("x", (-1)), ("ch", 0), ("attr", 1)):
            p = function.parameters[name]
            self.assertEqual(p.group, group)
            self.assertEqual(p.kind, inspect.Parameter.POSITIONAL_ONLY)
        self.assertEqual(
            function.docstring.strip(),
            "\naddch([y, x,] ch, [attr])\n\n\n  y\n    Y-coordinate.\n  x\n    X-coordinate.\n  ch\n    Character to add.\n  attr\n    Attributes for the character.\n            ".strip(),
        )

    def test_nested_groups(self):
        function = self.parse_function(
            "\nmodule curses\ncurses.imaginary\n   [\n   [\n   y1: int\n     Y-coordinate.\n   y2: int\n     Y-coordinate.\n   ]\n   x1: int\n     X-coordinate.\n   x2: int\n     X-coordinate.\n   ]\n   ch: char\n     Character to add.\n   [\n   attr1: long\n     Attributes for the character.\n   attr2: long\n     Attributes for the character.\n   attr3: long\n     Attributes for the character.\n   [\n   attr4: long\n     Attributes for the character.\n   attr5: long\n     Attributes for the character.\n   attr6: long\n     Attributes for the character.\n   ]\n   ]\n   /\n"
        )
        for (name, group) in (
            ("y1", (-2)),
            ("y2", (-2)),
            ("x1", (-1)),
            ("x2", (-1)),
            ("ch", 0),
            ("attr1", 1),
            ("attr2", 1),
            ("attr3", 1),
            ("attr4", 2),
            ("attr5", 2),
            ("attr6", 2),
        ):
            p = function.parameters[name]
            self.assertEqual(p.group, group)
            self.assertEqual(p.kind, inspect.Parameter.POSITIONAL_ONLY)
        self.assertEqual(
            function.docstring.strip(),
            "\nimaginary([[y1, y2,] x1, x2,] ch, [attr1, attr2, attr3, [attr4, attr5,\n          attr6]])\n\n\n  y1\n    Y-coordinate.\n  y2\n    Y-coordinate.\n  x1\n    X-coordinate.\n  x2\n    X-coordinate.\n  ch\n    Character to add.\n  attr1\n    Attributes for the character.\n  attr2\n    Attributes for the character.\n  attr3\n    Attributes for the character.\n  attr4\n    Attributes for the character.\n  attr5\n    Attributes for the character.\n  attr6\n    Attributes for the character.\n                ".strip(),
        )

    def parse_function_should_fail(self, s):
        with support.captured_stdout() as stdout:
            with self.assertRaises(SystemExit):
                self.parse_function(s)
        return stdout.getvalue()

    def test_disallowed_grouping__two_top_groups_on_left(self):
        s = self.parse_function_should_fail(
            "\nmodule foo\nfoo.two_top_groups_on_left\n    [\n    group1 : int\n    ]\n    [\n    group2 : int\n    ]\n    param: int\n            "
        )
        self.assertEqual(
            s,
            "Error on line 0:\nFunction two_top_groups_on_left has an unsupported group configuration. (Unexpected state 2.b)\n",
        )

    def test_disallowed_grouping__two_top_groups_on_right(self):
        self.parse_function_should_fail(
            "\nmodule foo\nfoo.two_top_groups_on_right\n    param: int\n    [\n    group1 : int\n    ]\n    [\n    group2 : int\n    ]\n            "
        )

    def test_disallowed_grouping__parameter_after_group_on_right(self):
        self.parse_function_should_fail(
            "\nmodule foo\nfoo.parameter_after_group_on_right\n    param: int\n    [\n    [\n    group1 : int\n    ]\n    group2 : int\n    ]\n            "
        )

    def test_disallowed_grouping__group_after_parameter_on_left(self):
        self.parse_function_should_fail(
            "\nmodule foo\nfoo.group_after_parameter_on_left\n    [\n    group2 : int\n    [\n    group1 : int\n    ]\n    ]\n    param: int\n            "
        )

    def test_disallowed_grouping__empty_group_on_left(self):
        self.parse_function_should_fail(
            "\nmodule foo\nfoo.empty_group\n    [\n    [\n    ]\n    group2 : int\n    ]\n    param: int\n            "
        )

    def test_disallowed_grouping__empty_group_on_right(self):
        self.parse_function_should_fail(
            "\nmodule foo\nfoo.empty_group\n    param: int\n    [\n    [\n    ]\n    group2 : int\n    ]\n            "
        )

    def test_no_parameters(self):
        function = self.parse_function("\nmodule foo\nfoo.bar\n\nDocstring\n\n")
        self.assertEqual("bar($module, /)\n--\n\nDocstring", function.docstring)
        self.assertEqual(1, len(function.parameters))

    def test_init_with_no_parameters(self):
        function = self.parse_function(
            '\nmodule foo\nclass foo.Bar "unused" "notneeded"\nfoo.Bar.__init__\n\nDocstring\n\n',
            signatures_in_block=3,
            function_index=2,
        )
        self.assertEqual("Bar()\n--\n\nDocstring", function.docstring)
        self.assertEqual(1, len(function.parameters))

    def test_illegal_module_line(self):
        self.parse_function_should_fail("\nmodule foo\nfoo.bar => int\n    /\n")

    def test_illegal_c_basename(self):
        self.parse_function_should_fail("\nmodule foo\nfoo.bar as 935\n    /\n")

    def test_single_star(self):
        self.parse_function_should_fail("\nmodule foo\nfoo.bar\n    *\n    *\n")

    def test_parameters_required_after_star_without_initial_parameters_or_docstring(
        self,
    ):
        self.parse_function_should_fail("\nmodule foo\nfoo.bar\n    *\n")

    def test_parameters_required_after_star_without_initial_parameters_with_docstring(
        self,
    ):
        self.parse_function_should_fail(
            "\nmodule foo\nfoo.bar\n    *\nDocstring here.\n"
        )

    def test_parameters_required_after_star_with_initial_parameters_without_docstring(
        self,
    ):
        self.parse_function_should_fail("\nmodule foo\nfoo.bar\n    this: int\n    *\n")

    def test_parameters_required_after_star_with_initial_parameters_and_docstring(self):
        self.parse_function_should_fail(
            "\nmodule foo\nfoo.bar\n    this: int\n    *\nDocstring.\n"
        )

    def test_single_slash(self):
        self.parse_function_should_fail("\nmodule foo\nfoo.bar\n    /\n    /\n")

    def test_mix_star_and_slash(self):
        self.parse_function_should_fail(
            "\nmodule foo\nfoo.bar\n   x: int\n   y: int\n   *\n   z: int\n   /\n"
        )

    def test_parameters_not_permitted_after_slash_for_now(self):
        self.parse_function_should_fail("\nmodule foo\nfoo.bar\n    /\n    x: int\n")

    def test_function_not_at_column_0(self):
        function = self.parse_function(
            "\n  module foo\n  foo.bar\n    x: int\n      Nested docstring here, goeth.\n    *\n    y: str\n  Not at column 0!\n"
        )
        self.assertEqual(
            "\nbar($module, /, x, *, y)\n--\n\nNot at column 0!\n\n  x\n    Nested docstring here, goeth.\n".strip(),
            function.docstring,
        )

    def test_directive(self):
        c = FakeClinic()
        parser = DSLParser(c)
        parser.flag = False
        parser.directives["setflag"] = lambda: setattr(parser, "flag", True)
        block = clinic.Block("setflag")
        parser.parse(block)
        self.assertTrue(parser.flag)

    def test_legacy_converters(self):
        block = self.parse('module os\nos.access\n   path: "s"')
        (module, function) = block.signatures
        self.assertIsInstance(
            function.parameters["path"].converter, clinic.str_converter
        )

    def parse(self, text):
        c = FakeClinic()
        parser = DSLParser(c)
        block = clinic.Block(text)
        parser.parse(block)
        return block

    def parse_function(self, text, signatures_in_block=2, function_index=1):
        block = self.parse(text)
        s = block.signatures
        self.assertEqual(len(s), signatures_in_block)
        assert isinstance(s[0], clinic.Module)
        assert isinstance(s[function_index], clinic.Function)
        return s[function_index]

    def test_scaffolding(self):
        self.assertEqual(repr(clinic.unspecified), "<Unspecified>")
        self.assertEqual(repr(clinic.NULL), "<Null>")
        with support.captured_stdout() as stdout:
            with self.assertRaises(SystemExit):
                clinic.fail(
                    "The igloos are melting!", filename="clown.txt", line_number=69
                )
        self.assertEqual(
            stdout.getvalue(),
            'Error in file "clown.txt" on line 69:\nThe igloos are melting!\n',
        )


class ClinicExternalTest(TestCase):
    maxDiff = None

    def test_external(self):
        source = support.findfile("clinic.test")
        with open(source, "r", encoding="utf-8") as f:
            orig_contents = f.read()
        with os_helper.temp_dir() as tmp_dir:
            testfile = os.path.join(tmp_dir, "clinic.test.c")
            with open(testfile, "w", encoding="utf-8") as f:
                f.write(orig_contents)
            old_mtime_ns = os.stat(testfile).st_mtime_ns
            clinic.parse_file(testfile)
            with open(testfile, "r", encoding="utf-8") as f:
                new_contents = f.read()
            new_mtime_ns = os.stat(testfile).st_mtime_ns
        self.assertEqual(new_contents, orig_contents)
        self.assertEqual(new_mtime_ns, old_mtime_ns)


if __name__ == "__main__":
    unittest.main()
