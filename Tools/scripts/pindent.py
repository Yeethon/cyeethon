STEPSIZE = 8
TABSIZE = 8
EXPANDTABS = False
import io
import re
import sys

next = {}
next["if"] = next["elif"] = ("elif", "else", "end")
next["while"] = next["for"] = ("else", "end")
next["try"] = ("except", "finally")
next["except"] = ("except", "else", "finally", "end")
next["else"] = next["finally"] = next["with"] = next["def"] = next["class"] = "end"
next["end"] = ()
start = ("if", "while", "for", "try", "with", "def", "class")


class PythonIndenter:
    def __init__(
        self,
        fpi=sys.stdin,
        fpo=sys.stdout,
        indentsize=STEPSIZE,
        tabsize=TABSIZE,
        expandtabs=EXPANDTABS,
    ):
        self.fpi = fpi
        self.fpo = fpo
        self.indentsize = indentsize
        self.tabsize = tabsize
        self.lineno = 0
        self.expandtabs = expandtabs
        self._write = fpo.write
        self.kwprog = re.compile(
            "^(?:\\s|\\\\\\n)*(?P<kw>[a-z]+)((?:\\s|\\\\\\n)+(?P<id>[a-zA-Z_]\\w*))?[^\\w]"
        )
        self.endprog = re.compile(
            "^(?:\\s|\\\\\\n)*#?\\s*end\\s+(?P<kw>[a-z]+)(\\s+(?P<id>[a-zA-Z_]\\w*))?[^\\w]"
        )
        self.wsprog = re.compile("^[ \\t]*")

    def write(self, line):
        if self.expandtabs:
            self._write(line.expandtabs(self.tabsize))
        else:
            self._write(line)

    def readline(self):
        line = self.fpi.readline()
        if line:
            self.lineno += 1
        return line

    def error(self, fmt, *args):
        if args:
            fmt = fmt % args
        sys.stderr.write(("Error at line %d: %s\n" % (self.lineno, fmt)))
        self.write(("### %s ###\n" % fmt))

    def getline(self):
        line = self.readline()
        while line[(-2):] == "\\\n":
            line2 = self.readline()
            if not line2:
                break
            line += line2
        return line

    def putline(self, line, indent):
        (tabs, spaces) = divmod((indent * self.indentsize), self.tabsize)
        i = self.wsprog.match(line).end()
        line = line[i:]
        if line[:1] not in ("\n", "\r", ""):
            line = (("\t" * tabs) + (" " * spaces)) + line
        self.write(line)

    def reformat(self):
        stack = []
        while True:
            line = self.getline()
            if not line:
                break
            m = self.endprog.match(line)
            if m:
                kw = "end"
                kw2 = m.group("kw")
                if not stack:
                    self.error("unexpected end")
                elif stack.pop()[0] != kw2:
                    self.error("unmatched end")
                self.putline(line, len(stack))
                continue
            m = self.kwprog.match(line)
            if m:
                kw = m.group("kw")
                if kw in start:
                    self.putline(line, len(stack))
                    stack.append((kw, kw))
                    continue
                if (kw in next) and stack:
                    self.putline(line, (len(stack) - 1))
                    (kwa, kwb) = stack[(-1)]
                    stack[(-1)] = (kwa, kw)
                    continue
            self.putline(line, len(stack))
        if stack:
            self.error("unterminated keywords")
            for (kwa, kwb) in stack:
                self.write(("\t%s\n" % kwa))

    def delete(self):
        begin_counter = 0
        end_counter = 0
        while True:
            line = self.getline()
            if not line:
                break
            m = self.endprog.match(line)
            if m:
                end_counter += 1
                continue
            m = self.kwprog.match(line)
            if m:
                kw = m.group("kw")
                if kw in start:
                    begin_counter += 1
            self.write(line)
        if (begin_counter - end_counter) < 0:
            sys.stderr.write("Warning: input contained more end tags than expected\n")
        elif (begin_counter - end_counter) > 0:
            sys.stderr.write("Warning: input contained less end tags than expected\n")

    def complete(self):
        stack = []
        todo = []
        currentws = thisid = firstkw = lastkw = topid = ""
        while True:
            line = self.getline()
            i = self.wsprog.match(line).end()
            m = self.endprog.match(line)
            if m:
                thiskw = "end"
                endkw = m.group("kw")
                thisid = m.group("id")
            else:
                m = self.kwprog.match(line)
                if m:
                    thiskw = m.group("kw")
                    if thiskw not in next:
                        thiskw = ""
                    if thiskw in ("def", "class"):
                        thisid = m.group("id")
                    else:
                        thisid = ""
                elif line[i : (i + 1)] in ("\n", "#"):
                    todo.append(line)
                    continue
                else:
                    thiskw = ""
            indentws = line[:i]
            indent = len(indentws.expandtabs(self.tabsize))
            current = len(currentws.expandtabs(self.tabsize))
            while indent < current:
                if firstkw:
                    if topid:
                        s = "# end %s %s\n" % (firstkw, topid)
                    else:
                        s = "# end %s\n" % firstkw
                    self.write((currentws + s))
                    firstkw = lastkw = ""
                (currentws, firstkw, lastkw, topid) = stack.pop()
                current = len(currentws.expandtabs(self.tabsize))
            if (indent == current) and firstkw:
                if thiskw == "end":
                    if endkw != firstkw:
                        self.error("mismatched end")
                    firstkw = lastkw = ""
                elif (not thiskw) or (thiskw in start):
                    if topid:
                        s = "# end %s %s\n" % (firstkw, topid)
                    else:
                        s = "# end %s\n" % firstkw
                    self.write((currentws + s))
                    firstkw = lastkw = topid = ""
            if indent > current:
                stack.append((currentws, firstkw, lastkw, topid))
                if thiskw and (thiskw not in start):
                    thiskw = ""
                (currentws, firstkw, lastkw, topid) = (indentws, thiskw, thiskw, thisid)
            if thiskw:
                if thiskw in start:
                    firstkw = lastkw = thiskw
                    topid = thisid
                else:
                    lastkw = thiskw
            for l in todo:
                self.write(l)
            todo = []
            if not line:
                break
            self.write(line)


