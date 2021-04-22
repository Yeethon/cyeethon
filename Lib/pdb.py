"\nThe Python Debugger Pdb\n=======================\n\nTo use the debugger in its simplest form:\n\n        >>> import pdb\n        >>> pdb.run('<a statement>')\n\nThe debugger's prompt is '(Pdb) '.  This will stop in the first\nfunction call in <a statement>.\n\nAlternatively, if a statement terminated with an unhandled exception,\nyou can use pdb's post-mortem facility to inspect the contents of the\ntraceback:\n\n        >>> <a statement>\n        <exception traceback>\n        >>> import pdb\n        >>> pdb.pm()\n\nThe commands recognized by the debugger are listed in the next\nsection.  Most can be abbreviated as indicated; e.g., h(elp) means\nthat 'help' can be typed as 'h' or 'help' (but not as 'he' or 'hel',\nnor as 'H' or 'Help' or 'HELP').  Optional arguments are enclosed in\nsquare brackets.  Alternatives in the command syntax are separated\nby a vertical bar (|).\n\nA blank line repeats the previous command literally, except for\n'list', where it lists the next 11 lines.\n\nCommands that the debugger doesn't recognize are assumed to be Python\nstatements and are executed in the context of the program being\ndebugged.  Python statements can also be prefixed with an exclamation\npoint ('!').  This is a powerful way to inspect the program being\ndebugged; it is even possible to change variables or call functions.\nWhen an exception occurs in such a statement, the exception name is\nprinted but the debugger's state is not changed.\n\nThe debugger supports aliases, which can save typing.  And aliases can\nhave parameters (see the alias help entry) which allows one a certain\nlevel of adaptability to the context under examination.\n\nMultiple commands may be entered on a single line, separated by the\npair ';;'.  No intelligence is applied to separating the commands; the\ninput is split at the first ';;', even if it is in the middle of a\nquoted string.\n\nIf a file \".pdbrc\" exists in your home directory or in the current\ndirectory, it is read in and executed as if it had been typed at the\ndebugger prompt.  This is particularly useful for aliases.  If both\nfiles exist, the one in the home directory is read first and aliases\ndefined there can be overridden by the local file.  This behavior can be\ndisabled by passing the \"readrc=False\" argument to the Pdb constructor.\n\nAside from aliases, the debugger is not directly programmable; but it\nis implemented as a class from which you can derive your own debugger\nclass, which you can make as fancy as you like.\n\n\nDebugger commands\n=================\n\n"
import os
import io
import re
import sys
import cmd
import bdb
import dis
import code
import glob
import pprint
import signal
import inspect
import tokenize
import traceback
import linecache


class Restart(Exception):
    "Causes a debugger to be restarted for the debugged python program."
    pass


__all__ = [
    "run",
    "pm",
    "Pdb",
    "runeval",
    "runctx",
    "runcall",
    "set_trace",
    "post_mortem",
    "help",
]


def find_function(funcname, filename):
    cre = re.compile(("def\\s+%s\\s*[(]" % re.escape(funcname)))
    try:
        fp = tokenize.open(filename)
    except OSError:
        return None
    with fp:
        for (lineno, line) in enumerate(fp, start=1):
            if cre.match(line):
                return (funcname, filename, lineno)
    return None


def getsourcelines(obj):
    (lines, lineno) = inspect.findsource(obj)
    if inspect.isframe(obj) and (obj.f_globals is obj.f_locals):
        return (lines, 1)
    elif inspect.ismodule(obj):
        return (lines, 1)
    return (inspect.getblock(lines[lineno:]), (lineno + 1))


def lasti2lineno(code, lasti):
    linestarts = list(dis.findlinestarts(code))
    linestarts.reverse()
    for (i, lineno) in linestarts:
        if lasti >= i:
            return lineno
    return 0


class _rstr(str):
    "String that doesn't quote its repr."

    def __repr__(self):
        return self


line_prefix = "\n-> "


