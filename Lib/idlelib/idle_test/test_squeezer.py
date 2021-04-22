"Test squeezer, coverage 95%"
from textwrap import dedent
from tkinter import Text, Tk
import unittest
from unittest.mock import Mock, NonCallableMagicMock, patch, sentinel, ANY
from test.support import requires
from idlelib.config import idleConf
from idlelib.squeezer import count_lines_with_wrapping, ExpandingButton, Squeezer
from idlelib import macosx
from idlelib.textview import view_text
from idlelib.tooltip import Hovertip
from idlelib.pyshell import PyShell

SENTINEL_VALUE = sentinel.SENTINEL_VALUE


def get_test_tk_root(test_instance):
    "Helper for tests: Create a root Tk object."
    requires("gui")
    root = Tk()
    root.withdraw()

    def cleanup_root():
        root.update_idletasks()
        root.destroy()

    test_instance.addCleanup(cleanup_root)
    return root


class CountLinesTest(unittest.TestCase):
    "Tests for the count_lines_with_wrapping function."

    def check(self, expected, text, linewidth):
        return self.assertEqual(expected, count_lines_with_wrapping(text, linewidth))

    def test_count_empty(self):
        "Test with an empty string."
        self.assertEqual(count_lines_with_wrapping(""), 0)

    def test_count_begins_with_empty_line(self):
        "Test with a string which begins with a newline."
        self.assertEqual(count_lines_with_wrapping("\ntext"), 2)

    def test_count_ends_with_empty_line(self):
        "Test with a string which ends with a newline."
        self.assertEqual(count_lines_with_wrapping("text\n"), 1)

    def test_count_several_lines(self):
        "Test with several lines of text."
        self.assertEqual(count_lines_with_wrapping("1\n2\n3\n"), 3)

    def test_empty_lines(self):
        self.check(expected=1, text="\n", linewidth=80)
        self.check(expected=2, text="\n\n", linewidth=80)
        self.check(expected=10, text=("\n" * 10), linewidth=80)

    def test_long_line(self):
        self.check(expected=3, text=("a" * 200), linewidth=80)
        self.check(expected=3, text=(("a" * 200) + "\n"), linewidth=80)

    def test_several_lines_different_lengths(self):
        text = dedent(
            "            13 characters\n            43 is the number of characters on this line\n\n            7 chars\n            13 characters"
        )
        self.check(expected=5, text=text, linewidth=80)
        self.check(expected=5, text=(text + "\n"), linewidth=80)
        self.check(expected=6, text=text, linewidth=40)
        self.check(expected=7, text=text, linewidth=20)
        self.check(expected=11, text=text, linewidth=10)