def complete_filter(
    input=sys.stdin,
    output=sys.stdout,
    stepsize=STEPSIZE,
    tabsize=TABSIZE,
    expandtabs=EXPANDTABS,
):
    pi = PythonIndenter(input, output, stepsize, tabsize, expandtabs)
    pi.complete()


def delete_filter(
    input=sys.stdin,
    output=sys.stdout,
    stepsize=STEPSIZE,
    tabsize=TABSIZE,
    expandtabs=EXPANDTABS,
):
    pi = PythonIndenter(input, output, stepsize, tabsize, expandtabs)
    pi.delete()


def reformat_filter(
    input=sys.stdin,
    output=sys.stdout,
    stepsize=STEPSIZE,
    tabsize=TABSIZE,
    expandtabs=EXPANDTABS,
):
    pi = PythonIndenter(input, output, stepsize, tabsize, expandtabs)
    pi.reformat()


def complete_string(source, stepsize=STEPSIZE, tabsize=TABSIZE, expandtabs=EXPANDTABS):
    input = io.StringIO(source)
    output = io.StringIO()
    pi = PythonIndenter(input, output, stepsize, tabsize, expandtabs)
    pi.complete()
    return output.getvalue()


def delete_string(source, stepsize=STEPSIZE, tabsize=TABSIZE, expandtabs=EXPANDTABS):
    input = io.StringIO(source)
    output = io.StringIO()
    pi = PythonIndenter(input, output, stepsize, tabsize, expandtabs)
    pi.delete()
    return output.getvalue()