class Pdb(bdb.Bdb, cmd.Cmd):
    _previous_sigint_handler = None

    def __init__(
        self,
        completekey="tab",
        stdin=None,
        stdout=None,
        skip=None,
        nosigint=False,
        readrc=True,
    ):
        bdb.Bdb.__init__(self, skip=skip)
        cmd.Cmd.__init__(self, completekey, stdin, stdout)
        sys.audit("pdb.Pdb")
        if stdout:
            self.use_rawinput = 0
        self.prompt = "(Pdb) "
        self.aliases = {}
        self.displaying = {}
        self.mainpyfile = ""
        self._wait_for_mainpyfile = False
        self.tb_lineno = {}
        try:
            import readline

            readline.set_completer_delims(" \t\n`@#$%^&*()=+[{]}\\|;:'\",<>?")
        except ImportError:
            pass
        self.allow_kbdint = False
        self.nosigint = nosigint
        self.rcLines = []
        if readrc:
            try:
                with open(os.path.expanduser("~/.pdbrc")) as rcFile:
                    self.rcLines.extend(rcFile)
            except OSError:
                pass
            try:
                with open(".pdbrc") as rcFile:
                    self.rcLines.extend(rcFile)
            except OSError:
                pass
        self.commands = {}
        self.commands_doprompt = {}
        self.commands_silent = {}
        self.commands_defining = False
        self.commands_bnum = None

    def sigint_handler(self, signum, frame):
        if self.allow_kbdint:
            raise KeyboardInterrupt
        self.message("\nProgram interrupted. (Use 'cont' to resume).")
        self.set_step()
        self.set_trace(frame)

    def reset(self):
        bdb.Bdb.reset(self)
        self.forget()

    def forget(self):
        self.lineno = None
        self.stack = []
        self.curindex = 0
        self.curframe = None
        self.tb_lineno.clear()

    def setup(self, f, tb):
        self.forget()
        (self.stack, self.curindex) = self.get_stack(f, tb)
        while tb:
            lineno = lasti2lineno(tb.tb_frame.f_code, tb.tb_lasti)
            self.tb_lineno[tb.tb_frame] = lineno
            tb = tb.tb_next
        self.curframe = self.stack[self.curindex][0]
        self.curframe_locals = self.curframe.f_locals
        return self.execRcLines()

    def execRcLines(self):
        if not self.rcLines:
            return
        rcLines = self.rcLines
        rcLines.reverse()
        self.rcLines = []
        while rcLines:
            line = rcLines.pop().strip()
            if line and (line[0] != "#"):
                if self.onecmd(line):
                    self.rcLines += reversed(rcLines)
                    return True

    def user_call(self, frame, argument_list):
        "This method is called when there is the remote possibility\n        that we ever need to stop in this function."
        if self._wait_for_mainpyfile:
            return
        if self.stop_here(frame):
            self.message("--Call--")
            self.interaction(frame, None)

    def user_line(self, frame):
        "This function is called when we stop or break at this line."
        if self._wait_for_mainpyfile:
            if (self.mainpyfile != self.canonic(frame.f_code.co_filename)) or (
                frame.f_lineno <= 0
            ):
                return
            self._wait_for_mainpyfile = False
        if self.bp_commands(frame):
            self.interaction(frame, None)

    def bp_commands(self, frame):
        "Call every command that was set for the current active breakpoint\n        (if there is one).\n\n        Returns True if the normal interaction function must be called,\n        False otherwise."
        if getattr(self, "currentbp", False) and (self.currentbp in self.commands):
            currentbp = self.currentbp
            self.currentbp = 0
            lastcmd_back = self.lastcmd
            self.setup(frame, None)
            for line in self.commands[currentbp]:
                self.onecmd(line)
            self.lastcmd = lastcmd_back
            if not self.commands_silent[currentbp]:
                self.print_stack_entry(self.stack[self.curindex])
            if self.commands_doprompt[currentbp]:
                self._cmdloop()
            self.forget()
            return
        return 1

    def user_return(self, frame, return_value):
        "This function is called when a return trap is set here."
        if self._wait_for_mainpyfile:
            return
        frame.f_locals["__return__"] = return_value
        self.message("--Return--")
        self.interaction(frame, None)

    def user_exception(self, frame, exc_info):
        "This function is called if an exception occurs,\n        but only if we are to stop at or just below this level."
        if self._wait_for_mainpyfile:
            return
        (exc_type, exc_value, exc_traceback) = exc_info
        frame.f_locals["__exception__"] = (exc_type, exc_value)
        prefix = (
            "Internal " if ((not exc_traceback) and (exc_type is StopIteration)) else ""
        )
        self.message(
            (
                "%s%s"
                % (
                    prefix,
                    traceback.format_exception_only(exc_type, exc_value)[(-1)].strip(),
                )
            )
        )
        self.interaction(frame, exc_traceback)

    def _cmdloop(self):
        while True:
            try:
                self.allow_kbdint = True
                self.cmdloop()
                self.allow_kbdint = False
                break
            except KeyboardInterrupt:
                self.message("--KeyboardInterrupt--")

    def preloop(self):
        displaying = self.displaying.get(self.curframe)
        if displaying:
            for (expr, oldvalue) in displaying.items():
                newvalue = self._getval_except(expr)
                if (newvalue is not oldvalue) and (newvalue != oldvalue):
                    displaying[expr] = newvalue
                    self.message(
                        ("display %s: %r  [old: %r]" % (expr, newvalue, oldvalue))
                    )

    def interaction(self, frame, traceback):
        if Pdb._previous_sigint_handler:
            try:
                signal.signal(signal.SIGINT, Pdb._previous_sigint_handler)
            except ValueError:
                pass
            else:
                Pdb._previous_sigint_handler = None
        if self.setup(frame, traceback):
            self.forget()
            return
        self.print_stack_entry(self.stack[self.curindex])
        self._cmdloop()
        self.forget()

    def displayhook(self, obj):
        "Custom displayhook for the exec in default(), which prevents\n        assignment of the _ variable in the builtins.\n        "
        if obj is not None:
            self.message(repr(obj))

    def default(self, line):
        if line[:1] == "!":
            line = line[1:]
        locals = self.curframe_locals
        globals = self.curframe.f_globals
        try:
            code = compile((line + "\n"), "<stdin>", "single")
            save_stdout = sys.stdout
            save_stdin = sys.stdin
            save_displayhook = sys.displayhook
            try:
                sys.stdin = self.stdin
                sys.stdout = self.stdout
                sys.displayhook = self.displayhook
                exec(code, globals, locals)
            finally:
                sys.stdout = save_stdout
                sys.stdin = save_stdin
                sys.displayhook = save_displayhook
        except:
            exc_info = sys.exc_info()[:2]
            self.error(traceback.format_exception_only(*exc_info)[(-1)].strip())

    def precmd(self, line):
        "Handle alias expansion and ';;' separator."
        if not line.strip():
            return line
        args = line.split()
        while args[0] in self.aliases:
            line = self.aliases[args[0]]
            ii = 1
            for tmpArg in args[1:]:
                line = line.replace(("%" + str(ii)), tmpArg)
                ii += 1
            line = line.replace("%*", " ".join(args[1:]))
            args = line.split()
        if args[0] != "alias":
            marker = line.find(";;")
            if marker >= 0:
                next = line[(marker + 2) :].lstrip()
                self.cmdqueue.append(next)
                line = line[:marker].rstrip()
        return line

    def onecmd(self, line):
        "Interpret the argument as though it had been typed in response\n        to the prompt.\n\n        Checks whether this line is typed at the normal prompt or in\n        a breakpoint command list definition.\n        "
        if not self.commands_defining:
            return cmd.Cmd.onecmd(self, line)
        else:
            return self.handle_command_def(line)

    def handle_command_def(self, line):
        "Handles one command line during command list definition."
        (cmd, arg, line) = self.parseline(line)
        if not cmd:
            return
        if cmd == "silent":
            self.commands_silent[self.commands_bnum] = True
            return
        elif cmd == "end":
            self.cmdqueue = []
            return 1
        cmdlist = self.commands[self.commands_bnum]
        if arg:
            cmdlist.append(((cmd + " ") + arg))
        else:
            cmdlist.append(cmd)
        try:
            func = getattr(self, ("do_" + cmd))
        except AttributeError:
            func = self.default
        if func.__name__ in self.commands_resuming:
            self.commands_doprompt[self.commands_bnum] = False
            self.cmdqueue = []
            return 1
        return

    def message(self, msg):
        print(msg, file=self.stdout)

    def error(self, msg):
        print("***", msg, file=self.stdout)

    def _complete_location(self, text, line, begidx, endidx):
        if line.strip().endswith((":", ",")):
            return []
        try:
            ret = self._complete_expression(text, line, begidx, endidx)
        except Exception:
            ret = []
        globs = glob.glob((glob.escape(text) + "*"))
        for fn in globs:
            if os.path.isdir(fn):
                ret.append((fn + "/"))
            elif os.path.isfile(fn) and fn.lower().endswith((".py", ".pyw")):
                ret.append((fn + ":"))
        return ret

    def _complete_bpnumber(self, text, line, begidx, endidx):
        return [
            str(i)
            for (i, bp) in enumerate(bdb.Breakpoint.bpbynumber)
            if ((bp is not None) and str(i).startswith(text))
        ]

    def _complete_expression(self, text, line, begidx, endidx):
        if not self.curframe:
            return []
        ns = {**self.curframe.f_globals, **self.curframe_locals}
        if "." in text:
            dotted = text.split(".")
            try:
                obj = ns[dotted[0]]
                for part in dotted[1:(-1)]:
                    obj = getattr(obj, part)
            except (KeyError, AttributeError):
                return []
            prefix = ".".join(dotted[:(-1)]) + "."
            return [(prefix + n) for n in dir(obj) if n.startswith(dotted[(-1)])]
        else:
            return [n for n in ns.keys() if n.startswith(text)]

    def do_commands(self, arg):
        "commands [bpnumber]\n        (com) ...\n        (com) end\n        (Pdb)\n\n        Specify a list of commands for breakpoint number bpnumber.\n        The commands themselves are entered on the following lines.\n        Type a line containing just 'end' to terminate the commands.\n        The commands are executed when the breakpoint is hit.\n\n        To remove all commands from a breakpoint, type commands and\n        follow it immediately with end; that is, give no commands.\n\n        With no bpnumber argument, commands refers to the last\n        breakpoint set.\n\n        You can use breakpoint commands to start your program up\n        again.  Simply use the continue command, or step, or any other\n        command that resumes execution.\n\n        Specifying any command resuming execution (currently continue,\n        step, next, return, jump, quit and their abbreviations)\n        terminates the command list (as if that command was\n        immediately followed by end).  This is because any time you\n        resume execution (even with a simple next or step), you may\n        encounter another breakpoint -- which could have its own\n        command list, leading to ambiguities about which list to\n        execute.\n\n        If you use the 'silent' command in the command list, the usual\n        message about stopping at a breakpoint is not printed.  This\n        may be desirable for breakpoints that are to print a specific\n        message and then continue.  If none of the other commands\n        print anything, you will see no sign that the breakpoint was\n        reached.\n        "
        if not arg:
            bnum = len(bdb.Breakpoint.bpbynumber) - 1
        else:
            try:
                bnum = int(arg)
            except:
                self.error("Usage: commands [bnum]\n        ...\n        end")
                return
        self.commands_bnum = bnum
        if bnum in self.commands:
            old_command_defs = (
                self.commands[bnum],
                self.commands_doprompt[bnum],
                self.commands_silent[bnum],
            )
        else:
            old_command_defs = None
        self.commands[bnum] = []
        self.commands_doprompt[bnum] = True
        self.commands_silent[bnum] = False
        prompt_back = self.prompt
        self.prompt = "(com) "
        self.commands_defining = True
        try:
            self.cmdloop()
        except KeyboardInterrupt:
            if old_command_defs:
                self.commands[bnum] = old_command_defs[0]
                self.commands_doprompt[bnum] = old_command_defs[1]
                self.commands_silent[bnum] = old_command_defs[2]
            else:
                del self.commands[bnum]
                del self.commands_doprompt[bnum]
                del self.commands_silent[bnum]
            self.error("command definition aborted, old commands restored")
        finally:
            self.commands_defining = False
            self.prompt = prompt_back

    complete_commands = _complete_bpnumber

    def do_break(self, arg, temporary=0):
        "b(reak) [ ([filename:]lineno | function) [, condition] ]\n        Without argument, list all breaks.\n\n        With a line number argument, set a break at this line in the\n        current file.  With a function name, set a break at the first\n        executable line of that function.  If a second argument is\n        present, it is a string specifying an expression which must\n        evaluate to true before the breakpoint is honored.\n\n        The line number may be prefixed with a filename and a colon,\n        to specify a breakpoint in another file (probably one that\n        hasn't been loaded yet).  The file is searched for on\n        sys.path; the .py suffix may be omitted.\n        "
        if not arg:
            if self.breaks:
                self.message("Num Type         Disp Enb   Where")
                for bp in bdb.Breakpoint.bpbynumber:
                    if bp:
                        self.message(bp.bpformat())
            return
        filename = None
        lineno = None
        cond = None
        comma = arg.find(",")
        if comma > 0:
            cond = arg[(comma + 1) :].lstrip()
            arg = arg[:comma].rstrip()
        colon = arg.rfind(":")
        funcname = None
        if colon >= 0:
            filename = arg[:colon].rstrip()
            f = self.lookupmodule(filename)
            if not f:
                self.error(("%r not found from sys.path" % filename))
                return
            else:
                filename = f
            arg = arg[(colon + 1) :].lstrip()
            try:
                lineno = int(arg)
            except ValueError:
                self.error(("Bad lineno: %s" % arg))
                return
        else:
            try:
                lineno = int(arg)
            except ValueError:
                try:
                    func = eval(arg, self.curframe.f_globals, self.curframe_locals)
                except:
                    func = arg
                try:
                    if hasattr(func, "__func__"):
                        func = func.__func__
                    code = func.__code__
                    funcname = code.co_name
                    lineno = code.co_firstlineno
                    filename = code.co_filename
                except:
                    (ok, filename, ln) = self.lineinfo(arg)
                    if not ok:
                        self.error(
                            (
                                "The specified object %r is not a function or was not found along sys.path."
                                % arg
                            )
                        )
                        return
                    funcname = ok
                    lineno = int(ln)
        if not filename:
            filename = self.defaultFile()
        line = self.checkline(filename, lineno)
        if line:
            err = self.set_break(filename, line, temporary, cond, funcname)
            if err:
                self.error(err)
            else:
                bp = self.get_breaks(filename, line)[(-1)]
                self.message(("Breakpoint %d at %s:%d" % (bp.number, bp.file, bp.line)))

    def defaultFile(self):
        "Produce a reasonable default."
        filename = self.curframe.f_code.co_filename
        if (filename == "<string>") and self.mainpyfile:
            filename = self.mainpyfile
        return filename

    do_b = do_break
    complete_break = _complete_location
    complete_b = _complete_location

    def do_tbreak(self, arg):
        "tbreak [ ([filename:]lineno | function) [, condition] ]\n        Same arguments as break, but sets a temporary breakpoint: it\n        is automatically deleted when first hit.\n        "
        self.do_break(arg, 1)

    complete_tbreak = _complete_location

    def lineinfo(self, identifier):
        failed = (None, None, None)
        idstring = identifier.split("'")
        if len(idstring) == 1:
            id = idstring[0].strip()
        elif len(idstring) == 3:
            id = idstring[1].strip()
        else:
            return failed
        if id == "":
            return failed
        parts = id.split(".")
        if parts[0] == "self":
            del parts[0]
            if len(parts) == 0:
                return failed
        fname = self.defaultFile()
        if len(parts) == 1:
            item = parts[0]
        else:
            f = self.lookupmodule(parts[0])
            if f:
                fname = f
            item = parts[1]
        answer = find_function(item, fname)
        return answer or failed

    def checkline(self, filename, lineno):
        "Check whether specified line seems to be executable.\n\n        Return `lineno` if it is, 0 if not (e.g. a docstring, comment, blank\n        line or EOF). Warning: testing is not comprehensive.\n        "
        globs = self.curframe.f_globals if hasattr(self, "curframe") else None
        line = linecache.getline(filename, lineno, globs)
        if not line:
            self.message("End of file")
            return 0
        line = line.strip()
        if (not line) or (line[0] == "#") or (line[:3] == '"""') or (line[:3] == "'''"):
            self.error("Blank or comment")
            return 0
        return lineno

    def do_enable(self, arg):
        "enable bpnumber [bpnumber ...]\n        Enables the breakpoints given as a space separated list of\n        breakpoint numbers.\n        "
        args = arg.split()
        for i in args:
            try:
                bp = self.get_bpbynumber(i)
            except ValueError as err:
                self.error(err)
            else:
                bp.enable()
                self.message(("Enabled %s" % bp))

    complete_enable = _complete_bpnumber

    def do_disable(self, arg):
        "disable bpnumber [bpnumber ...]\n        Disables the breakpoints given as a space separated list of\n        breakpoint numbers.  Disabling a breakpoint means it cannot\n        cause the program to stop execution, but unlike clearing a\n        breakpoint, it remains in the list of breakpoints and can be\n        (re-)enabled.\n        "
        args = arg.split()
        for i in args:
            try:
                bp = self.get_bpbynumber(i)
            except ValueError as err:
                self.error(err)
            else:
                bp.disable()
                self.message(("Disabled %s" % bp))

    complete_disable = _complete_bpnumber

    def do_condition(self, arg):
        "condition bpnumber [condition]\n        Set a new condition for the breakpoint, an expression which\n        must evaluate to true before the breakpoint is honored.  If\n        condition is absent, any existing condition is removed; i.e.,\n        the breakpoint is made unconditional.\n        "
        args = arg.split(" ", 1)
        try:
            cond = args[1]
        except IndexError:
            cond = None
        try:
            bp = self.get_bpbynumber(args[0].strip())
        except IndexError:
            self.error("Breakpoint number expected")
        except ValueError as err:
            self.error(err)
        else:
            bp.cond = cond
            if not cond:
                self.message(("Breakpoint %d is now unconditional." % bp.number))
            else:
                self.message(("New condition set for breakpoint %d." % bp.number))

    complete_condition = _complete_bpnumber

    def do_ignore(self, arg):
        "ignore bpnumber [count]\n        Set the ignore count for the given breakpoint number.  If\n        count is omitted, the ignore count is set to 0.  A breakpoint\n        becomes active when the ignore count is zero.  When non-zero,\n        the count is decremented each time the breakpoint is reached\n        and the breakpoint is not disabled and any associated\n        condition evaluates to true.\n        "
        args = arg.split()
        try:
            count = int(args[1].strip())
        except:
            count = 0
        try:
            bp = self.get_bpbynumber(args[0].strip())
        except IndexError:
            self.error("Breakpoint number expected")
        except ValueError as err:
            self.error(err)
        else:
            bp.ignore = count
            if count > 0:
                if count > 1:
                    countstr = "%d crossings" % count
                else:
                    countstr = "1 crossing"
                self.message(
                    ("Will ignore next %s of breakpoint %d." % (countstr, bp.number))
                )
            else:
                self.message(
                    ("Will stop next time breakpoint %d is reached." % bp.number)
                )

    complete_ignore = _complete_bpnumber

    def do_clear(self, arg):
        "cl(ear) filename:lineno\ncl(ear) [bpnumber [bpnumber...]]\n        With a space separated list of breakpoint numbers, clear\n        those breakpoints.  Without argument, clear all breaks (but\n        first ask confirmation).  With a filename:lineno argument,\n        clear all breaks at that line in that file.\n        "
        if not arg:
            try:
                reply = input("Clear all breaks? ")
            except EOFError:
                reply = "no"
            reply = reply.strip().lower()
            if reply in ("y", "yes"):
                bplist = [bp for bp in bdb.Breakpoint.bpbynumber if bp]
                self.clear_all_breaks()
                for bp in bplist:
                    self.message(("Deleted %s" % bp))
            return
        if ":" in arg:
            i = arg.rfind(":")
            filename = arg[:i]
            arg = arg[(i + 1) :]
            try:
                lineno = int(arg)
            except ValueError:
                err = "Invalid line number (%s)" % arg
            else:
                bplist = self.get_breaks(filename, lineno)
                err = self.clear_break(filename, lineno)
            if err:
                self.error(err)
            else:
                for bp in bplist:
                    self.message(("Deleted %s" % bp))
            return
        numberlist = arg.split()
        for i in numberlist:
            try:
                bp = self.get_bpbynumber(i)
            except ValueError as err:
                self.error(err)
            else:
                self.clear_bpbynumber(i)
                self.message(("Deleted %s" % bp))

    do_cl = do_clear
    complete_clear = _complete_location
    complete_cl = _complete_location

    def do_where(self, arg):
        "w(here)\n        Print a stack trace, with the most recent frame at the bottom.\n        An arrow indicates the \"current frame\", which determines the\n        context of most commands.  'bt' is an alias for this command.\n        "
        self.print_stack_trace()

    do_w = do_where
    do_bt = do_where

    def _select_frame(self, number):
        assert 0 <= number < len(self.stack)
        self.curindex = number
        self.curframe = self.stack[self.curindex][0]
        self.curframe_locals = self.curframe.f_locals
        self.print_stack_entry(self.stack[self.curindex])
        self.lineno = None

    def do_up(self, arg):
        "u(p) [count]\n        Move the current frame count (default one) levels up in the\n        stack trace (to an older frame).\n        "
        if self.curindex == 0:
            self.error("Oldest frame")
            return
        try:
            count = int((arg or 1))
        except ValueError:
            self.error(("Invalid frame count (%s)" % arg))
            return
        if count < 0:
            newframe = 0
        else:
            newframe = max(0, (self.curindex - count))
        self._select_frame(newframe)

    do_u = do_up

    def do_down(self, arg):
        "d(own) [count]\n        Move the current frame count (default one) levels down in the\n        stack trace (to a newer frame).\n        "
        if (self.curindex + 1) == len(self.stack):
            self.error("Newest frame")
            return
        try:
            count = int((arg or 1))
        except ValueError:
            self.error(("Invalid frame count (%s)" % arg))
            return
        if count < 0:
            newframe = len(self.stack) - 1
        else:
            newframe = min((len(self.stack) - 1), (self.curindex + count))
        self._select_frame(newframe)

    do_d = do_down

    def do_until(self, arg):
        "unt(il) [lineno]\n        Without argument, continue execution until the line with a\n        number greater than the current one is reached.  With a line\n        number, continue execution until a line with a number greater\n        or equal to that is reached.  In both cases, also stop when\n        the current frame returns.\n        "
        if arg:
            try:
                lineno = int(arg)
            except ValueError:
                self.error(("Error in argument: %r" % arg))
                return
            if lineno <= self.curframe.f_lineno:
                self.error('"until" line number is smaller than current line number')
                return
        else:
            lineno = None
        self.set_until(self.curframe, lineno)
        return 1

    do_unt = do_until

    def do_step(self, arg):
        "s(tep)\n        Execute the current line, stop at the first possible occasion\n        (either in a function that is called or in the current\n        function).\n        "
        self.set_step()
        return 1

    do_s = do_step

    def do_next(self, arg):
        "n(ext)\n        Continue execution until the next line in the current function\n        is reached or it returns.\n        "
        self.set_next(self.curframe)
        return 1

    do_n = do_next

    def do_run(self, arg):
        'run [args...]\n        Restart the debugged python program. If a string is supplied\n        it is split with "shlex", and the result is used as the new\n        sys.argv.  History, breakpoints, actions and debugger options\n        are preserved.  "restart" is an alias for "run".\n        '
        if arg:
            import shlex

            argv0 = sys.argv[0:1]
            sys.argv = shlex.split(arg)
            sys.argv[:0] = argv0
        raise Restart

    do_restart = do_run

    def do_return(self, arg):
        "r(eturn)\n        Continue execution until the current function returns.\n        "
        self.set_return(self.curframe)
        return 1

    do_r = do_return

    def do_continue(self, arg):
        "c(ont(inue))\n        Continue execution, only stop when a breakpoint is encountered.\n        "
        if not self.nosigint:
            try:
                Pdb._previous_sigint_handler = signal.signal(
                    signal.SIGINT, self.sigint_handler
                )
            except ValueError:
                pass
        self.set_continue()
        return 1

    do_c = do_cont = do_continue

    def do_jump(self, arg):
        "j(ump) lineno\n        Set the next line that will be executed.  Only available in\n        the bottom-most frame.  This lets you jump back and execute\n        code again, or jump forward to skip code that you don't want\n        to run.\n\n        It should be noted that not all jumps are allowed -- for\n        instance it is not possible to jump into the middle of a\n        for loop or out of a finally clause.\n        "
        if (self.curindex + 1) != len(self.stack):
            self.error("You can only jump within the bottom frame")
            return
        try:
            arg = int(arg)
        except ValueError:
            self.error("The 'jump' command requires a line number")
        else:
            try:
                self.curframe.f_lineno = arg
                self.stack[self.curindex] = (self.stack[self.curindex][0], arg)
                self.print_stack_entry(self.stack[self.curindex])
            except ValueError as e:
                self.error(("Jump failed: %s" % e))

    do_j = do_jump

    def do_debug(self, arg):
        "debug code\n        Enter a recursive debugger that steps through the code\n        argument (which is an arbitrary expression or statement to be\n        executed in the current environment).\n        "
        sys.settrace(None)
        globals = self.curframe.f_globals
        locals = self.curframe_locals
        p = Pdb(self.completekey, self.stdin, self.stdout)
        p.prompt = "(%s) " % self.prompt.strip()
        self.message("ENTERING RECURSIVE DEBUGGER")
        try:
            sys.call_tracing(p.run, (arg, globals, locals))
        except Exception:
            exc_info = sys.exc_info()[:2]
            self.error(traceback.format_exception_only(*exc_info)[(-1)].strip())
        self.message("LEAVING RECURSIVE DEBUGGER")
        sys.settrace(self.trace_dispatch)
        self.lastcmd = p.lastcmd

    complete_debug = _complete_expression

    def do_quit(self, arg):
        "q(uit)\nexit\n        Quit from the debugger. The program being executed is aborted.\n        "
        self._user_requested_quit = True
        self.set_quit()
        return 1

    do_q = do_quit
    do_exit = do_quit

    def do_EOF(self, arg):
        "EOF\n        Handles the receipt of EOF as a command.\n        "
        self.message("")
        self._user_requested_quit = True
        self.set_quit()
        return 1

    def do_args(self, arg):
        "a(rgs)\n        Print the argument list of the current function.\n        "
        co = self.curframe.f_code
        dict = self.curframe_locals
        n = co.co_argcount + co.co_kwonlyargcount
        if co.co_flags & inspect.CO_VARARGS:
            n = n + 1
        if co.co_flags & inspect.CO_VARKEYWORDS:
            n = n + 1
        for i in range(n):
            name = co.co_varnames[i]
            if name in dict:
                self.message(("%s = %r" % (name, dict[name])))
            else:
                self.message(("%s = *** undefined ***" % (name,)))

    do_a = do_args

    def do_retval(self, arg):
        "retval\n        Print the return value for the last return of a function.\n        "
        if "__return__" in self.curframe_locals:
            self.message(repr(self.curframe_locals["__return__"]))
        else:
            self.error("Not yet returned!")

    do_rv = do_retval

    def _getval(self, arg):
        try:
            return eval(arg, self.curframe.f_globals, self.curframe_locals)
        except:
            exc_info = sys.exc_info()[:2]
            self.error(traceback.format_exception_only(*exc_info)[(-1)].strip())
            raise

    def _getval_except(self, arg, frame=None):
        try:
            if frame is None:
                return eval(arg, self.curframe.f_globals, self.curframe_locals)
            else:
                return eval(arg, frame.f_globals, frame.f_locals)
        except:
            exc_info = sys.exc_info()[:2]
            err = traceback.format_exception_only(*exc_info)[(-1)].strip()
            return _rstr(("** raised %s **" % err))

    def do_p(self, arg):
        "p expression\n        Print the value of the expression.\n        "
        try:
            self.message(repr(self._getval(arg)))
        except:
            pass

    def do_pp(self, arg):
        "pp expression\n        Pretty-print the value of the expression.\n        "
        try:
            self.message(pprint.pformat(self._getval(arg)))
        except:
            pass

    complete_print = _complete_expression
    complete_p = _complete_expression
    complete_pp = _complete_expression

    def do_list(self, arg):
        'l(ist) [first [,last] | .]\n\n        List source code for the current file.  Without arguments,\n        list 11 lines around the current line or continue the previous\n        listing.  With . as argument, list 11 lines around the current\n        line.  With one argument, list 11 lines starting at that line.\n        With two arguments, list the given range; if the second\n        argument is less than the first, it is a count.\n\n        The current line in the current frame is indicated by "->".\n        If an exception is being debugged, the line where the\n        exception was originally raised or propagated is indicated by\n        ">>", if it differs from the current line.\n        '
        self.lastcmd = "list"
        last = None
        if arg and (arg != "."):
            try:
                if "," in arg:
                    (first, last) = arg.split(",")
                    first = int(first.strip())
                    last = int(last.strip())
                    if last < first:
                        last = first + last
                else:
                    first = int(arg.strip())
                    first = max(1, (first - 5))
            except ValueError:
                self.error(("Error in argument: %r" % arg))
                return
        elif (self.lineno is None) or (arg == "."):
            first = max(1, (self.curframe.f_lineno - 5))
        else:
            first = self.lineno + 1
        if last is None:
            last = first + 10
        filename = self.curframe.f_code.co_filename
        breaklist = self.get_file_breaks(filename)
        try:
            lines = linecache.getlines(filename, self.curframe.f_globals)
            self._print_lines(
                lines[(first - 1) : last], first, breaklist, self.curframe
            )
            self.lineno = min(last, len(lines))
            if len(lines) < last:
                self.message("[EOF]")
        except KeyboardInterrupt:
            pass

    do_l = do_list

    def do_longlist(self, arg):
        "longlist | ll\n        List the whole source code for the current function or frame.\n        "
        filename = self.curframe.f_code.co_filename
        breaklist = self.get_file_breaks(filename)
        try:
            (lines, lineno) = getsourcelines(self.curframe)
        except OSError as err:
            self.error(err)
            return
        self._print_lines(lines, lineno, breaklist, self.curframe)

    do_ll = do_longlist

    def do_source(self, arg):
        "source expression\n        Try to get source code for the given object and display it.\n        "
        try:
            obj = self._getval(arg)
        except:
            return
        try:
            (lines, lineno) = getsourcelines(obj)
        except (OSError, TypeError) as err:
            self.error(err)
            return
        self._print_lines(lines, lineno)

    complete_source = _complete_expression

    def _print_lines(self, lines, start, breaks=(), frame=None):
        "Print a range of lines."
        if frame:
            current_lineno = frame.f_lineno
            exc_lineno = self.tb_lineno.get(frame, (-1))
        else:
            current_lineno = exc_lineno = -1
        for (lineno, line) in enumerate(lines, start):
            s = str(lineno).rjust(3)
            if len(s) < 4:
                s += " "
            if lineno in breaks:
                s += "B"
            else:
                s += " "
            if lineno == current_lineno:
                s += "->"
            elif lineno == exc_lineno:
                s += ">>"
            self.message(((s + "\t") + line.rstrip()))

    def do_whatis(self, arg):
        "whatis arg\n        Print the type of the argument.\n        "
        try:
            value = self._getval(arg)
        except:
            return
        code = None
        try:
            code = value.__func__.__code__
        except Exception:
            pass
        if code:
            self.message(("Method %s" % code.co_name))
            return
        try:
            code = value.__code__
        except Exception:
            pass
        if code:
            self.message(("Function %s" % code.co_name))
            return
        if value.__class__ is type:
            self.message(("Class %s.%s" % (value.__module__, value.__qualname__)))
            return
        self.message(type(value))

    complete_whatis = _complete_expression

    def do_display(self, arg):
        "display [expression]\n\n        Display the value of the expression if it changed, each time execution\n        stops in the current frame.\n\n        Without expression, list all display expressions for the current frame.\n        "
        if not arg:
            self.message("Currently displaying:")
            for item in self.displaying.get(self.curframe, {}).items():
                self.message(("%s: %r" % item))
        else:
            val = self._getval_except(arg)
            self.displaying.setdefault(self.curframe, {})[arg] = val
            self.message(("display %s: %r" % (arg, val)))

    complete_display = _complete_expression

    def do_undisplay(self, arg):
        "undisplay [expression]\n\n        Do not display the expression any more in the current frame.\n\n        Without expression, clear all display expressions for the current frame.\n        "
        if arg:
            try:
                del self.displaying.get(self.curframe, {})[arg]
            except KeyError:
                self.error(("not displaying %s" % arg))
        else:
            self.displaying.pop(self.curframe, None)

    def complete_undisplay(self, text, line, begidx, endidx):
        return [e for e in self.displaying.get(self.curframe, {}) if e.startswith(text)]

    def do_interact(self, arg):
        "interact\n\n        Start an interactive interpreter whose global namespace\n        contains all the (global and local) names found in the current scope.\n        "
        ns = {**self.curframe.f_globals, **self.curframe_locals}
        code.interact("*interactive*", local=ns)

    def do_alias(self, arg):
        'alias [name [command [parameter parameter ...] ]]\n        Create an alias called \'name\' that executes \'command\'.  The\n        command must *not* be enclosed in quotes.  Replaceable\n        parameters can be indicated by %1, %2, and so on, while %* is\n        replaced by all the parameters.  If no command is given, the\n        current alias for name is shown. If no name is given, all\n        aliases are listed.\n\n        Aliases may be nested and can contain anything that can be\n        legally typed at the pdb prompt.  Note!  You *can* override\n        internal pdb commands with aliases!  Those internal commands\n        are then hidden until the alias is removed.  Aliasing is\n        recursively applied to the first word of the command line; all\n        other words in the line are left alone.\n\n        As an example, here are two useful aliases (especially when\n        placed in the .pdbrc file):\n\n        # Print instance variables (usage "pi classInst")\n        alias pi for k in %1.__dict__.keys(): print("%1.",k,"=",%1.__dict__[k])\n        # Print instance variables in self\n        alias ps pi self\n        '
        args = arg.split()
        if len(args) == 0:
            keys = sorted(self.aliases.keys())
            for alias in keys:
                self.message(("%s = %s" % (alias, self.aliases[alias])))
            return
        if (args[0] in self.aliases) and (len(args) == 1):
            self.message(("%s = %s" % (args[0], self.aliases[args[0]])))
        else:
            self.aliases[args[0]] = " ".join(args[1:])

    def do_unalias(self, arg):
        "unalias name\n        Delete the specified alias.\n        "
        args = arg.split()
        if len(args) == 0:
            return
        if args[0] in self.aliases:
            del self.aliases[args[0]]

    def complete_unalias(self, text, line, begidx, endidx):
        return [a for a in self.aliases if a.startswith(text)]

    commands_resuming = [
        "do_continue",
        "do_step",
        "do_next",
        "do_return",
        "do_quit",
        "do_jump",
    ]

    def print_stack_trace(self):
        try:
            for frame_lineno in self.stack:
                self.print_stack_entry(frame_lineno)
        except KeyboardInterrupt:
            pass

    def print_stack_entry(self, frame_lineno, prompt_prefix=line_prefix):
        (frame, lineno) = frame_lineno
        if frame is self.curframe:
            prefix = "> "
        else:
            prefix = "  "
        self.message((prefix + self.format_stack_entry(frame_lineno, prompt_prefix)))

    def do_help(self, arg):
        'h(elp)\n        Without argument, print the list of available commands.\n        With a command name as argument, print help about that command.\n        "help pdb" shows the full pdb documentation.\n        "help exec" gives help on the ! command.\n        '
        if not arg:
            return cmd.Cmd.do_help(self, arg)
        try:
            try:
                topic = getattr(self, ("help_" + arg))
                return topic()
            except AttributeError:
                command = getattr(self, ("do_" + arg))
        except AttributeError:
            self.error(("No help for %r" % arg))
        else:
            if sys.flags.optimize >= 2:
                self.error(
                    (
                        "No help for %r; please do not run Python with -OO if you need command help"
                        % arg
                    )
                )
                return
            self.message(command.__doc__.rstrip())

    do_h = do_help

    def help_exec(self):
        "(!) statement\n        Execute the (one-line) statement in the context of the current\n        stack frame.  The exclamation point can be omitted unless the\n        first word of the statement resembles a debugger command.  To\n        assign to a global variable you must always prefix the command\n        with a 'global' command, e.g.:\n        (Pdb) global list_options; list_options = ['-l']\n        (Pdb)\n        "
        self.message((self.help_exec.__doc__ or "").strip())

    def help_pdb(self):
        help()

    def lookupmodule(self, filename):
        "Helper function for break/clear parsing -- may be overridden.\n\n        lookupmodule() translates (possibly incomplete) file or module name\n        into an absolute file name.\n        "
        if os.path.isabs(filename) and os.path.exists(filename):
            return filename
        f = os.path.join(sys.path[0], filename)
        if os.path.exists(f) and (self.canonic(f) == self.mainpyfile):
            return f
        (root, ext) = os.path.splitext(filename)
        if ext == "":
            filename = filename + ".py"
        if os.path.isabs(filename):
            return filename
        for dirname in sys.path:
            while os.path.islink(dirname):
                dirname = os.readlink(dirname)
            fullname = os.path.join(dirname, filename)
            if os.path.exists(fullname):
                return fullname
        return None

    def _runmodule(self, module_name):
        self._wait_for_mainpyfile = True
        self._user_requested_quit = False
        import runpy

        (mod_name, mod_spec, code) = runpy._get_module_details(module_name)
        self.mainpyfile = self.canonic(code.co_filename)
        import __main__

        __main__.__dict__.clear()
        __main__.__dict__.update(
            {
                "__name__": "__main__",
                "__file__": self.mainpyfile,
                "__package__": mod_spec.parent,
                "__loader__": mod_spec.loader,
                "__spec__": mod_spec,
                "__builtins__": __builtins__,
            }
        )
        self.run(code)

    def _runscript(self, filename):
        import __main__

        __main__.__dict__.clear()
        __main__.__dict__.update(
            {"__name__": "__main__", "__file__": filename, "__builtins__": __builtins__}
        )
        self._wait_for_mainpyfile = True
        self.mainpyfile = self.canonic(filename)
        self._user_requested_quit = False
        with io.open_code(filename) as fp:
            statement = "exec(compile(%r, %r, 'exec'))" % (fp.read(), self.mainpyfile)
        self.run(statement)


