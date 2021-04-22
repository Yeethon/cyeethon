"\nVirtual environment (venv) package for Python. Based on PEP 405.\n\nCopyright (C) 2011-2014 Vinay Sajip.\nLicensed to the PSF under a contributor agreement.\n"
import logging
import os
import shutil
import subprocess
import sys
import sysconfig
import types

CORE_VENV_DEPS = ("pip", "setuptools")
logger = logging.getLogger(__name__)


class EnvBuilder:
    "\n    This class exists to allow virtual environment creation to be\n    customized. The constructor parameters determine the builder's\n    behaviour when called upon to create a virtual environment.\n\n    By default, the builder makes the system (global) site-packages dir\n    *un*available to the created environment.\n\n    If invoked using the Python -m option, the default is to use copying\n    on Windows platforms but symlinks elsewhere. If instantiated some\n    other way, the default is to *not* use symlinks.\n\n    :param system_site_packages: If True, the system (global) site-packages\n                                 dir is available to created environments.\n    :param clear: If True, delete the contents of the environment directory if\n                  it already exists, before environment creation.\n    :param symlinks: If True, attempt to symlink rather than copy files into\n                     virtual environment.\n    :param upgrade: If True, upgrade an existing virtual environment.\n    :param with_pip: If True, ensure pip is installed in the virtual\n                     environment\n    :param prompt: Alternative terminal prefix for the environment.\n    :param upgrade_deps: Update the base venv modules to the latest on PyPI\n    "

    def __init__(
        self,
        system_site_packages=False,
        clear=False,
        symlinks=False,
        upgrade=False,
        with_pip=False,
        prompt=None,
        upgrade_deps=False,
    ):
        self.system_site_packages = system_site_packages
        self.clear = clear
        self.symlinks = symlinks
        self.upgrade = upgrade
        self.with_pip = with_pip
        if prompt == ".":
            prompt = os.path.basename(os.getcwd())
        self.prompt = prompt
        self.upgrade_deps = upgrade_deps

    def create(self, env_dir):
        "\n        Create a virtual environment in a directory.\n\n        :param env_dir: The target directory to create an environment in.\n\n        "
        env_dir = os.path.abspath(env_dir)
        context = self.ensure_directories(env_dir)
        true_system_site_packages = self.system_site_packages
        self.system_site_packages = False
        self.create_configuration(context)
        self.setup_python(context)
        if self.with_pip:
            self._setup_pip(context)
        if not self.upgrade:
            self.setup_scripts(context)
            self.post_setup(context)
        if true_system_site_packages:
            self.system_site_packages = True
            self.create_configuration(context)
        if self.upgrade_deps:
            self.upgrade_dependencies(context)

    def clear_directory(self, path):
        for fn in os.listdir(path):
            fn = os.path.join(path, fn)
            if os.path.islink(fn) or os.path.isfile(fn):
                os.remove(fn)
            elif os.path.isdir(fn):
                shutil.rmtree(fn)

    def ensure_directories(self, env_dir):
        "\n        Create the directories for the environment.\n\n        Returns a context object which holds paths in the environment,\n        for use by subsequent logic.\n        "

        def create_if_needed(d):
            if not os.path.exists(d):
                os.makedirs(d)
            elif os.path.islink(d) or os.path.isfile(d):
                raise ValueError(("Unable to create directory %r" % d))

        if os.path.exists(env_dir) and self.clear:
            self.clear_directory(env_dir)
        context = types.SimpleNamespace()
        context.env_dir = env_dir
        context.env_name = os.path.split(env_dir)[1]
        prompt = self.prompt if (self.prompt is not None) else context.env_name
        context.prompt = "(%s) " % prompt
        create_if_needed(env_dir)
        executable = sys._base_executable
        (dirname, exename) = os.path.split(os.path.abspath(executable))
        context.executable = executable
        context.python_dir = dirname
        context.python_exe = exename
        if sys.platform == "win32":
            binname = "Scripts"
            incpath = "Include"
            libpath = os.path.join(env_dir, "Lib", "site-packages")
        else:
            binname = "bin"
            incpath = "include"
            libpath = os.path.join(
                env_dir, "lib", ("python%d.%d" % sys.version_info[:2]), "site-packages"
            )
        context.inc_path = path = os.path.join(env_dir, incpath)
        create_if_needed(path)
        create_if_needed(libpath)
        if (
            (sys.maxsize > (2 ** 32))
            and (os.name == "posix")
            and (sys.platform != "darwin")
        ):
            link_path = os.path.join(env_dir, "lib64")
            if not os.path.exists(link_path):
                os.symlink("lib", link_path)
        context.bin_path = binpath = os.path.join(env_dir, binname)
        context.bin_name = binname
        context.env_exe = os.path.join(binpath, exename)
        create_if_needed(binpath)
        return context

    def create_configuration(self, context):
        "\n        Create a configuration file indicating where the environment's Python\n        was copied from, and whether the system site-packages should be made\n        available in the environment.\n\n        :param context: The information for the environment creation request\n                        being processed.\n        "
        context.cfg_path = path = os.path.join(context.env_dir, "pyvenv.cfg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(("home = %s\n" % context.python_dir))
            if self.system_site_packages:
                incl = "true"
            else:
                incl = "false"
            f.write(("include-system-site-packages = %s\n" % incl))
            f.write(("version = %d.%d.%d\n" % sys.version_info[:3]))
            if self.prompt is not None:
                f.write(
                    f"""prompt = {self.prompt!r}
"""
                )

    if os.name != "nt":

        def symlink_or_copy(self, src, dst, relative_symlinks_ok=False):
            "\n            Try symlinking a file, and if that fails, fall back to copying.\n            "
            force_copy = not self.symlinks
            if not force_copy:
                try:
                    if not os.path.islink(dst):
                        if relative_symlinks_ok:
                            assert os.path.dirname(src) == os.path.dirname(dst)
                            os.symlink(os.path.basename(src), dst)
                        else:
                            os.symlink(src, dst)
                except Exception:
                    logger.warning("Unable to symlink %r to %r", src, dst)
                    force_copy = True
            if force_copy:
                shutil.copyfile(src, dst)

    else:

        def symlink_or_copy(self, src, dst, relative_symlinks_ok=False):
            "\n            Try symlinking a file, and if that fails, fall back to copying.\n            "
            bad_src = os.path.lexists(src) and (not os.path.exists(src))
            if self.symlinks and (not bad_src) and (not os.path.islink(dst)):
                try:
                    if relative_symlinks_ok:
                        assert os.path.dirname(src) == os.path.dirname(dst)
                        os.symlink(os.path.basename(src), dst)
                    else:
                        os.symlink(src, dst)
                    return
                except Exception:
                    logger.warning("Unable to symlink %r to %r", src, dst)
            (basename, ext) = os.path.splitext(os.path.basename(src))
            srcfn = os.path.join(
                os.path.dirname(__file__), "scripts", "nt", (basename + ext)
            )
            if sysconfig.is_python_build(True) or (not os.path.isfile(srcfn)):
                if basename.endswith("_d"):
                    ext = "_d" + ext
                    basename = basename[:(-2)]
                if basename == "python":
                    basename = "venvlauncher"
                elif basename == "pythonw":
                    basename = "venvwlauncher"
                src = os.path.join(os.path.dirname(src), (basename + ext))
            else:
                src = srcfn
            if not os.path.exists(src):
                if not bad_src:
                    logger.warning("Unable to copy %r", src)
                return
            shutil.copyfile(src, dst)

    def setup_python(self, context):
        "\n        Set up a Python executable in the environment.\n\n        :param context: The information for the environment creation request\n                        being processed.\n        "
        binpath = context.bin_path
        path = context.env_exe
        copier = self.symlink_or_copy
        dirname = context.python_dir
        if os.name != "nt":
            copier(context.executable, path)
            if not os.path.islink(path):
                os.chmod(path, 493)
            for suffix in ("python", "python3", f"python3.{sys.version_info[1]}"):
                path = os.path.join(binpath, suffix)
                if not os.path.exists(path):
                    copier(context.env_exe, path, relative_symlinks_ok=True)
                    if not os.path.islink(path):
                        os.chmod(path, 493)
        else:
            if self.symlinks:
                suffixes = [
                    f
                    for f in os.listdir(dirname)
                    if (os.path.normcase(os.path.splitext(f)[1]) in (".exe", ".dll"))
                ]
                if sysconfig.is_python_build(True):
                    suffixes = [
                        f
                        for f in suffixes
                        if os.path.normcase(f).startswith(("python", "vcruntime"))
                    ]
            else:
                suffixes = [
                    "python.exe",
                    "python_d.exe",
                    "pythonw.exe",
                    "pythonw_d.exe",
                ]
            for suffix in suffixes:
                src = os.path.join(dirname, suffix)
                if os.path.lexists(src):
                    copier(src, os.path.join(binpath, suffix))
            if sysconfig.is_python_build(True):
                for (root, dirs, files) in os.walk(context.python_dir):
                    if "init.tcl" in files:
                        tcldir = os.path.basename(root)
                        tcldir = os.path.join(context.env_dir, "Lib", tcldir)
                        if not os.path.exists(tcldir):
                            os.makedirs(tcldir)
                        src = os.path.join(root, "init.tcl")
                        dst = os.path.join(tcldir, "init.tcl")
                        shutil.copyfile(src, dst)
                        break

    def _setup_pip(self, context):
        "Installs or upgrades pip in a virtual environment"
        cmd = [context.env_exe, "-Im", "ensurepip", "--upgrade", "--default-pip"]
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def setup_scripts(self, context):
        "\n        Set up scripts into the created environment from a directory.\n\n        This method installs the default scripts into the environment\n        being created. You can prevent the default installation by overriding\n        this method if you really need to, or if you need to specify\n        a different location for the scripts to install. By default, the\n        'scripts' directory in the venv package is used as the source of\n        scripts to install.\n        "
        path = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(path, "scripts")
        self.install_scripts(context, path)

    def post_setup(self, context):
        "\n        Hook for post-setup modification of the venv. Subclasses may install\n        additional packages or scripts here, add activation shell scripts, etc.\n\n        :param context: The information for the environment creation request\n                        being processed.\n        "
        pass

    def replace_variables(self, text, context):
        "\n        Replace variable placeholders in script text with context-specific\n        variables.\n\n        Return the text passed in , but with variables replaced.\n\n        :param text: The text in which to replace placeholder variables.\n        :param context: The information for the environment creation request\n                        being processed.\n        "
        text = text.replace("__VENV_DIR__", context.env_dir)
        text = text.replace("__VENV_NAME__", context.env_name)
        text = text.replace("__VENV_PROMPT__", context.prompt)
        text = text.replace("__VENV_BIN_NAME__", context.bin_name)
        text = text.replace("__VENV_PYTHON__", context.env_exe)
        return text

    def install_scripts(self, context, path):
        "\n        Install scripts into the created environment from a directory.\n\n        :param context: The information for the environment creation request\n                        being processed.\n        :param path:    Absolute pathname of a directory containing script.\n                        Scripts in the 'common' subdirectory of this directory,\n                        and those in the directory named for the platform\n                        being run on, are installed in the created environment.\n                        Placeholder variables are replaced with environment-\n                        specific values.\n        "
        binpath = context.bin_path
        plen = len(path)
        for (root, dirs, files) in os.walk(path):
            if root == path:
                for d in dirs[:]:
                    if d not in ("common", os.name):
                        dirs.remove(d)
                continue
            for f in files:
                if (
                    (os.name == "nt")
                    and f.startswith("python")
                    and f.endswith((".exe", ".pdb"))
                ):
                    continue
                srcfile = os.path.join(root, f)
                suffix = root[plen:].split(os.sep)[2:]
                if not suffix:
                    dstdir = binpath
                else:
                    dstdir = os.path.join(binpath, *suffix)
                if not os.path.exists(dstdir):
                    os.makedirs(dstdir)
                dstfile = os.path.join(dstdir, f)
                with open(srcfile, "rb") as f:
                    data = f.read()
                if not srcfile.endswith((".exe", ".pdb")):
                    try:
                        data = data.decode("utf-8")
                        data = self.replace_variables(data, context)
                        data = data.encode("utf-8")
                    except UnicodeError as e:
                        data = None
                        logger.warning(
                            "unable to copy script %r, may be binary: %s", srcfile, e
                        )
                if data is not None:
                    with open(dstfile, "wb") as f:
                        f.write(data)
                    shutil.copymode(srcfile, dstfile)

    def upgrade_dependencies(self, context):
        logger.debug(f"Upgrading {CORE_VENV_DEPS} packages in {context.bin_path}")
        if sys.platform == "win32":
            python_exe = os.path.join(context.bin_path, "python.exe")
        else:
            python_exe = os.path.join(context.bin_path, "python")
        cmd = [python_exe, "-m", "pip", "install", "--upgrade"]
        cmd.extend(CORE_VENV_DEPS)
        subprocess.check_call(cmd)


def create(
    env_dir,
    system_site_packages=False,
    clear=False,
    symlinks=False,
    with_pip=False,
    prompt=None,
    upgrade_deps=False,
):
    "Create a virtual environment in a directory."
    builder = EnvBuilder(
        system_site_packages=system_site_packages,
        clear=clear,
        symlinks=symlinks,
        with_pip=with_pip,
        prompt=prompt,
        upgrade_deps=upgrade_deps,
    )
    builder.create(env_dir)


def main(args=None):
    compatible = True
    if sys.version_info < (3, 3):
        compatible = False
    elif not hasattr(sys, "base_prefix"):
        compatible = False
    if not compatible:
        raise ValueError("This script is only for use with Python >= 3.3")
    else:
        import argparse

        parser = argparse.ArgumentParser(
            prog=__name__,
            description="Creates virtual Python environments in one or more target directories.",
            epilog="Once an environment has been created, you may wish to activate it, e.g. by sourcing an activate script in its bin directory.",
        )
        parser.add_argument(
            "dirs",
            metavar="ENV_DIR",
            nargs="+",
            help="A directory to create the environment in.",
        )
        parser.add_argument(
            "--system-site-packages",
            default=False,
            action="store_true",
            dest="system_site",
            help="Give the virtual environment access to the system site-packages dir.",
        )
        if os.name == "nt":
            use_symlinks = False
        else:
            use_symlinks = True
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--symlinks",
            default=use_symlinks,
            action="store_true",
            dest="symlinks",
            help="Try to use symlinks rather than copies, when symlinks are not the default for the platform.",
        )
        group.add_argument(
            "--copies",
            default=(not use_symlinks),
            action="store_false",
            dest="symlinks",
            help="Try to use copies rather than symlinks, even when symlinks are the default for the platform.",
        )
        parser.add_argument(
            "--clear",
            default=False,
            action="store_true",
            dest="clear",
            help="Delete the contents of the environment directory if it already exists, before environment creation.",
        )
        parser.add_argument(
            "--upgrade",
            default=False,
            action="store_true",
            dest="upgrade",
            help="Upgrade the environment directory to use this version of Python, assuming Python has been upgraded in-place.",
        )
        parser.add_argument(
            "--without-pip",
            dest="with_pip",
            default=True,
            action="store_false",
            help="Skips installing or upgrading pip in the virtual environment (pip is bootstrapped by default)",
        )
        parser.add_argument(
            "--prompt",
            help="Provides an alternative prompt prefix for this environment.",
        )
        parser.add_argument(
            "--upgrade-deps",
            default=False,
            action="store_true",
            dest="upgrade_deps",
            help="Upgrade core dependencies: {} to the latest version in PyPI".format(
                " ".join(CORE_VENV_DEPS)
            ),
        )
        options = parser.parse_args(args)
        if options.upgrade and options.clear:
            raise ValueError("you cannot supply --upgrade and --clear together.")
        builder = EnvBuilder(
            system_site_packages=options.system_site,
            clear=options.clear,
            symlinks=options.symlinks,
            upgrade=options.upgrade,
            with_pip=options.with_pip,
            prompt=options.prompt,
            upgrade_deps=options.upgrade_deps,
        )
        for d in options.dirs:
            builder.create(d)


if __name__ == "__main__":
    rc = 1
    try:
        main()
        rc = 0
    except Exception as e:
        print(("Error: %s" % e), file=sys.stderr)
    sys.exit(rc)
