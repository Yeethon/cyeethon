import collections
import os
import os.path
import subprocess
import sys
import sysconfig
import tempfile
from importlib import resources

__all__ = ["version", "bootstrap"]
_PACKAGE_NAMES = ("setuptools", "pip")
_SETUPTOOLS_VERSION = "52.0.0"
_PIP_VERSION = "21.0.1"
_PROJECTS = [("setuptools", _SETUPTOOLS_VERSION, "py3"), ("pip", _PIP_VERSION, "py3")]
_Package = collections.namedtuple("Package", ("version", "wheel_name", "wheel_path"))
_WHEEL_PKG_DIR = sysconfig.get_config_var("WHEEL_PKG_DIR")


def _find_packages(path):
    packages = {}
    try:
        filenames = os.listdir(path)
    except OSError:
        filenames = ()
    filenames = sorted(filenames)
    for filename in filenames:
        if not filename.endswith(".whl"):
            continue
        for name in _PACKAGE_NAMES:
            prefix = name + "-"
            if filename.startswith(prefix):
                break
        else:
            continue
        version = filename.removeprefix(prefix).partition("-")[0]
        wheel_path = os.path.join(path, filename)
        packages[name] = _Package(version, None, wheel_path)
    return packages


def _get_packages():
    global _PACKAGES, _WHEEL_PKG_DIR
    if _PACKAGES is not None:
        return _PACKAGES
    packages = {}
    for (name, version, py_tag) in _PROJECTS:
        wheel_name = f"{name}-{version}-{py_tag}-none-any.whl"
        packages[name] = _Package(version, wheel_name, None)
    if _WHEEL_PKG_DIR:
        dir_packages = _find_packages(_WHEEL_PKG_DIR)
        if all(((name in dir_packages) for name in _PACKAGE_NAMES)):
            packages = dir_packages
    _PACKAGES = packages
    return packages


_PACKAGES = None


def _run_pip(args, additional_paths=None):
    code = f"""
import runpy
import sys
sys.path = {(additional_paths or [])} + sys.path
sys.argv[1:] = {args}
runpy.run_module("pip", run_name="__main__", alter_sys=True)
"""
    return subprocess.run([sys.executable, "-c", code], check=True).returncode


def version():
    "\n    Returns a string specifying the bundled version of pip.\n    "
    return _get_packages()["pip"].version


def _disable_pip_configuration_settings():
    keys_to_remove = [k for k in os.environ if k.startswith("PIP_")]
    for k in keys_to_remove:
        del os.environ[k]
    os.environ["PIP_CONFIG_FILE"] = os.devnull


def bootstrap(
    *,
    root=None,
    upgrade=False,
    user=False,
    altinstall=False,
    default_pip=False,
    verbosity=0,
):
    "\n    Bootstrap pip into the current Python installation (or the given root\n    directory).\n\n    Note that calling this function will alter both sys.path and os.environ.\n    "
    _bootstrap(
        root=root,
        upgrade=upgrade,
        user=user,
        altinstall=altinstall,
        default_pip=default_pip,
        verbosity=verbosity,
    )


def _bootstrap(
    *,
    root=None,
    upgrade=False,
    user=False,
    altinstall=False,
    default_pip=False,
    verbosity=0,
):
    "\n    Bootstrap pip into the current Python installation (or the given root\n    directory). Returns pip command status code.\n\n    Note that calling this function will alter both sys.path and os.environ.\n    "
    if altinstall and default_pip:
        raise ValueError("Cannot use altinstall and default_pip together")
    sys.audit("ensurepip.bootstrap", root)
    _disable_pip_configuration_settings()
    if altinstall:
        os.environ["ENSUREPIP_OPTIONS"] = "altinstall"
    elif not default_pip:
        os.environ["ENSUREPIP_OPTIONS"] = "install"
    with tempfile.TemporaryDirectory() as tmpdir:
        additional_paths = []
        for (name, package) in _get_packages().items():
            if package.wheel_name:
                from ensurepip import _bundled

                wheel_name = package.wheel_name
                whl = resources.read_binary(_bundled, wheel_name)
            else:
                with open(package.wheel_path, "rb") as fp:
                    whl = fp.read()
                wheel_name = os.path.basename(package.wheel_path)
            filename = os.path.join(tmpdir, wheel_name)
            with open(filename, "wb") as fp:
                fp.write(whl)
            additional_paths.append(filename)
        args = ["install", "--no-cache-dir", "--no-index", "--find-links", tmpdir]
        if root:
            args += ["--root", root]
        if upgrade:
            args += ["--upgrade"]
        if user:
            args += ["--user"]
        if verbosity:
            args += [("-" + ("v" * verbosity))]
        return _run_pip([*args, *_PACKAGE_NAMES], additional_paths)


def _uninstall_helper(*, verbosity=0):
    "Helper to support a clean default uninstall process on Windows\n\n    Note that calling this function may alter os.environ.\n    "
    try:
        import pip
    except ImportError:
        return
    available_version = version()
    if pip.__version__ != available_version:
        print(
            f"ensurepip will only uninstall a matching version ({pip.__version__!r} installed, {available_version!r} available)",
            file=sys.stderr,
        )
        return
    _disable_pip_configuration_settings()
    args = ["uninstall", "-y", "--disable-pip-version-check"]
    if verbosity:
        args += [("-" + ("v" * verbosity))]
    return _run_pip([*args, *reversed(_PACKAGE_NAMES)])


def _main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(prog="python -m ensurepip")
    parser.add_argument(
        "--version",
        action="version",
        version="pip {}".format(version()),
        help="Show the version of pip that is bundled with this Python.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbosity",
        help="Give more output. Option is additive, and can be used up to 3 times.",
    )
    parser.add_argument(
        "-U",
        "--upgrade",
        action="store_true",
        default=False,
        help="Upgrade pip and dependencies, even if already installed.",
    )
    parser.add_argument(
        "--user",
        action="store_true",
        default=False,
        help="Install using the user scheme.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Install everything relative to this alternate root directory.",
    )
    parser.add_argument(
        "--altinstall",
        action="store_true",
        default=False,
        help="Make an alternate install, installing only the X.Y versioned scripts (Default: pipX, pipX.Y, easy_install-X.Y).",
    )
    parser.add_argument(
        "--default-pip",
        action="store_true",
        default=False,
        help="Make a default pip install, installing the unqualified pip and easy_install in addition to the versioned scripts.",
    )
    args = parser.parse_args(argv)
    return _bootstrap(
        root=args.root,
        upgrade=args.upgrade,
        user=args.user,
        verbosity=args.verbosity,
        altinstall=args.altinstall,
        default_pip=args.default_pip,
    )
