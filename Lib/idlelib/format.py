"Format all or a selected region (line slice) of text.\n\nRegion formatting options: paragraph, comment block, indent, deindent,\ncomment, uncomment, tabify, and untabify.\n\nFile renamed from paragraph.py with functions added from editor.py.\n"
import re
from tkinter.messagebox import askyesno
from tkinter.simpledialog import askinteger
from idlelib.config import idleConf


class FormatParagraph:
    'Format a paragraph, comment block, or selection to a max width.\n\n    Does basic, standard text formatting, and also understands Python\n    comment blocks. Thus, for editing Python source code, this\n    extension is really only suitable for reformatting these comment\n    blocks or triple-quoted strings.\n\n    Known problems with comment reformatting:\n    * If there is a selection marked, and the first line of the\n      selection is not complete, the block will probably not be detected\n      as comments, and will have the normal "text formatting" rules\n      applied.\n    * If a comment block has leading whitespace that mixes tabs and\n      spaces, they will not be considered part of the same block.\n    * Fancy comments, like this bulleted list, aren\'t handled :-)\n    '

    def __init__(self, editwin):
        self.editwin = editwin

    @classmethod
    def reload(cls):
        cls.max_width = idleConf.GetOption(
            "extensions", "FormatParagraph", "max-width", type="int", default=72
        )

    def close(self):
        self.editwin = None

    def format_paragraph_event(self, event, limit=None):
        "Formats paragraph to a max width specified in idleConf.\n\n        If text is selected, format_paragraph_event will start breaking lines\n        at the max width, starting from the beginning selection.\n\n        If no text is selected, format_paragraph_event uses the current\n        cursor location to determine the paragraph (lines of text surrounded\n        by blank lines) and formats it.\n\n        The length limit parameter is for testing with a known value.\n        "
        limit = self.max_width if (limit is None) else limit
        text = self.editwin.text
        (first, last) = self.editwin.get_selection_indices()
        if first and last:
            data = text.get(first, last)
            comment_header = get_comment_header(data)
        else:
            (first, last, comment_header, data) = find_paragraph(
                text, text.index("insert")
            )
        if comment_header:
            newdata = reformat_comment(data, limit, comment_header)
        else:
            newdata = reformat_paragraph(data, limit)
        text.tag_remove("sel", "1.0", "end")
        if newdata != data:
            text.mark_set("insert", first)
            text.undo_block_start()
            text.delete(first, last)
            text.insert(first, newdata)
            text.undo_block_stop()
        else:
            text.mark_set("insert", last)
        text.see("insert")
        return "break"


FormatParagraph.reload()


def find_paragraph(text, mark):
    "Returns the start/stop indices enclosing the paragraph that mark is in.\n\n    Also returns the comment format string, if any, and paragraph of text\n    between the start/stop indices.\n    "
    (lineno, col) = map(int, mark.split("."))
    line = text.get(("%d.0" % lineno), ("%d.end" % lineno))
    while text.compare(("%d.0" % lineno), "<", "end") and is_all_white(line):
        lineno = lineno + 1
        line = text.get(("%d.0" % lineno), ("%d.end" % lineno))
    first_lineno = lineno
    comment_header = get_comment_header(line)
    comment_header_len = len(comment_header)
    while (get_comment_header(line) == comment_header) and (
        not is_all_white(line[comment_header_len:])
    ):
        lineno = lineno + 1
        line = text.get(("%d.0" % lineno), ("%d.end" % lineno))
    last = "%d.0" % lineno
    lineno = first_lineno - 1
    line = text.get(("%d.0" % lineno), ("%d.end" % lineno))
    while (
        (lineno > 0)
        and (get_comment_header(line) == comment_header)
        and (not is_all_white(line[comment_header_len:]))
    ):
        lineno = lineno - 1
        line = text.get(("%d.0" % lineno), ("%d.end" % lineno))
    first = "%d.0" % (lineno + 1)
    return (first, last, comment_header, text.get(first, last))