if __doc__ is not None:
    _help_order = [
        "help",
        "where",
        "down",
        "up",
        "break",
        "tbreak",
        "clear",
        "disable",
        "enable",
        "ignore",
        "condition",
        "commands",
        "step",
        "next",
        "until",
        "jump",
        "return",
        "retval",
        "run",
        "continue",
        "list",
        "longlist",
        "args",
        "p",
        "pp",
        "whatis",
        "source",
        "display",
        "undisplay",
        "interact",
        "alias",
        "unalias",
        "debug",
        "quit",
    ]
    for _command in _help_order:
        __doc__ += getattr(Pdb, ("do_" + _command)).__doc__.strip() + "\n\n"
    __doc__ += Pdb.help_exec.__doc__
    del _help_order, _command


def run(statement, globals=None, locals=None):
    Pdb().run(statement, globals, locals)


def runeval(expression, globals=None, locals=None):
    return Pdb().runeval(expression, globals, locals)


def runctx(statement, globals, locals):
    run(statement, globals, locals)


def runcall(*args, **kwds):
    return Pdb().runcall(*args, **kwds)


def set_trace(*, header=None):
    pdb = Pdb()
    if header is not None:
        pdb.message(header)
    pdb.set_trace(sys._getframe().f_back)


def post_mortem(t=None):
    if t is None:
        t = sys.exc_info()[2]
    if t is None:
        raise ValueError(
            "A valid traceback must be passed if no exception is being handled"
        )
    p = Pdb()
    p.reset()
    p.interaction(None, t)


