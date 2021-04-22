"Debugger basics"
import fnmatch
import sys
import os
from inspect import CO_GENERATOR, CO_COROUTINE, CO_ASYNC_GENERATOR

__all__ = ["BdbQuit", "Bdb", "Breakpoint"]
GENERATOR_AND_COROUTINE_FLAGS = (CO_GENERATOR | CO_COROUTINE) | CO_ASYNC_GENERATOR


class BdbQuit(Exception):
    "Exception to give up completely."


class Bdb:
    "Generic Python debugger base class.\n\n    This class takes care of details of the trace facility;\n    a derived class should implement user interaction.\n    The standard debugger class (pdb.Pdb) is an example.\n\n    The optional skip argument must be an iterable of glob-style\n    module name patterns.  The debugger will not step into frames\n    that originate in a module that matches one of these patterns.\n    Whether a frame is considered to originate in a certain module\n    is determined by the __name__ in the frame globals.\n    "

    def __init__(self, skip=None):
        self.skip = set(skip) if skip else None
        self.breaks = {}
        self.fncache = {}
        self.frame_returning = None
        self._load_breaks()

    def canonic(self, filename):
        "Return canonical form of filename.\n\n        For real filenames, the canonical form is a case-normalized (on\n        case insensitive filesystems) absolute path.  'Filenames' with\n        angle brackets, such as \"<stdin>\", generated in interactive\n        mode, are returned unchanged.\n        "
        if filename == (("<" + filename[1:(-1)]) + ">"):
            return filename
        canonic = self.fncache.get(filename)
        if not canonic:
            canonic = os.path.abspath(filename)
            canonic = os.path.normcase(canonic)
            self.fncache[filename] = canonic
        return canonic

    def reset(self):
        "Set values of attributes as ready to start debugging."
        import linecache

        linecache.checkcache()
        self.botframe = None
        self._set_stopinfo(None, None)

    def trace_dispatch(self, frame, event, arg):
        "Dispatch a trace function for debugged frames based on the event.\n\n        This function is installed as the trace function for debugged\n        frames. Its return value is the new trace function, which is\n        usually itself. The default implementation decides how to\n        dispatch a frame, depending on the type of event (passed in as a\n        string) that is about to be executed.\n\n        The event can be one of the following:\n            line: A new line of code is going to be executed.\n            call: A function is about to be called or another code block\n                  is entered.\n            return: A function or other code block is about to return.\n            exception: An exception has occurred.\n            c_call: A C function is about to be called.\n            c_return: A C function has returned.\n            c_exception: A C function has raised an exception.\n\n        For the Python events, specialized functions (see the dispatch_*()\n        methods) are called.  For the C events, no action is taken.\n\n        The arg parameter depends on the previous event.\n        "
        if self.quitting:
            return
        if event == "line":
            return self.dispatch_line(frame)
        if event == "call":
            return self.dispatch_call(frame, arg)
        if event == "return":
            return self.dispatch_return(frame, arg)
        if event == "exception":
            return self.dispatch_exception(frame, arg)
        if event == "c_call":
            return self.trace_dispatch
        if event == "c_exception":
            return self.trace_dispatch
        if event == "c_return":
            return self.trace_dispatch
        print("bdb.Bdb.dispatch: unknown debugging event:", repr(event))
        return self.trace_dispatch

    def dispatch_line(self, frame):
        "Invoke user function and return trace function for line event.\n\n        If the debugger stops on the current line, invoke\n        self.user_line(). Raise BdbQuit if self.quitting is set.\n        Return self.trace_dispatch to continue tracing in this scope.\n        "
        if self.stop_here(frame) or self.break_here(frame):
            self.user_line(frame)
            if self.quitting:
                raise BdbQuit
        return self.trace_dispatch

    def dispatch_call(self, frame, arg):
        "Invoke user function and return trace function for call event.\n\n        If the debugger stops on this function call, invoke\n        self.user_call(). Raise BbdQuit if self.quitting is set.\n        Return self.trace_dispatch to continue tracing in this scope.\n        "
        if self.botframe is None:
            self.botframe = frame.f_back
            return self.trace_dispatch
        if not (self.stop_here(frame) or self.break_anywhere(frame)):
            return
        if self.stopframe and (frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS):
            return self.trace_dispatch
        self.user_call(frame, arg)
        if self.quitting:
            raise BdbQuit
        return self.trace_dispatch

    def dispatch_return(self, frame, arg):
        "Invoke user function and return trace function for return event.\n\n        If the debugger stops on this function return, invoke\n        self.user_return(). Raise BdbQuit if self.quitting is set.\n        Return self.trace_dispatch to continue tracing in this scope.\n        "
        if self.stop_here(frame) or (frame == self.returnframe):
            if self.stopframe and (
                frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS
            ):
                return self.trace_dispatch
            try:
                self.frame_returning = frame
                self.user_return(frame, arg)
            finally:
                self.frame_returning = None
            if self.quitting:
                raise BdbQuit
            if (self.stopframe is frame) and (self.stoplineno != (-1)):
                self._set_stopinfo(None, None)
        return self.trace_dispatch

    def dispatch_exception(self, frame, arg):
        "Invoke user function and return trace function for exception event.\n\n        If the debugger stops on this exception, invoke\n        self.user_exception(). Raise BdbQuit if self.quitting is set.\n        Return self.trace_dispatch to continue tracing in this scope.\n        "
        if self.stop_here(frame):
            if not (
                (frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS)
                and (arg[0] is StopIteration)
                and (arg[2] is None)
            ):
                self.user_exception(frame, arg)
                if self.quitting:
                    raise BdbQuit
        elif (
            self.stopframe
            and (frame is not self.stopframe)
            and (self.stopframe.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS)
            and (arg[0] in (StopIteration, GeneratorExit))
        ):
            self.user_exception(frame, arg)
            if self.quitting:
                raise BdbQuit
        return self.trace_dispatch

    def is_skipped_module(self, module_name):
        "Return True if module_name matches any skip pattern."
        if module_name is None:
            return False
        for pattern in self.skip:
            if fnmatch.fnmatch(module_name, pattern):
                return True
        return False

    def stop_here(self, frame):
        "Return True if frame is below the starting frame in the stack."
        if self.skip and self.is_skipped_module(frame.f_globals.get("__name__")):
            return False
        if frame is self.stopframe:
            if self.stoplineno == (-1):
                return False
            return frame.f_lineno >= self.stoplineno
        if not self.stopframe:
            return True
        return False

    def break_here(self, frame):
        "Return True if there is an effective breakpoint for this line.\n\n        Check for line or function breakpoint and if in effect.\n        Delete temporary breakpoints if effective() says to.\n        "
        filename = self.canonic(frame.f_code.co_filename)
        if filename not in self.breaks:
            return False
        lineno = frame.f_lineno
        if lineno not in self.breaks[filename]:
            lineno = frame.f_code.co_firstlineno
            if lineno not in self.breaks[filename]:
                return False
        (bp, flag) = effective(filename, lineno, frame)
        if bp:
            self.currentbp = bp.number
            if flag and bp.temporary:
                self.do_clear(str(bp.number))
            return True
        else:
            return False

    def do_clear(self, arg):
        "Remove temporary breakpoint.\n\n        Must implement in derived classes or get NotImplementedError.\n        "
        raise NotImplementedError("subclass of bdb must implement do_clear()")

    def break_anywhere(self, frame):
        "Return True if there is any breakpoint for frame's filename.\n        "
        return self.canonic(frame.f_code.co_filename) in self.breaks

    def user_call(self, frame, argument_list):
        "Called if we might stop in a function."
        pass

    def user_line(self, frame):
        "Called when we stop or break at a line."
        pass

    def user_return(self, frame, return_value):
        "Called when a return trap is set here."
        pass

    def user_exception(self, frame, exc_info):
        "Called when we stop on an exception."
        pass

    def _set_stopinfo(self, stopframe, returnframe, stoplineno=0):
        "Set the attributes for stopping.\n\n        If stoplineno is greater than or equal to 0, then stop at line\n        greater than or equal to the stopline.  If stoplineno is -1, then\n        don't stop at all.\n        "
        self.stopframe = stopframe
        self.returnframe = returnframe
        self.quitting = False
        self.stoplineno = stoplineno

    def set_until(self, frame, lineno=None):
        "Stop when the line with the lineno greater than the current one is\n        reached or when returning from current frame."
        if lineno is None:
            lineno = frame.f_lineno + 1
        self._set_stopinfo(frame, frame, lineno)

    def set_step(self):
        "Stop after one line of code."
        if self.frame_returning:
            caller_frame = self.frame_returning.f_back
            if caller_frame and (not caller_frame.f_trace):
                caller_frame.f_trace = self.trace_dispatch
        self._set_stopinfo(None, None)

    def set_next(self, frame):
        "Stop on the next line in or below the given frame."
        self._set_stopinfo(frame, None)

    def set_return(self, frame):
        "Stop when returning from the given frame."
        if frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS:
            self._set_stopinfo(frame, None, (-1))
        else:
            self._set_stopinfo(frame.f_back, frame)

    def set_trace(self, frame=None):
        "Start debugging from frame.\n\n        If frame is not specified, debugging starts from caller's frame.\n        "
        if frame is None:
            frame = sys._getframe().f_back
        self.reset()
        while frame:
            frame.f_trace = self.trace_dispatch
            self.botframe = frame
            frame = frame.f_back
        self.set_step()
        sys.settrace(self.trace_dispatch)

    def set_continue(self):
        "Stop only at breakpoints or when finished.\n\n        If there are no breakpoints, set the system trace function to None.\n        "
        self._set_stopinfo(self.botframe, None, (-1))
        if not self.breaks:
            sys.settrace(None)
            frame = sys._getframe().f_back
            while frame and (frame is not self.botframe):
                del frame.f_trace
                frame = frame.f_back

    def set_quit(self):
        "Set quitting attribute to True.\n\n        Raises BdbQuit exception in the next call to a dispatch_*() method.\n        "
        self.stopframe = self.botframe
        self.returnframe = None
        self.quitting = True
        sys.settrace(None)

    def _add_to_breaks(self, filename, lineno):
        "Add breakpoint to breaks, if not already there."
        bp_linenos = self.breaks.setdefault(filename, [])
        if lineno not in bp_linenos:
            bp_linenos.append(lineno)

    def set_break(self, filename, lineno, temporary=False, cond=None, funcname=None):
        "Set a new breakpoint for filename:lineno.\n\n        If lineno doesn't exist for the filename, return an error message.\n        The filename should be in canonical form.\n        "
        filename = self.canonic(filename)
        import linecache

        line = linecache.getline(filename, lineno)
        if not line:
            return "Line %s:%d does not exist" % (filename, lineno)
        self._add_to_breaks(filename, lineno)
        bp = Breakpoint(filename, lineno, temporary, cond, funcname)
        return None

    def _load_breaks(self):
        "Apply all breakpoints (set in other instances) to this one.\n\n        Populates this instance's breaks list from the Breakpoint class's\n        list, which can have breakpoints set by another Bdb instance. This\n        is necessary for interactive sessions to keep the breakpoints\n        active across multiple calls to run().\n        "
        for (filename, lineno) in Breakpoint.bplist.keys():
            self._add_to_breaks(filename, lineno)

    def _prune_breaks(self, filename, lineno):
        "Prune breakpoints for filename:lineno.\n\n        A list of breakpoints is maintained in the Bdb instance and in\n        the Breakpoint class.  If a breakpoint in the Bdb instance no\n        longer exists in the Breakpoint class, then it's removed from the\n        Bdb instance.\n        "
        if (filename, lineno) not in Breakpoint.bplist:
            self.breaks[filename].remove(lineno)
        if not self.breaks[filename]:
            del self.breaks[filename]

    def clear_break(self, filename, lineno):
        "Delete breakpoints for filename:lineno.\n\n        If no breakpoints were set, return an error message.\n        "
        filename = self.canonic(filename)
        if filename not in self.breaks:
            return "There are no breakpoints in %s" % filename
        if lineno not in self.breaks[filename]:
            return "There is no breakpoint at %s:%d" % (filename, lineno)
        for bp in Breakpoint.bplist[(filename, lineno)][:]:
            bp.deleteMe()
        self._prune_breaks(filename, lineno)
        return None

    def clear_bpbynumber(self, arg):
        "Delete a breakpoint by its index in Breakpoint.bpbynumber.\n\n        If arg is invalid, return an error message.\n        "
        try:
            bp = self.get_bpbynumber(arg)
        except ValueError as err:
            return str(err)
        bp.deleteMe()
        self._prune_breaks(bp.file, bp.line)
        return None

    def clear_all_file_breaks(self, filename):
        "Delete all breakpoints in filename.\n\n        If none were set, return an error message.\n        "
        filename = self.canonic(filename)
        if filename not in self.breaks:
            return "There are no breakpoints in %s" % filename
        for line in self.breaks[filename]:
            blist = Breakpoint.bplist[(filename, line)]
            for bp in blist:
                bp.deleteMe()
        del self.breaks[filename]
        return None

    def clear_all_breaks(self):
        "Delete all existing breakpoints.\n\n        If none were set, return an error message.\n        "
        if not self.breaks:
            return "There are no breakpoints"
        for bp in Breakpoint.bpbynumber:
            if bp:
                bp.deleteMe()
        self.breaks = {}
        return None

    def get_bpbynumber(self, arg):
        "Return a breakpoint by its index in Breakpoint.bybpnumber.\n\n        For invalid arg values or if the breakpoint doesn't exist,\n        raise a ValueError.\n        "
        if not arg:
            raise ValueError("Breakpoint number expected")
        try:
            number = int(arg)
        except ValueError:
            raise ValueError(("Non-numeric breakpoint number %s" % arg)) from None
        try:
            bp = Breakpoint.bpbynumber[number]
        except IndexError:
            raise ValueError(("Breakpoint number %d out of range" % number)) from None
        if bp is None:
            raise ValueError(("Breakpoint %d already deleted" % number))
        return bp

    def get_break(self, filename, lineno):
        "Return True if there is a breakpoint for filename:lineno."
        filename = self.canonic(filename)
        return (filename in self.breaks) and (lineno in self.breaks[filename])

    def get_breaks(self, filename, lineno):
        "Return all breakpoints for filename:lineno.\n\n        If no breakpoints are set, return an empty list.\n        "
        filename = self.canonic(filename)
        return (
            (filename in self.breaks)
            and (lineno in self.breaks[filename])
            and Breakpoint.bplist[(filename, lineno)]
        ) or []

    def get_file_breaks(self, filename):
        "Return all lines with breakpoints for filename.\n\n        If no breakpoints are set, return an empty list.\n        "
        filename = self.canonic(filename)
        if filename in self.breaks:
            return self.breaks[filename]
        else:
            return []

    def get_all_breaks(self):
        "Return all breakpoints that are set."
        return self.breaks

    def get_stack(self, f, t):
        "Return a list of (frame, lineno) in a stack trace and a size.\n\n        List starts with original calling frame, if there is one.\n        Size may be number of frames above or below f.\n        "
        stack = []
        if t and (t.tb_frame is f):
            t = t.tb_next
        while f is not None:
            stack.append((f, f.f_lineno))
            if f is self.botframe:
                break
            f = f.f_back
        stack.reverse()
        i = max(0, (len(stack) - 1))
        while t is not None:
            stack.append((t.tb_frame, t.tb_lineno))
            t = t.tb_next
        if f is None:
            i = max(0, (len(stack) - 1))
        return (stack, i)

    def format_stack_entry(self, frame_lineno, lprefix=": "):
        "Return a string with information about a stack entry.\n\n        The stack entry frame_lineno is a (frame, lineno) tuple.  The\n        return string contains the canonical filename, the function name\n        or '<lambda>', the input arguments, the return value, and the\n        line of code (if it exists).\n\n        "
        import linecache, reprlib

        (frame, lineno) = frame_lineno
        filename = self.canonic(frame.f_code.co_filename)
        s = "%s(%r)" % (filename, lineno)
        if frame.f_code.co_name:
            s += frame.f_code.co_name
        else:
            s += "<lambda>"
        s += "()"
        if "__return__" in frame.f_locals:
            rv = frame.f_locals["__return__"]
            s += "->"
            s += reprlib.repr(rv)
        line = linecache.getline(filename, lineno, frame.f_globals)
        if line:
            s += lprefix + line.strip()
        return s

    def run(self, cmd, globals=None, locals=None):
        "Debug a statement executed via the exec() function.\n\n        globals defaults to __main__.dict; locals defaults to globals.\n        "
        if globals is None:
            import __main__

            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        if isinstance(cmd, str):
            cmd = compile(cmd, "<string>", "exec")
        sys.settrace(self.trace_dispatch)
        try:
            exec(cmd, globals, locals)
        except BdbQuit:
            pass
        finally:
            self.quitting = True
            sys.settrace(None)

    def runeval(self, expr, globals=None, locals=None):
        "Debug an expression executed via the eval() function.\n\n        globals defaults to __main__.dict; locals defaults to globals.\n        "
        if globals is None:
            import __main__

            globals = __main__.__dict__
        if locals is None:
            locals = globals
        self.reset()
        sys.settrace(self.trace_dispatch)
        try:
            return eval(expr, globals, locals)
        except BdbQuit:
            pass
        finally:
            self.quitting = True
            sys.settrace(None)

    def runctx(self, cmd, globals, locals):
        "For backwards-compatibility.  Defers to run()."
        self.run(cmd, globals, locals)

    def runcall(self, func, /, *args, **kwds):
        "Debug a single function call.\n\n        Return the result of the function call.\n        "
        self.reset()
        sys.settrace(self.trace_dispatch)
        res = None
        try:
            res = func(*args, **kwds)
        except BdbQuit:
            pass
        finally:
            self.quitting = True
            sys.settrace(None)
        return res


