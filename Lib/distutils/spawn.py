"distutils.spawn\n\nProvides the 'spawn()' function, a front-end to various platform-\nspecific functions for launching another program in a sub-process.\nAlso provides the 'find_executable()' to search the path for a given\nexecutable name.\n"
import sys
import os
import subprocess
from distutils.errors import DistutilsPlatformError, DistutilsExecError
from distutils.debug import DEBUG
from distutils import log

if sys.platform == "darwin":
    _cfg_target = None
    _cfg_target_split = None


def spawn(cmd, search_path=1, verbose=0, dry_run=0):
    "Run another program, specified as a command list 'cmd', in a new process.\n\n    'cmd' is just the argument list for the new process, ie.\n    cmd[0] is the program to run and cmd[1:] are the rest of its arguments.\n    There is no way to run a program with a name different from that of its\n    executable.\n\n    If 'search_path' is true (the default), the system's executable\n    search path will be used to find the program; otherwise, cmd[0]\n    must be the exact path to the executable.  If 'dry_run' is true,\n    the command will not actually be run.\n\n    Raise DistutilsExecError if running the program fails in any way; just\n    return on success.\n    "
    cmd = list(cmd)
    log.info(" ".join(cmd))
    if dry_run:
        return
    if search_path:
        executable = find_executable(cmd[0])
        if executable is not None:
            cmd[0] = executable
    env = None
    if sys.platform == "darwin":
        global _cfg_target, _cfg_target_split
        if _cfg_target is None:
            from distutils import sysconfig

            _cfg_target = sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET") or ""
            if _cfg_target:
                _cfg_target_split = [int(x) for x in _cfg_target.split(".")]
        if _cfg_target:
            cur_target = os.environ.get("MACOSX_DEPLOYMENT_TARGET", _cfg_target)
            if _cfg_target_split > [int(x) for x in cur_target.split(".")]:
                my_msg = (
                    '$MACOSX_DEPLOYMENT_TARGET mismatch: now "%s" but "%s" during configure'
                    % (cur_target, _cfg_target)
                )
                raise DistutilsPlatformError(my_msg)
            env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET=cur_target)
    try:
        proc = subprocess.Popen(cmd, env=env)
        proc.wait()
        exitcode = proc.returncode
    except OSError as exc:
        if not DEBUG:
            cmd = cmd[0]
        raise DistutilsExecError(
            ("command %r failed: %s" % (cmd, exc.args[(-1)]))
        ) from exc
    if exitcode:
        if not DEBUG:
            cmd = cmd[0]
        raise DistutilsExecError(
            ("command %r failed with exit code %s" % (cmd, exitcode))
        )


def find_executable(executable, path=None):
    "Tries to find 'executable' in the directories listed in 'path'.\n\n    A string listing directories separated by 'os.pathsep'; defaults to\n    os.environ['PATH'].  Returns the complete filename or None if not found.\n    "
    (_, ext) = os.path.splitext(executable)
    if (sys.platform == "win32") and (ext != ".exe"):
        executable = executable + ".exe"
    if os.path.isfile(executable):
        return executable
    if path is None:
        path = os.environ.get("PATH", None)
        if path is None:
            try:
                path = os.confstr("CS_PATH")
            except (AttributeError, ValueError):
                path = os.defpath
    if not path:
        return None
    paths = path.split(os.pathsep)
    for p in paths:
        f = os.path.join(p, executable)
        if os.path.isfile(f):
            return f
    return None