class SqueezerTest(unittest.TestCase):
    "Tests for the Squeezer class."

    def make_mock_editor_window(self, with_text_widget=False):
        "Create a mock EditorWindow instance."
        editwin = NonCallableMagicMock()
        editwin.width = 80
        if with_text_widget:
            editwin.root = get_test_tk_root(self)
            text_widget = self.make_text_widget(root=editwin.root)
            editwin.text = editwin.per.bottom = text_widget
        return editwin

    def make_squeezer_instance(self, editor_window=None):
        "Create an actual Squeezer instance with a mock EditorWindow."
        if editor_window is None:
            editor_window = self.make_mock_editor_window()
        squeezer = Squeezer(editor_window)
        return squeezer

    def make_text_widget(self, root=None):
        if root is None:
            root = get_test_tk_root(self)
        text_widget = Text(root)
        text_widget["font"] = ("Courier", 10)
        text_widget.mark_set("iomark", "1.0")
        return text_widget

    def set_idleconf_option_with_cleanup(self, configType, section, option, value):
        prev_val = idleConf.GetOption(configType, section, option)
        idleConf.SetOption(configType, section, option, value)
        self.addCleanup(idleConf.SetOption, configType, section, option, prev_val)

    def test_count_lines(self):
        "Test Squeezer.count_lines() with various inputs."
        editwin = self.make_mock_editor_window()
        squeezer = self.make_squeezer_instance(editwin)
        for (text_code, line_width, expected) in [
            ("'\\n'", 80, 1),
            ("'\\n' * 3", 80, 3),
            ("'a' * 40 + '\\n'", 80, 1),
            ("'a' * 80 + '\\n'", 80, 1),
            ("'a' * 200 + '\\n'", 80, 3),
            ("'aa\\t' * 20", 80, 2),
            ("'aa\\t' * 21", 80, 3),
            ("'aa\\t' * 20", 40, 4),
        ]:
            with self.subTest(
                text_code=text_code, line_width=line_width, expected=expected
            ):
                text = eval(text_code)
                with patch.object(editwin, "width", line_width):
                    self.assertEqual(squeezer.count_lines(text), expected)

    def test_init(self):
        "Test the creation of Squeezer instances."
        editwin = self.make_mock_editor_window()
        squeezer = self.make_squeezer_instance(editwin)
        self.assertIs(squeezer.editwin, editwin)
        self.assertEqual(squeezer.expandingbuttons, [])

    def test_write_no_tags(self):
        "Test Squeezer's overriding of the EditorWindow's write() method."
        editwin = self.make_mock_editor_window()
        for text in ["", "TEXT", ("LONG TEXT" * 1000), ("MANY_LINES\n" * 100)]:
            editwin.write = orig_write = Mock(return_value=SENTINEL_VALUE)
            squeezer = self.make_squeezer_instance(editwin)
            self.assertEqual(squeezer.editwin.write(text, ()), SENTINEL_VALUE)
            self.assertEqual(orig_write.call_count, 1)
            orig_write.assert_called_with(text, ())
            self.assertEqual(len(squeezer.expandingbuttons), 0)

    def test_write_not_stdout(self):
        "Test Squeezer's overriding of the EditorWindow's write() method."
        for text in ["", "TEXT", ("LONG TEXT" * 1000), ("MANY_LINES\n" * 100)]:
            editwin = self.make_mock_editor_window()
            editwin.write.return_value = SENTINEL_VALUE
            orig_write = editwin.write
            squeezer = self.make_squeezer_instance(editwin)
            self.assertEqual(squeezer.editwin.write(text, "stderr"), SENTINEL_VALUE)
            self.assertEqual(orig_write.call_count, 1)
            orig_write.assert_called_with(text, "stderr")
            self.assertEqual(len(squeezer.expandingbuttons), 0)

    def test_write_stdout(self):
        "Test Squeezer's overriding of the EditorWindow's write() method."
        editwin = self.make_mock_editor_window()
        for text in ["", "TEXT"]:
            editwin.write = orig_write = Mock(return_value=SENTINEL_VALUE)
            squeezer = self.make_squeezer_instance(editwin)
            squeezer.auto_squeeze_min_lines = 50
            self.assertEqual(squeezer.editwin.write(text, "stdout"), SENTINEL_VALUE)
            self.assertEqual(orig_write.call_count, 1)
            orig_write.assert_called_with(text, "stdout")
            self.assertEqual(len(squeezer.expandingbuttons), 0)
        for text in [("LONG TEXT" * 1000), ("MANY_LINES\n" * 100)]:
            editwin.write = orig_write = Mock(return_value=SENTINEL_VALUE)
            squeezer = self.make_squeezer_instance(editwin)
            squeezer.auto_squeeze_min_lines = 50
            self.assertEqual(squeezer.editwin.write(text, "stdout"), None)
            self.assertEqual(orig_write.call_count, 0)
            self.assertEqual(len(squeezer.expandingbuttons), 1)

    def test_auto_squeeze(self):
        "Test that the auto-squeezing creates an ExpandingButton properly."
        editwin = self.make_mock_editor_window(with_text_widget=True)
        text_widget = editwin.text
        squeezer = self.make_squeezer_instance(editwin)
        squeezer.auto_squeeze_min_lines = 5
        squeezer.count_lines = Mock(return_value=6)
        editwin.write(("TEXT\n" * 6), "stdout")
        self.assertEqual(text_widget.get("1.0", "end"), "\n")
        self.assertEqual(len(squeezer.expandingbuttons), 1)

    def test_squeeze_current_text_event(self):
        "Test the squeeze_current_text event."
        for tag_name in ["stdout", "stderr"]:
            editwin = self.make_mock_editor_window(with_text_widget=True)
            text_widget = editwin.text
            squeezer = self.make_squeezer_instance(editwin)
            squeezer.count_lines = Mock(return_value=6)
            text_widget.insert("1.0", "SOME\nTEXT\n", tag_name)
            text_widget.mark_set("insert", "1.0")
            self.assertEqual(text_widget.get("1.0", "end"), "SOME\nTEXT\n\n")
            self.assertEqual(len(squeezer.expandingbuttons), 0)
            retval = squeezer.squeeze_current_text_event(event=Mock())
            self.assertEqual(retval, "break")
            self.assertEqual(text_widget.get("1.0", "end"), "\n\n")
            self.assertEqual(len(squeezer.expandingbuttons), 1)
            self.assertEqual(squeezer.expandingbuttons[0].s, "SOME\nTEXT")
            squeezer.expandingbuttons[0].expand(event=Mock())
            self.assertEqual(text_widget.get("1.0", "end"), "SOME\nTEXT\n\n")
            self.assertEqual(len(squeezer.expandingbuttons), 0)

    def test_squeeze_current_text_event_no_allowed_tags(self):
        "Test that the event doesn't squeeze text without a relevant tag."
        editwin = self.make_mock_editor_window(with_text_widget=True)
        text_widget = editwin.text
        squeezer = self.make_squeezer_instance(editwin)
        squeezer.count_lines = Mock(return_value=6)
        text_widget.insert("1.0", "SOME\nTEXT\n", "TAG")
        text_widget.mark_set("insert", "1.0")
        self.assertEqual(text_widget.get("1.0", "end"), "SOME\nTEXT\n\n")
        self.assertEqual(len(squeezer.expandingbuttons), 0)
        retval = squeezer.squeeze_current_text_event(event=Mock())
        self.assertEqual(retval, "break")
        self.assertEqual(text_widget.get("1.0", "end"), "SOME\nTEXT\n\n")
        self.assertEqual(len(squeezer.expandingbuttons), 0)

    def test_squeeze_text_before_existing_squeezed_text(self):
        "Test squeezing text before existing squeezed text."
        editwin = self.make_mock_editor_window(with_text_widget=True)
        text_widget = editwin.text
        squeezer = self.make_squeezer_instance(editwin)
        squeezer.count_lines = Mock(return_value=6)
        text_widget.insert("1.0", "SOME\nTEXT\n", "stdout")
        text_widget.mark_set("insert", "1.0")
        squeezer.squeeze_current_text_event(event=Mock())
        self.assertEqual(len(squeezer.expandingbuttons), 1)
        text_widget.insert("1.0", "MORE\nSTUFF\n", "stdout")
        text_widget.mark_set("insert", "1.0")
        retval = squeezer.squeeze_current_text_event(event=Mock())
        self.assertEqual(retval, "break")
        self.assertEqual(text_widget.get("1.0", "end"), "\n\n\n")
        self.assertEqual(len(squeezer.expandingbuttons), 2)
        self.assertTrue(
            text_widget.compare(
                squeezer.expandingbuttons[0], "<", squeezer.expandingbuttons[1]
            )
        )

    def test_reload(self):
        "Test the reload() class-method."
        editwin = self.make_mock_editor_window(with_text_widget=True)
        squeezer = self.make_squeezer_instance(editwin)
        orig_auto_squeeze_min_lines = squeezer.auto_squeeze_min_lines
        new_auto_squeeze_min_lines = orig_auto_squeeze_min_lines + 10
        self.set_idleconf_option_with_cleanup(
            "main", "PyShell", "auto-squeeze-min-lines", str(new_auto_squeeze_min_lines)
        )
        Squeezer.reload()
        self.assertEqual(squeezer.auto_squeeze_min_lines, new_auto_squeeze_min_lines)

    def test_reload_no_squeezer_instances(self):
        "Test that Squeezer.reload() runs without any instances existing."
        Squeezer.reload()