def pm():
    post_mortem(sys.last_traceback)


TESTCMD = "import x; x.main()"


def test():
    run(TESTCMD)


def help():
    import pydoc

    pydoc.pager(__doc__)


_usage = 'usage: pdb.py [-c command] ... [-m module | pyfile] [arg] ...\n\nDebug the Python program given by pyfile. Alternatively,\nan executable module or package to debug can be specified using\nthe -m switch.\n\nInitial commands are read from .pdbrc files in your home directory\nand in the current directory, if they exist.  Commands supplied with\n-c are executed after commands from .pdbrc files.\n\nTo let the script run until an exception occurs, use "-c continue".\nTo let the script run up to a given line X in the debugged file, use\n"-c \'until X\'".'


def main():
    import getopt

    (opts, args) = getopt.getopt(sys.argv[1:], "mhc:", ["help", "command="])
    if not args:
        print(_usage)
        sys.exit(2)
    commands = []
    run_as_module = False
    for (opt, optarg) in opts:
        if opt in ["-h", "--help"]:
            print(_usage)
            sys.exit()
        elif opt in ["-c", "--command"]:
            commands.append(optarg)
        elif opt in ["-m"]:
            run_as_module = True
    mainpyfile = args[0]
    if (not run_as_module) and (not os.path.exists(mainpyfile)):
        print("Error:", mainpyfile, "does not exist")
        sys.exit(1)
    sys.argv[:] = args
    if not run_as_module:
        mainpyfile = os.path.realpath(mainpyfile)
        sys.path[0] = os.path.dirname(mainpyfile)
    pdb = Pdb()
    pdb.rcLines.extend(commands)
    while True:
        try:
            if run_as_module:
                pdb._runmodule(mainpyfile)
            else:
                pdb._runscript(mainpyfile)
            if pdb._user_requested_quit:
                break
            print("The program finished and will be restarted")
        except Restart:
            print("Restarting", mainpyfile, "with arguments:")
            print(("\t" + " ".join(sys.argv[1:])))
        except SystemExit:
            print("The program exited via sys.exit(). Exit status:", end=" ")
            print(sys.exc_info()[1])
        except SyntaxError:
            traceback.print_exc()
            sys.exit(1)
        except:
            traceback.print_exc()
            print("Uncaught exception. Entering post mortem debugging")
            print("Running 'cont' or 'step' will restart the program")
            t = sys.exc_info()[2]
            pdb.interaction(None, t)
            print(
                (
                    ("Post mortem debugger finished. The " + mainpyfile)
                    + " will be restarted"
                )
            )


if __name__ == "__main__":
    import pdb

    pdb.main()
