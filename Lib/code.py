"Utilities needed to emulate Python's interactive interpreter.\n\n"
import sys
import traceback
from codeop import CommandCompiler, compile_command

__all__ = [
    "InteractiveInterpreter",
    "InteractiveConsole",
    "interact",
    "compile_command",
]


class InteractiveInterpreter:
    "Base class for InteractiveConsole.\n\n    This class deals with parsing and interpreter state (the user's\n    namespace); it doesn't deal with input buffering or prompting or\n    input file naming (the filename is always passed in explicitly).\n\n    "

    def __init__(self, locals=None):
        'Constructor.\n\n        The optional \'locals\' argument specifies the dictionary in\n        which code will be executed; it defaults to a newly created\n        dictionary with key "__name__" set to "__console__" and key\n        "__doc__" set to None.\n\n        '
        if locals is None:
            locals = {"__name__": "__console__", "__doc__": None}
        self.locals = locals
        self.compile = CommandCompiler()

    def runsource(self, source, filename="<input>", symbol="single"):
        "Compile and run some source in the interpreter.\n\n        Arguments are as for compile_command().\n\n        One of several things can happen:\n\n        1) The input is incorrect; compile_command() raised an\n        exception (SyntaxError or OverflowError).  A syntax traceback\n        will be printed by calling the showsyntaxerror() method.\n\n        2) The input is incomplete, and more input is required;\n        compile_command() returned None.  Nothing happens.\n\n        3) The input is complete; compile_command() returned a code\n        object.  The code is executed by calling self.runcode() (which\n        also handles run-time exceptions, except for SystemExit).\n\n        The return value is True in case 2, False in the other cases (unless\n        an exception is raised).  The return value can be used to\n        decide whether to use sys.ps1 or sys.ps2 to prompt the next\n        line.\n\n        "
        try:
            code = self.compile(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            self.showsyntaxerror(filename)
            return False
        if code is None:
            return True
        self.runcode(code)
        return False

    def runcode(self, code):
        "Execute a code object.\n\n        When an exception occurs, self.showtraceback() is called to\n        display a traceback.  All exceptions are caught except\n        SystemExit, which is reraised.\n\n        A note about KeyboardInterrupt: this exception may occur\n        elsewhere in this code, and may not always be caught.  The\n        caller should be prepared to deal with it.\n\n        "
        try:
            exec(code, self.locals)
        except SystemExit:
            raise
        except:
            self.showtraceback()

    def showsyntaxerror(self, filename=None):
        "Display the syntax error that just occurred.\n\n        This doesn't display a stack trace because there isn't one.\n\n        If a filename is given, it is stuffed in the exception instead\n        of what was there before (because Python's parser always uses\n        \"<string>\" when reading from a string).\n\n        The output is written by self.write(), below.\n\n        "
        (type, value, tb) = sys.exc_info()
        sys.last_type = type
        sys.last_value = value
        sys.last_traceback = tb
        if filename and (type is SyntaxError):
            try:
                (msg, (dummy_filename, lineno, offset, line)) = value.args
            except ValueError:
                pass
            else:
                value = SyntaxError(msg, (filename, lineno, offset, line))
                sys.last_value = value
        if sys.excepthook is sys.__excepthook__:
            lines = traceback.format_exception_only(type, value)
            self.write("".join(lines))
        else:
            sys.excepthook(type, value, tb)

    def showtraceback(self):
        "Display the exception that just occurred.\n\n        We remove the first stack item because it is our own code.\n\n        The output is written by self.write(), below.\n\n        "
        (sys.last_type, sys.last_value, last_tb) = ei = sys.exc_info()
        sys.last_traceback = last_tb
        try:
            lines = traceback.format_exception(ei[0], ei[1], last_tb.tb_next)
            if sys.excepthook is sys.__excepthook__:
                self.write("".join(lines))
            else:
                sys.excepthook(ei[0], ei[1], last_tb)
        finally:
            last_tb = ei = None

    def write(self, data):
        "Write a string.\n\n        The base implementation writes to sys.stderr; a subclass may\n        replace this with a different implementation.\n\n        "
        sys.stderr.write(data)


class InteractiveConsole(InteractiveInterpreter):
    "Closely emulate the behavior of the interactive Python interpreter.\n\n    This class builds on InteractiveInterpreter and adds prompting\n    using the familiar sys.ps1 and sys.ps2, and input buffering.\n\n    "

    def __init__(self, locals=None, filename="<console>"):
        "Constructor.\n\n        The optional locals argument will be passed to the\n        InteractiveInterpreter base class.\n\n        The optional filename argument should specify the (file)name\n        of the input stream; it will show up in tracebacks.\n\n        "
        InteractiveInterpreter.__init__(self, locals)
        self.filename = filename
        self.resetbuffer()

    def resetbuffer(self):
        "Reset the input buffer."
        self.buffer = []

    def interact(self, banner=None, exitmsg=None):
        "Closely emulate the interactive Python console.\n\n        The optional banner argument specifies the banner to print\n        before the first interaction; by default it prints a banner\n        similar to the one printed by the real Python interpreter,\n        followed by the current class name in parentheses (so as not\n        to confuse this with the real interpreter -- since it's so\n        close!).\n\n        The optional exitmsg argument specifies the exit message\n        printed when exiting. Pass the empty string to suppress\n        printing an exit message. If exitmsg is not given or None,\n        a default message is printed.\n\n        "
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
        cprt = 'Type "help", "copyright", "credits" or "license" for more information.'
        if banner is None:
            self.write(
                (
                    "Python %s on %s\n%s\n(%s)\n"
                    % (sys.version, sys.platform, cprt, self.__class__.__name__)
                )
            )
        elif banner:
            self.write(("%s\n" % str(banner)))
        more = 0
        while 1:
            try:
                if more:
                    prompt = sys.ps2
                else:
                    prompt = sys.ps1
                try:
                    line = self.raw_input(prompt)
                except EOFError:
                    self.write("\n")
                    break
                else:
                    more = self.push(line)
            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0
        if exitmsg is None:
            self.write(("now exiting %s...\n" % self.__class__.__name__))
        elif exitmsg != "":
            self.write(("%s\n" % exitmsg))

    def push(self, line):
        "Push a line to the interpreter.\n\n        The line should not have a trailing newline; it may have\n        internal newlines.  The line is appended to a buffer and the\n        interpreter's runsource() method is called with the\n        concatenated contents of the buffer as source.  If this\n        indicates that the command was executed or invalid, the buffer\n        is reset; otherwise, the command is incomplete, and the buffer\n        is left as it was after the line was appended.  The return\n        value is 1 if more input is required, 0 if the line was dealt\n        with in some way (this is the same as runsource()).\n\n        "
        self.buffer.append(line)
        source = "\n".join(self.buffer)
        more = self.runsource(source, self.filename)
        if not more:
            self.resetbuffer()
        return more

    def raw_input(self, prompt=""):
        "Write a prompt and read a line.\n\n        The returned line does not include the trailing newline.\n        When the user enters the EOF key sequence, EOFError is raised.\n\n        The base implementation uses the built-in function\n        input(); a subclass may replace this with a different\n        implementation.\n\n        "
        return input(prompt)


def interact(banner=None, readfunc=None, local=None, exitmsg=None):
    "Closely emulate the interactive Python interpreter.\n\n    This is a backwards compatible interface to the InteractiveConsole\n    class.  When readfunc is not specified, it attempts to import the\n    readline module to enable GNU readline if it is available.\n\n    Arguments (all optional, all default to None):\n\n    banner -- passed to InteractiveConsole.interact()\n    readfunc -- if not None, replaces InteractiveConsole.raw_input()\n    local -- passed to InteractiveInterpreter.__init__()\n    exitmsg -- passed to InteractiveConsole.interact()\n\n    "
    console = InteractiveConsole(local)
    if readfunc is not None:
        console.raw_input = readfunc
    else:
        try:
            import readline
        except ImportError:
            pass
    console.interact(banner, exitmsg)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q", action="store_true", help="don't print version and copyright messages"
    )
    args = parser.parse_args()
    if args.q or sys.flags.quiet:
        banner = ""
    else:
        banner = None
    interact(banner)
