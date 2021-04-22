from __future__ import print_function
import os
import re
import sys
import subprocess
from shutil import copy


def find_all_on_path(filename, extras=None):
    entries = os.environ["PATH"].split(os.pathsep)
    ret = []
    for p in entries:
        fname = os.path.abspath(os.path.join(p, filename))
        if os.path.isfile(fname) and (fname not in ret):
            ret.append(fname)
    if extras:
        for p in extras:
            fname = os.path.abspath(os.path.join(p, filename))
            if os.path.isfile(fname) and (fname not in ret):
                ret.append(fname)
    return ret


def find_working_perl(perls):
    for perl in perls:
        try:
            subprocess.check_output([perl, "-e", "use Win32;"])
        except subprocess.CalledProcessError:
            continue
        else:
            return perl
    if perls:
        print("The following perl interpreters were found:")
        for p in perls:
            print(" ", p)
        print(" None of these versions appear suitable for building OpenSSL")
    else:
        print("NO perl interpreters were found on this machine at all!")
    print(" Please install ActivePerl and ensure it appears on your path")


def copy_includes(makefile, suffix):
    dir = ("inc" + suffix) + "\\openssl"
    try:
        os.makedirs(dir)
    except OSError:
        pass
    copy_if_different = "$(PERL) $(SRC_D)\\util\\copy-if-different.pl"
    with open(makefile) as fin:
        for line in fin:
            if copy_if_different in line:
                (perl, script, src, dest) = line.split()
                if not ("$(INCO_D)" in dest):
                    continue
                src = src.replace("$(SRC_D)", ".").strip('"')
                dest = dest.strip('"').replace("$(INCO_D)", dir)
                print("copying", src, "to", dest)
                copy(src, dest)


def run_configure(configure, do_script):
    print((("perl Configure " + configure) + " no-idea no-mdc2"))
    os.system((("perl Configure " + configure) + " no-idea no-mdc2"))
    print(do_script)
    os.system(do_script)


def fix_uplink():
    with open("ms\\uplink.c", "r", encoding="utf-8") as f1:
        code = list(f1)
    os.replace("ms\\uplink.c", "ms\\uplink.c.orig")
    already_patched = False
    with open("ms\\uplink.c", "w", encoding="utf-8") as f2:
        for line in code:
            if not already_patched:
                if re.search("MODIFIED FOR CPYTHON _ssl MODULE", line):
                    already_patched = True
                elif re.match(
                    "^\\s+if\\s*\\(\\(h\\s*=\\s*GetModuleHandle[AW]?\\(NULL\\)\\)\\s*==\\s*NULL\\)",
                    line,
                ):
                    f2.write("/* MODIFIED FOR CPYTHON _ssl MODULE */\n")
                    f2.write(
                        'if ((h = GetModuleHandleW(L"_ssl.pyd")) == NULL) if ((h = GetModuleHandleW(L"_ssl_d.pyd")) == NULL)\n'
                    )
                    already_patched = True
            f2.write(line)
    if not already_patched:
        print("WARN: failed to patch ms\\uplink.c")


def prep(arch):
    makefile_template = "ms\\ntdll{}.mak"
    generated_makefile = makefile_template.format("")
    if arch == "x86":
        configure = "VC-WIN32"
        do_script = "ms\\do_nasm"
        suffix = "32"
    elif arch == "amd64":
        configure = "VC-WIN64A"
        do_script = "ms\\do_win64a"
        suffix = "64"
    else:
        raise ValueError(("Unrecognized platform: %s" % arch))
    print("Creating the makefiles...")
    sys.stdout.flush()
    run_configure(configure, do_script)
    makefile = makefile_template.format(suffix)
    try:
        os.unlink(makefile)
    except FileNotFoundError:
        pass
    os.rename(generated_makefile, makefile)
    copy_includes(makefile, suffix)
    print("patching ms\\uplink.c...")
    fix_uplink()


def main():
    if len(sys.argv) == 1:
        print(
            "Not enough arguments: directory containing OpenSSL",
            "sources must be supplied",
        )
        sys.exit(1)
    if (len(sys.argv) == 3) and (sys.argv[2] not in ("x86", "amd64")):
        print("Second argument must be x86 or amd64")
        sys.exit(1)
    if len(sys.argv) > 3:
        print(
            "Too many arguments supplied, all we need is the directory",
            "containing OpenSSL sources and optionally the architecture",
        )
        sys.exit(1)
    ssl_dir = sys.argv[1]
    arch = sys.argv[2] if (len(sys.argv) >= 3) else None
    if not os.path.isdir(ssl_dir):
        print(ssl_dir, "is not an existing directory!")
        sys.exit(1)
    perls = find_all_on_path(
        "perl.exe", ["\\perl\\bin", "C:\\perl\\bin", "\\perl64\\bin", "C:\\perl64\\bin"]
    )
    perl = find_working_perl(perls)
    if perl:
        print(("Found a working perl at '%s'" % (perl,)))
    else:
        sys.exit(1)
    if not find_all_on_path("nmake.exe"):
        print("Could not find nmake.exe, try running env.bat")
        sys.exit(1)
    if not find_all_on_path("nasm.exe"):
        print("Could not find nasm.exe, please add to PATH")
        sys.exit(1)
    sys.stdout.flush()
    os.environ["PATH"] = (os.path.dirname(perl) + os.pathsep) + os.environ["PATH"]
    old_cwd = os.getcwd()
    try:
        os.chdir(ssl_dir)
        if arch:
            prep(arch)
        else:
            for arch in ["amd64", "x86"]:
                prep(arch)
    finally:
        os.chdir(old_cwd)


if __name__ == "__main__":
    main()