def set_trace():
    "Start debugging with a Bdb instance from the caller's frame."
    Bdb().set_trace()


class Breakpoint:
    "Breakpoint class.\n\n    Implements temporary breakpoints, ignore counts, disabling and\n    (re)-enabling, and conditionals.\n\n    Breakpoints are indexed by number through bpbynumber and by\n    the (file, line) tuple using bplist.  The former points to a\n    single instance of class Breakpoint.  The latter points to a\n    list of such instances since there may be more than one\n    breakpoint per line.\n\n    When creating a breakpoint, its associated filename should be\n    in canonical form.  If funcname is defined, a breakpoint hit will be\n    counted when the first line of that function is executed.  A\n    conditional breakpoint always counts a hit.\n    "
    next = 1
    bplist = {}
    bpbynumber = [None]

    def __init__(self, file, line, temporary=False, cond=None, funcname=None):
        self.funcname = funcname
        self.func_first_executable_line = None
        self.file = file
        self.line = line
        self.temporary = temporary
        self.cond = cond
        self.enabled = True
        self.ignore = 0
        self.hits = 0
        self.number = Breakpoint.next
        Breakpoint.next += 1
        self.bpbynumber.append(self)
        if (file, line) in self.bplist:
            self.bplist[(file, line)].append(self)
        else:
            self.bplist[(file, line)] = [self]

    @staticmethod
    def clearBreakpoints():
        Breakpoint.next = 1
        Breakpoint.bplist = {}
        Breakpoint.bpbynumber = [None]

    def deleteMe(self):
        "Delete the breakpoint from the list associated to a file:line.\n\n        If it is the last breakpoint in that position, it also deletes\n        the entry for the file:line.\n        "
        index = (self.file, self.line)
        self.bpbynumber[self.number] = None
        self.bplist[index].remove(self)
        if not self.bplist[index]:
            del self.bplist[index]

    def enable(self):
        "Mark the breakpoint as enabled."
        self.enabled = True

    def disable(self):
        "Mark the breakpoint as disabled."
        self.enabled = False

    def bpprint(self, out=None):
        "Print the output of bpformat().\n\n        The optional out argument directs where the output is sent\n        and defaults to standard output.\n        "
        if out is None:
            out = sys.stdout
        print(self.bpformat(), file=out)

    def bpformat(self):
        "Return a string with information about the breakpoint.\n\n        The information includes the breakpoint number, temporary\n        status, file:line position, break condition, number of times to\n        ignore, and number of times hit.\n\n        "
        if self.temporary:
            disp = "del  "
        else:
            disp = "keep "
        if self.enabled:
            disp = disp + "yes  "
        else:
            disp = disp + "no   "
        ret = "%-4dbreakpoint   %s at %s:%d" % (self.number, disp, self.file, self.line)
        if self.cond:
            ret += "\n\tstop only if %s" % (self.cond,)
        if self.ignore:
            ret += "\n\tignore next %d hits" % (self.ignore,)
        if self.hits:
            if self.hits > 1:
                ss = "s"
            else:
                ss = ""
            ret += "\n\tbreakpoint already hit %d time%s" % (self.hits, ss)
        return ret

    def __str__(self):
        "Return a condensed description of the breakpoint."
        return "breakpoint %s at %s:%s" % (self.number, self.file, self.line)


