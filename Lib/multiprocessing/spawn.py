import os
import sys
import runpy
import types
from . import get_start_method, set_start_method
from . import process
from .context import reduction
from . import util

__all__ = [
    "_main",
    "freeze_support",
    "set_executable",
    "get_executable",
    "get_preparation_data",
    "get_command_line",
    "import_main_path",
]
if sys.platform != "win32":
    WINEXE = False
    WINSERVICE = False
else:
    WINEXE = getattr(sys, "frozen", False)
    WINSERVICE = sys.executable.lower().endswith("pythonservice.exe")
if WINSERVICE:
    _python_exe = os.path.join(sys.exec_prefix, "python.exe")
else:
    _python_exe = sys.executable


def set_executable(exe):
    global _python_exe
    _python_exe = exe


def get_executable():
    return _python_exe


def is_forking(argv):
    "\n    Return whether commandline indicates we are forking\n    "
    if (len(argv) >= 2) and (argv[1] == "--multiprocessing-fork"):
        return True
    else:
        return False


def freeze_support():
    "\n    Run code for process object if this in not the main process\n    "
    if is_forking(sys.argv):
        kwds = {}
        for arg in sys.argv[2:]:
            (name, value) = arg.split("=")
            if value == "None":
                kwds[name] = None
            else:
                kwds[name] = int(value)
        spawn_main(**kwds)
        sys.exit()


def get_command_line(**kwds):
    "\n    Returns prefix of command line used for spawning a child process\n    "
    if getattr(sys, "frozen", False):
        return [sys.executable, "--multiprocessing-fork"] + [
            ("%s=%r" % item) for item in kwds.items()
        ]
    else:
        prog = "from multiprocessing.spawn import spawn_main; spawn_main(%s)"
        prog %= ", ".join((("%s=%r" % item) for item in kwds.items()))
        opts = util._args_from_interpreter_flags()
        return ([_python_exe] + opts) + ["-c", prog, "--multiprocessing-fork"]


def spawn_main(pipe_handle, parent_pid=None, tracker_fd=None):
    "\n    Run code specified by data received over pipe\n    "
    assert is_forking(sys.argv), "Not forking"
    if sys.platform == "win32":
        import msvcrt
        import _winapi

        if parent_pid is not None:
            source_process = _winapi.OpenProcess(
                (_winapi.SYNCHRONIZE | _winapi.PROCESS_DUP_HANDLE), False, parent_pid
            )
        else:
            source_process = None
        new_handle = reduction.duplicate(pipe_handle, source_process=source_process)
        fd = msvcrt.open_osfhandle(new_handle, os.O_RDONLY)
        parent_sentinel = source_process
    else:
        from . import resource_tracker

        resource_tracker._resource_tracker._fd = tracker_fd
        fd = pipe_handle
        parent_sentinel = os.dup(pipe_handle)
    exitcode = _main(fd, parent_sentinel)
    sys.exit(exitcode)


def _main(fd, parent_sentinel):
    with os.fdopen(fd, "rb", closefd=True) as from_parent:
        process.current_process()._inheriting = True
        try:
            preparation_data = reduction.pickle.load(from_parent)
            prepare(preparation_data)
            self = reduction.pickle.load(from_parent)
        finally:
            del process.current_process()._inheriting
    return self._bootstrap(parent_sentinel)


def _check_not_importing_main():
    if getattr(process.current_process(), "_inheriting", False):
        raise RuntimeError(
            "\n        An attempt has been made to start a new process before the\n        current process has finished its bootstrapping phase.\n\n        This probably means that you are not using fork to start your\n        child processes and you have forgotten to use the proper idiom\n        in the main module:\n\n            if __name__ == '__main__':\n                freeze_support()\n                ...\n\n        The \"freeze_support()\" line can be omitted if the program\n        is not going to be frozen to produce an executable."
        )


def get_preparation_data(name):
    "\n    Return info about parent needed by child to unpickle process object\n    "
    _check_not_importing_main()
    d = dict(
        log_to_stderr=util._log_to_stderr, authkey=process.current_process().authkey
    )
    if util._logger is not None:
        d["log_level"] = util._logger.getEffectiveLevel()
    sys_path = sys.path.copy()
    try:
        i = sys_path.index("")
    except ValueError:
        pass
    else:
        sys_path[i] = process.ORIGINAL_DIR
    d.update(
        name=name,
        sys_path=sys_path,
        sys_argv=sys.argv,
        orig_dir=process.ORIGINAL_DIR,
        dir=os.getcwd(),
        start_method=get_start_method(),
    )
    main_module = sys.modules["__main__"]
    main_mod_name = getattr(main_module.__spec__, "name", None)
    if main_mod_name is not None:
        d["init_main_from_name"] = main_mod_name
    elif (sys.platform != "win32") or ((not WINEXE) and (not WINSERVICE)):
        main_path = getattr(main_module, "__file__", None)
        if main_path is not None:
            if (not os.path.isabs(main_path)) and (process.ORIGINAL_DIR is not None):
                main_path = os.path.join(process.ORIGINAL_DIR, main_path)
            d["init_main_from_path"] = os.path.normpath(main_path)
    return d


old_main_modules = []


def prepare(data):
    "\n    Try to get current process ready to unpickle process object\n    "
    if "name" in data:
        process.current_process().name = data["name"]
    if "authkey" in data:
        process.current_process().authkey = data["authkey"]
    if ("log_to_stderr" in data) and data["log_to_stderr"]:
        util.log_to_stderr()
    if "log_level" in data:
        util.get_logger().setLevel(data["log_level"])
    if "sys_path" in data:
        sys.path = data["sys_path"]
    if "sys_argv" in data:
        sys.argv = data["sys_argv"]
    if "dir" in data:
        os.chdir(data["dir"])
    if "orig_dir" in data:
        process.ORIGINAL_DIR = data["orig_dir"]
    if "start_method" in data:
        set_start_method(data["start_method"], force=True)
    if "init_main_from_name" in data:
        _fixup_main_from_name(data["init_main_from_name"])
    elif "init_main_from_path" in data:
        _fixup_main_from_path(data["init_main_from_path"])


def _fixup_main_from_name(mod_name):
    current_main = sys.modules["__main__"]
    if (mod_name == "__main__") or mod_name.endswith(".__main__"):
        return
    if getattr(current_main.__spec__, "name", None) == mod_name:
        return
    old_main_modules.append(current_main)
    main_module = types.ModuleType("__mp_main__")
    main_content = runpy.run_module(mod_name, run_name="__mp_main__", alter_sys=True)
    main_module.__dict__.update(main_content)
    sys.modules["__main__"] = sys.modules["__mp_main__"] = main_module


def _fixup_main_from_path(main_path):
    current_main = sys.modules["__main__"]
    main_name = os.path.splitext(os.path.basename(main_path))[0]
    if main_name == "ipython":
        return
    if getattr(current_main, "__file__", None) == main_path:
        return
    old_main_modules.append(current_main)
    main_module = types.ModuleType("__mp_main__")
    main_content = runpy.run_path(main_path, run_name="__mp_main__")
    main_module.__dict__.update(main_content)
    sys.modules["__main__"] = sys.modules["__mp_main__"] = main_module


def import_main_path(main_path):
    "\n    Set sys.modules['__main__'] to module at main_path\n    "
    _fixup_main_from_path(main_path)