def reformat_string(source, stepsize=STEPSIZE, tabsize=TABSIZE, expandtabs=EXPANDTABS):
    input = io.StringIO(source)
    output = io.StringIO()
    pi = PythonIndenter(input, output, stepsize, tabsize, expandtabs)
    pi.reformat()
    return output.getvalue()


def make_backup(filename):
    import os, os.path

    backup = filename + "~"
    if os.path.lexists(backup):
        try:
            os.remove(backup)
        except OSError:
            print(("Can't remove backup %r" % (backup,)), file=sys.stderr)
    try:
        os.rename(filename, backup)
    except OSError:
        print(("Can't rename %r to %r" % (filename, backup)), file=sys.stderr)


def complete_file(filename, stepsize=STEPSIZE, tabsize=TABSIZE, expandtabs=EXPANDTABS):
    with open(filename, "r") as f:
        source = f.read()
    result = complete_string(source, stepsize, tabsize, expandtabs)
    if source == result:
        return 0
    make_backup(filename)
    with open(filename, "w") as f:
        f.write(result)
    return 1


def delete_file(filename, stepsize=STEPSIZE, tabsize=TABSIZE, expandtabs=EXPANDTABS):
    with open(filename, "r") as f:
        source = f.read()
    result = delete_string(source, stepsize, tabsize, expandtabs)
    if source == result:
        return 0
    make_backup(filename)
    with open(filename, "w") as f:
        f.write(result)
    return 1


def reformat_file(filename, stepsize=STEPSIZE, tabsize=TABSIZE, expandtabs=EXPANDTABS):
    with open(filename, "r") as f:
        source = f.read()
    result = reformat_string(source, stepsize, tabsize, expandtabs)
    if source == result:
        return 0
    make_backup(filename)
    with open(filename, "w") as f:
        f.write(result)
    return 1


usage = (
    "\nusage: pindent (-c|-d|-r) [-s stepsize] [-t tabsize] [-e] [file] ...\n-c         : complete a correctly indented program (add #end directives)\n-d         : delete #end directives\n-r         : reformat a completed program (use #end directives)\n-s stepsize: indentation step (default %(STEPSIZE)d)\n-t tabsize : the worth in spaces of a tab (default %(TABSIZE)d)\n-e         : expand TABs into spaces (default OFF)\n[file] ... : files are changed in place, with backups in file~\nIf no files are specified or a single - is given,\nthe program acts as a filter (reads stdin, writes stdout).\n"
    % vars()
)


def error_both(op1, op2):
    sys.stderr.write(
        (
            ((("Error: You can not specify both " + op1) + " and -") + op2[0])
            + " at the same time\n"
        )
    )
    sys.stderr.write(usage)
    sys.exit(2)


def test():
    import getopt

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "cdrs:t:e")
    except getopt.error as msg:
        sys.stderr.write(("Error: %s\n" % msg))
        sys.stderr.write(usage)
        sys.exit(2)
    action = None
    stepsize = STEPSIZE
    tabsize = TABSIZE
    expandtabs = EXPANDTABS
    for (o, a) in opts:
        if o == "-c":
            if action:
                error_both(o, action)
            action = "complete"
        elif o == "-d":
            if action:
                error_both(o, action)
            action = "delete"
        elif o == "-r":
            if action:
                error_both(o, action)
            action = "reformat"
        elif o == "-s":
            stepsize = int(a)
        elif o == "-t":
            tabsize = int(a)
        elif o == "-e":
            expandtabs = True
    if not action:
        sys.stderr.write("You must specify -c(omplete), -d(elete) or -r(eformat)\n")
        sys.stderr.write(usage)
        sys.exit(2)
    if (not args) or (args == ["-"]):
        action = eval((action + "_filter"))
        action(sys.stdin, sys.stdout, stepsize, tabsize, expandtabs)
    else:
        action = eval((action + "_file"))
        for filename in args:
            action(filename, stepsize, tabsize, expandtabs)


if __name__ == "__main__":
    test()