def checkfuncname(b, frame):
    "Return True if break should happen here.\n\n    Whether a break should happen depends on the way that b (the breakpoint)\n    was set.  If it was set via line number, check if b.line is the same as\n    the one in the frame.  If it was set via function name, check if this is\n    the right function and if it is on the first executable line.\n    "
    if not b.funcname:
        if b.line != frame.f_lineno:
            return False
        return True
    if frame.f_code.co_name != b.funcname:
        return False
    if not b.func_first_executable_line:
        b.func_first_executable_line = frame.f_lineno
    if b.func_first_executable_line != frame.f_lineno:
        return False
    return True


def effective(file, line, frame):
    "Determine which breakpoint for this file:line is to be acted upon.\n\n    Called only if we know there is a breakpoint at this location.  Return\n    the breakpoint that was triggered and a boolean that indicates if it is\n    ok to delete a temporary breakpoint.  Return (None, None) if there is no\n    matching breakpoint.\n    "
    possibles = Breakpoint.bplist[(file, line)]
    for b in possibles:
        if not b.enabled:
            continue
        if not checkfuncname(b, frame):
            continue
        b.hits += 1
        if not b.cond:
            if b.ignore > 0:
                b.ignore -= 1
                continue
            else:
                return (b, True)
        else:
            try:
                val = eval(b.cond, frame.f_globals, frame.f_locals)
                if val:
                    if b.ignore > 0:
                        b.ignore -= 1
                    else:
                        return (b, True)
            except:
                return (b, False)
    return (None, None)


class Tdb(Bdb):
    def user_call(self, frame, args):
        name = frame.f_code.co_name
        if not name:
            name = "???"
        print("+++ call", name, args)

    def user_line(self, frame):
        import linecache

        name = frame.f_code.co_name
        if not name:
            name = "???"
        fn = self.canonic(frame.f_code.co_filename)
        line = linecache.getline(fn, frame.f_lineno, frame.f_globals)
        print("+++", fn, frame.f_lineno, name, ":", line.strip())

    def user_return(self, frame, retval):
        print("+++ return", retval)

    def user_exception(self, frame, exc_stuff):
        print("+++ exception", exc_stuff)
        self.set_continue()


def foo(n):
    print("foo(", n, ")")
    x = bar((n * 10))
    print("bar returned", x)


def bar(a):
    print("bar(", a, ")")
    return a / 2


def test():
    t = Tdb()
    t.run("import bdb; bdb.foo(10)")