def reformat_paragraph(data, limit):
    "Return data reformatted to specified width (limit)."
    lines = data.split("\n")
    i = 0
    n = len(lines)
    while (i < n) and is_all_white(lines[i]):
        i = i + 1
    if i >= n:
        return data
    indent1 = get_indent(lines[i])
    if ((i + 1) < n) and (not is_all_white(lines[(i + 1)])):
        indent2 = get_indent(lines[(i + 1)])
    else:
        indent2 = indent1
    new = lines[:i]
    partial = indent1
    while (i < n) and (not is_all_white(lines[i])):
        words = re.split("(\\s+)", lines[i])
        for j in range(0, len(words), 2):
            word = words[j]
            if not word:
                continue
            if (len((partial + word).expandtabs()) > limit) and (partial != indent1):
                new.append(partial.rstrip())
                partial = indent2
            partial = (partial + word) + " "
            if ((j + 1) < len(words)) and (words[(j + 1)] != " "):
                partial = partial + " "
        i = i + 1
    new.append(partial.rstrip())
    new.extend(lines[i:])
    return "\n".join(new)


def reformat_comment(data, limit, comment_header):
    "Return data reformatted to specified width with comment header."
    lc = len(comment_header)
    data = "\n".join((line[lc:] for line in data.split("\n")))
    format_width = max((limit - len(comment_header)), 20)
    newdata = reformat_paragraph(data, format_width)
    newdata = newdata.split("\n")
    block_suffix = ""
    if not newdata[(-1)]:
        block_suffix = "\n"
        newdata = newdata[:(-1)]
    return "\n".join(((comment_header + line) for line in newdata)) + block_suffix


def is_all_white(line):
    "Return True if line is empty or all whitespace."
    return re.match("^\\s*$", line) is not None


def get_indent(line):
    "Return the initial space or tab indent of line."
    return re.match("^([ \\t]*)", line).group()


def get_comment_header(line):
    "Return string with leading whitespace and '#' from line or ''.\n\n    A null return indicates that the line is not a comment line. A non-\n    null return, such as '    #', will be used to find the other lines of\n    a comment block with the same  indent.\n    "
    m = re.match("^([ \\t]*#*)", line)
    if m is None:
        return ""
    return m.group(1)


_line_indent_re = re.compile("[ \\t]*")


def get_line_indent(line, tabwidth):
    'Return a line\'s indentation as (# chars, effective # of spaces).\n\n    The effective # of spaces is the length after properly "expanding"\n    the tabs into spaces, as done by str.expandtabs(tabwidth).\n    '
    m = _line_indent_re.match(line)
    return (m.end(), len(m.group().expandtabs(tabwidth)))


