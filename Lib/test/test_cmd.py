"\nTest script for the 'cmd' module\nOriginal by Michael Schneider\n"
import cmd
import sys
import unittest
import io
from test import support


class samplecmdclass(cmd.Cmd):
    '\n    Instance the sampleclass:\n    >>> mycmd = samplecmdclass()\n\n    Test for the function parseline():\n    >>> mycmd.parseline("")\n    (None, None, \'\')\n    >>> mycmd.parseline("?")\n    (\'help\', \'\', \'help \')\n    >>> mycmd.parseline("?help")\n    (\'help\', \'help\', \'help help\')\n    >>> mycmd.parseline("!")\n    (\'shell\', \'\', \'shell \')\n    >>> mycmd.parseline("!command")\n    (\'shell\', \'command\', \'shell command\')\n    >>> mycmd.parseline("func")\n    (\'func\', \'\', \'func\')\n    >>> mycmd.parseline("func arg1")\n    (\'func\', \'arg1\', \'func arg1\')\n\n\n    Test for the function onecmd():\n    >>> mycmd.onecmd("")\n    >>> mycmd.onecmd("add 4 5")\n    9\n    >>> mycmd.onecmd("")\n    9\n    >>> mycmd.onecmd("test")\n    *** Unknown syntax: test\n\n    Test for the function emptyline():\n    >>> mycmd.emptyline()\n    *** Unknown syntax: test\n\n    Test for the function default():\n    >>> mycmd.default("default")\n    *** Unknown syntax: default\n\n    Test for the function completedefault():\n    >>> mycmd.completedefault()\n    This is the completedefault method\n    >>> mycmd.completenames("a")\n    [\'add\']\n\n    Test for the function completenames():\n    >>> mycmd.completenames("12")\n    []\n    >>> mycmd.completenames("help")\n    [\'help\']\n\n    Test for the function complete_help():\n    >>> mycmd.complete_help("a")\n    [\'add\']\n    >>> mycmd.complete_help("he")\n    [\'help\']\n    >>> mycmd.complete_help("12")\n    []\n    >>> sorted(mycmd.complete_help(""))\n    [\'add\', \'exit\', \'help\', \'shell\']\n\n    Test for the function do_help():\n    >>> mycmd.do_help("testet")\n    *** No help on testet\n    >>> mycmd.do_help("add")\n    help text for add\n    >>> mycmd.onecmd("help add")\n    help text for add\n    >>> mycmd.do_help("")\n    <BLANKLINE>\n    Documented commands (type help <topic>):\n    ========================================\n    add  help\n    <BLANKLINE>\n    Undocumented commands:\n    ======================\n    exit  shell\n    <BLANKLINE>\n\n    Test for the function print_topics():\n    >>> mycmd.print_topics("header", ["command1", "command2"], 2 ,10)\n    header\n    ======\n    command1\n    command2\n    <BLANKLINE>\n\n    Test for the function columnize():\n    >>> mycmd.columnize([str(i) for i in range(20)])\n    0  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15  16  17  18  19\n    >>> mycmd.columnize([str(i) for i in range(20)], 10)\n    0  7   14\n    1  8   15\n    2  9   16\n    3  10  17\n    4  11  18\n    5  12  19\n    6  13\n\n    This is an interactive test, put some commands in the cmdqueue attribute\n    and let it execute\n    This test includes the preloop(), postloop(), default(), emptyline(),\n    parseline(), do_help() functions\n    >>> mycmd.use_rawinput=0\n    >>> mycmd.cmdqueue=["", "add", "add 4 5", "help", "help add","exit"]\n    >>> mycmd.cmdloop()\n    Hello from preloop\n    help text for add\n    *** invalid number of arguments\n    9\n    <BLANKLINE>\n    Documented commands (type help <topic>):\n    ========================================\n    add  help\n    <BLANKLINE>\n    Undocumented commands:\n    ======================\n    exit  shell\n    <BLANKLINE>\n    help text for add\n    Hello from postloop\n    '

    def preloop(self):
        print("Hello from preloop")

    def postloop(self):
        print("Hello from postloop")

    def completedefault(self, *ignored):
        print("This is the completedefault method")

    def complete_command(self):
        print("complete command")

    def do_shell(self, s):
        pass

    def do_add(self, s):
        l = s.split()
        if len(l) != 2:
            print("*** invalid number of arguments")
            return
        try:
            l = [int(i) for i in l]
        except ValueError:
            print("*** arguments should be numbers")
            return
        print((l[0] + l[1]))

    def help_add(self):
        print("help text for add")
        return

    def do_exit(self, arg):
        return True


class TestAlternateInput(unittest.TestCase):
    class simplecmd(cmd.Cmd):
        def do_print(self, args):
            print(args, file=self.stdout)

        def do_EOF(self, args):
            return True

    class simplecmd2(simplecmd):
        def do_EOF(self, args):
            print("*** Unknown syntax: EOF", file=self.stdout)
            return True

    def test_file_with_missing_final_nl(self):
        input = io.StringIO("print test\nprint test2")
        output = io.StringIO()
        cmd = self.simplecmd(stdin=input, stdout=output)
        cmd.use_rawinput = False
        cmd.cmdloop()
        self.assertMultiLineEqual(output.getvalue(), "(Cmd) test\n(Cmd) test2\n(Cmd) ")

    def test_input_reset_at_EOF(self):
        input = io.StringIO("print test\nprint test2")
        output = io.StringIO()
        cmd = self.simplecmd2(stdin=input, stdout=output)
        cmd.use_rawinput = False
        cmd.cmdloop()
        self.assertMultiLineEqual(
            output.getvalue(),
            "(Cmd) test\n(Cmd) test2\n(Cmd) *** Unknown syntax: EOF\n",
        )
        input = io.StringIO("print \n\n")
        output = io.StringIO()
        cmd.stdin = input
        cmd.stdout = output
        cmd.cmdloop()
        self.assertMultiLineEqual(
            output.getvalue(), "(Cmd) \n(Cmd) \n(Cmd) *** Unknown syntax: EOF\n"
        )


def test_main(verbose=None):
    from test import test_cmd

    support.run_doctest(test_cmd, verbose)
    support.run_unittest(TestAlternateInput)


def test_coverage(coverdir):
    trace = support.import_module("trace")
    tracer = trace.Trace(
        ignoredirs=[sys.base_prefix, sys.base_exec_prefix], trace=0, count=1
    )
    tracer.run("import importlib; importlib.reload(cmd); test_main()")
    r = tracer.results()
    print("Writing coverage results...")
    r.write_results(show_missing=True, summary=True, coverdir=coverdir)


if __name__ == "__main__":
    if "-c" in sys.argv:
        test_coverage("/tmp/cmd.cover")
    elif "-i" in sys.argv:
        samplecmdclass().cmdloop()
    else:
        test_main()
