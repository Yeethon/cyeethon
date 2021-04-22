"Run Python's test suite in a fast, rigorous way.\n\nThe defaults are meant to be reasonably thorough, while skipping certain\ntests that can be time-consuming or resource-intensive (e.g. largefile),\nor distracting (e.g. audio and gui). These defaults can be overridden by\nsimply passing a -u option to this script.\n\n"
import os
import sys
import test.support


def is_multiprocess_flag(arg):
    return arg.startswith("-j") or arg.startswith("--multiprocess")


def is_resource_use_flag(arg):
    return arg.startswith("-u") or arg.startswith("--use")


def main(regrtest_args):
    args = [sys.executable, "-u", "-W", "default", "-bb", "-E"]
    args.extend(test.support.args_from_interpreter_flags())
    args.extend(["-m", "test", "-r", "-w"])
    if sys.platform == "win32":
        args.append("-n")
    if not any((is_multiprocess_flag(arg) for arg in regrtest_args)):
        args.extend(["-j", "0"])
    if not any((is_resource_use_flag(arg) for arg in regrtest_args)):
        args.extend(["-u", "all,-largefile,-audio,-gui"])
    args.extend(regrtest_args)
    print(" ".join(args))
    if sys.platform == "win32":
        from subprocess import call

        sys.exit(call(args))
    else:
        os.execv(sys.executable, args)


if __name__ == "__main__":
    main(sys.argv[1:])