class ExpandingButtonTest(unittest.TestCase):
    "Tests for the ExpandingButton class."

    def make_mock_squeezer(self):
        "Helper for tests: Create a mock Squeezer object."
        root = get_test_tk_root(self)
        squeezer = Mock()
        squeezer.editwin.text = Text(root)
        squeezer.auto_squeeze_min_lines = 50
        return squeezer

    @patch("idlelib.squeezer.Hovertip", autospec=Hovertip)
    def test_init(self, MockHovertip):
        "Test the simplest creation of an ExpandingButton."
        squeezer = self.make_mock_squeezer()
        text_widget = squeezer.editwin.text
        expandingbutton = ExpandingButton("TEXT", "TAGS", 50, squeezer)
        self.assertEqual(expandingbutton.s, "TEXT")
        self.assertEqual(expandingbutton.master, text_widget)
        self.assertTrue(("50 lines" in expandingbutton.cget("text")))
        self.assertEqual(text_widget.get("1.0", "end"), "\n")
        self.assertIn("<Double-Button-1>", expandingbutton.bind())
        right_button_code = "<Button-%s>" % ("2" if macosx.isAquaTk() else "3")
        self.assertIn(right_button_code, expandingbutton.bind())
        self.assertEqual(MockHovertip.call_count, 1)
        MockHovertip.assert_called_with(expandingbutton, ANY, hover_delay=ANY)
        tooltip_text = MockHovertip.call_args[0][1]
        self.assertIn("right-click", tooltip_text.lower())

    def test_expand(self):
        "Test the expand event."
        squeezer = self.make_mock_squeezer()
        expandingbutton = ExpandingButton("TEXT", "TAGS", 50, squeezer)
        text_widget = expandingbutton.text
        text_widget.window_create("1.0", window=expandingbutton)
        expandingbutton.base_text = expandingbutton.text
        retval = expandingbutton.expand(event=Mock())
        self.assertEqual(retval, None)
        self.assertEqual(text_widget.get("1.0", "end"), "TEXT\n")
        text_end_index = text_widget.index("end-1c")
        self.assertEqual(text_widget.get("1.0", text_end_index), "TEXT")
        self.assertEqual(
            text_widget.tag_nextrange("TAGS", "1.0"), ("1.0", text_end_index)
        )
        self.assertEqual(squeezer.expandingbuttons.remove.call_count, 1)
        squeezer.expandingbuttons.remove.assert_called_with(expandingbutton)

    def test_expand_dangerous_oupput(self):
        "Test that expanding very long output asks user for confirmation."
        squeezer = self.make_mock_squeezer()
        text = "a" * (10 ** 5)
        expandingbutton = ExpandingButton(text, "TAGS", 50, squeezer)
        expandingbutton.set_is_dangerous()
        self.assertTrue(expandingbutton.is_dangerous)
        text_widget = expandingbutton.text
        text_widget.window_create("1.0", window=expandingbutton)
        expandingbutton.base_text = expandingbutton.text
        with patch("idlelib.squeezer.messagebox") as mock_msgbox:
            mock_msgbox.askokcancel.return_value = False
            mock_msgbox.askyesno.return_value = False
            retval = expandingbutton.expand(event=Mock())
        self.assertEqual(retval, "break")
        self.assertEqual(expandingbutton.text.get("1.0", "end-1c"), "")
        with patch("idlelib.squeezer.messagebox") as mock_msgbox:
            mock_msgbox.askokcancel.return_value = True
            mock_msgbox.askyesno.return_value = True
            retval = expandingbutton.expand(event=Mock())
        self.assertEqual(retval, None)
        self.assertEqual(expandingbutton.text.get("1.0", "end-1c"), text)

    def test_copy(self):
        "Test the copy event."
        squeezer = self.make_mock_squeezer()
        expandingbutton = ExpandingButton("TEXT", "TAGS", 50, squeezer)
        expandingbutton.clipboard_clear = Mock()
        expandingbutton.clipboard_append = Mock()
        retval = expandingbutton.copy(event=Mock())
        self.assertEqual(retval, None)
        self.assertEqual(expandingbutton.clipboard_clear.call_count, 1)
        self.assertEqual(expandingbutton.clipboard_append.call_count, 1)
        expandingbutton.clipboard_append.assert_called_with("TEXT")

    def test_view(self):
        "Test the view event."
        squeezer = self.make_mock_squeezer()
        expandingbutton = ExpandingButton("TEXT", "TAGS", 50, squeezer)
        expandingbutton.selection_own = Mock()
        with patch("idlelib.squeezer.view_text", autospec=view_text) as mock_view_text:
            expandingbutton.view(event=Mock())
            self.assertEqual(mock_view_text.call_count, 1)
            self.assertEqual(mock_view_text.call_args[0][2], "TEXT")

    def test_rmenu(self):
        "Test the context menu."
        squeezer = self.make_mock_squeezer()
        expandingbutton = ExpandingButton("TEXT", "TAGS", 50, squeezer)
        with patch("tkinter.Menu") as mock_Menu:
            mock_menu = Mock()
            mock_Menu.return_value = mock_menu
            mock_event = Mock()
            mock_event.x = 10
            mock_event.y = 10
            expandingbutton.context_menu_event(event=mock_event)
            self.assertEqual(
                mock_menu.add_command.call_count, len(expandingbutton.rmenu_specs)
            )
            for (label, *data) in expandingbutton.rmenu_specs:
                mock_menu.add_command.assert_any_call(label=label, command=ANY)


if __name__ == "__main__":
    unittest.main(verbosity=2)