class FormatRegion:
    "Format selected text (region)."

    def __init__(self, editwin):
        self.editwin = editwin

    def get_region(self):
        "Return line information about the selected text region.\n\n        If text is selected, the first and last indices will be\n        for the selection.  If there is no text selected, the\n        indices will be the current cursor location.\n\n        Return a tuple containing (first index, last index,\n            string representation of text, list of text lines).\n        "
        text = self.editwin.text
        (first, last) = self.editwin.get_selection_indices()
        if first and last:
            head = text.index((first + " linestart"))
            tail = text.index((last + "-1c lineend +1c"))
        else:
            head = text.index("insert linestart")
            tail = text.index("insert lineend +1c")
        chars = text.get(head, tail)
        lines = chars.split("\n")
        return (head, tail, chars, lines)

    def set_region(self, head, tail, chars, lines):
        "Replace the text between the given indices.\n\n        Args:\n            head: Starting index of text to replace.\n            tail: Ending index of text to replace.\n            chars: Expected to be string of current text\n                between head and tail.\n            lines: List of new lines to insert between head\n                and tail.\n        "
        text = self.editwin.text
        newchars = "\n".join(lines)
        if newchars == chars:
            text.bell()
            return
        text.tag_remove("sel", "1.0", "end")
        text.mark_set("insert", head)
        text.undo_block_start()
        text.delete(head, tail)
        text.insert(head, newchars)
        text.undo_block_stop()
        text.tag_add("sel", head, "insert")

    def indent_region_event(self, event=None):
        "Indent region by indentwidth spaces."
        (head, tail, chars, lines) = self.get_region()
        for pos in range(len(lines)):
            line = lines[pos]
            if line:
                (raw, effective) = get_line_indent(line, self.editwin.tabwidth)
                effective = effective + self.editwin.indentwidth
                lines[pos] = self.editwin._make_blanks(effective) + line[raw:]
        self.set_region(head, tail, chars, lines)
        return "break"

    def dedent_region_event(self, event=None):
        "Dedent region by indentwidth spaces."
        (head, tail, chars, lines) = self.get_region()
        for pos in range(len(lines)):
            line = lines[pos]
            if line:
                (raw, effective) = get_line_indent(line, self.editwin.tabwidth)
                effective = max((effective - self.editwin.indentwidth), 0)
                lines[pos] = self.editwin._make_blanks(effective) + line[raw:]
        self.set_region(head, tail, chars, lines)
        return "break"

    def comment_region_event(self, event=None):
        "Comment out each line in region.\n\n        ## is appended to the beginning of each line to comment it out.\n        "
        (head, tail, chars, lines) = self.get_region()
        for pos in range((len(lines) - 1)):
            line = lines[pos]
            lines[pos] = "##" + line
        self.set_region(head, tail, chars, lines)
        return "break"

    def uncomment_region_event(self, event=None):
        "Uncomment each line in region.\n\n        Remove ## or # in the first positions of a line.  If the comment\n        is not in the beginning position, this command will have no effect.\n        "
        (head, tail, chars, lines) = self.get_region()
        for pos in range(len(lines)):
            line = lines[pos]
            if not line:
                continue
            if line[:2] == "##":
                line = line[2:]
            elif line[:1] == "#":
                line = line[1:]
            lines[pos] = line
        self.set_region(head, tail, chars, lines)
        return "break"

    def tabify_region_event(self, event=None):
        "Convert leading spaces to tabs for each line in selected region."
        (head, tail, chars, lines) = self.get_region()
        tabwidth = self._asktabwidth()
        if tabwidth is None:
            return
        for pos in range(len(lines)):
            line = lines[pos]
            if line:
                (raw, effective) = get_line_indent(line, tabwidth)
                (ntabs, nspaces) = divmod(effective, tabwidth)
                lines[pos] = (("\t" * ntabs) + (" " * nspaces)) + line[raw:]
        self.set_region(head, tail, chars, lines)
        return "break"

    def untabify_region_event(self, event=None):
        "Expand tabs to spaces for each line in region."
        (head, tail, chars, lines) = self.get_region()
        tabwidth = self._asktabwidth()
        if tabwidth is None:
            return
        for pos in range(len(lines)):
            lines[pos] = lines[pos].expandtabs(tabwidth)
        self.set_region(head, tail, chars, lines)
        return "break"

    def _asktabwidth(self):
        "Return value for tab width."
        return askinteger(
            "Tab width",
            "Columns per tab? (2-16)",
            parent=self.editwin.text,
            initialvalue=self.editwin.indentwidth,
            minvalue=2,
            maxvalue=16,
        )


class Indents:
    "Change future indents."

    def __init__(self, editwin):
        self.editwin = editwin

    def toggle_tabs_event(self, event):
        editwin = self.editwin
        usetabs = editwin.usetabs
        if askyesno(
            "Toggle tabs",
            (
                (
                    (
                        (("Turn tabs " + ("on", "off")[usetabs]) + "?\nIndent width ")
                        + ("will be", "remains at")[usetabs]
                    )
                    + " 8."
                )
                + "\n Note: a tab is always 8 columns"
            ),
            parent=editwin.text,
        ):
            editwin.usetabs = not usetabs
            editwin.indentwidth = 8
        return "break"

    def change_indentwidth_event(self, event):
        editwin = self.editwin
        new = askinteger(
            "Indent width",
            "New indent width (2-16)\n(Always use 8 when using tabs)",
            parent=editwin.text,
            initialvalue=editwin.indentwidth,
            minvalue=2,
            maxvalue=16,
        )
        if new and (new != editwin.indentwidth) and (not editwin.usetabs):
            editwin.indentwidth = new
        return "break"


class Rstrip:
    def __init__(self, editwin):
        self.editwin = editwin

    def do_rstrip(self, event=None):
        text = self.editwin.text
        undo = self.editwin.undo
        undo.undo_block_start()
        end_line = int(float(text.index("end")))
        for cur in range(1, end_line):
            txt = text.get(("%i.0" % cur), ("%i.end" % cur))
            raw = len(txt)
            cut = len(txt.rstrip())
            if cut < raw:
                text.delete(("%i.%i" % (cur, cut)), ("%i.end" % cur))
        if (text.get("end-2c") == "\n") and (not hasattr(self.editwin, "interp")):
            while (text.index("end-1c") > "1.0") and (text.get("end-3c") == "\n"):
                text.delete("end-3c")
        undo.undo_block_stop()


if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_format", verbosity=2, exit=False)
