"distutils.command.sdist\n\nImplements the Distutils 'sdist' command (create a source distribution)."
import os
import sys
from glob import glob
from warnings import warn
from distutils.core import Command
from distutils import dir_util
from distutils import file_util
from distutils import archive_util
from distutils.text_file import TextFile
from distutils.filelist import FileList
from distutils import log
from distutils.util import convert_path
from distutils.errors import DistutilsTemplateError, DistutilsOptionError


def show_formats():
    "Print all possible values for the 'formats' option (used by\n    the \"--help-formats\" command-line option).\n    "
    from distutils.fancy_getopt import FancyGetopt
    from distutils.archive_util import ARCHIVE_FORMATS

    formats = []
    for format in ARCHIVE_FORMATS.keys():
        formats.append((("formats=" + format), None, ARCHIVE_FORMATS[format][2]))
    formats.sort()
    FancyGetopt(formats).print_help("List of available source distribution formats:")


class sdist(Command):
    description = "create a source distribution (tarball, zip file, etc.)"

    def checking_metadata(self):
        "Callable used for the check sub-command.\n\n        Placed here so user_options can view it"
        return self.metadata_check

    user_options = [
        ("template=", "t", "name of manifest template file [default: MANIFEST.in]"),
        ("manifest=", "m", "name of manifest file [default: MANIFEST]"),
        (
            "use-defaults",
            None,
            "include the default file set in the manifest [default; disable with --no-defaults]",
        ),
        ("no-defaults", None, "don't include the default file set"),
        (
            "prune",
            None,
            "specifically exclude files/directories that should not be distributed (build tree, RCS/CVS dirs, etc.) [default; disable with --no-prune]",
        ),
        ("no-prune", None, "don't automatically exclude anything"),
        (
            "manifest-only",
            "o",
            "just regenerate the manifest and then stop (implies --force-manifest)",
        ),
        (
            "force-manifest",
            "f",
            "forcibly regenerate the manifest and carry on as usual. Deprecated: now the manifest is always regenerated.",
        ),
        ("formats=", None, "formats for source distribution (comma-separated list)"),
        (
            "keep-temp",
            "k",
            ("keep the distribution tree around after creating " + "archive file(s)"),
        ),
        (
            "dist-dir=",
            "d",
            "directory to put the source distribution archive(s) in [default: dist]",
        ),
        (
            "metadata-check",
            None,
            "Ensure that all required elements of meta-data are supplied. Warn if any missing. [default]",
        ),
        (
            "owner=",
            "u",
            "Owner name used when creating a tar file [default: current user]",
        ),
        (
            "group=",
            "g",
            "Group name used when creating a tar file [default: current group]",
        ),
    ]
    boolean_options = [
        "use-defaults",
        "prune",
        "manifest-only",
        "force-manifest",
        "keep-temp",
        "metadata-check",
    ]
    help_options = [
        ("help-formats", None, "list available distribution formats", show_formats)
    ]
    negative_opt = {"no-defaults": "use-defaults", "no-prune": "prune"}
    sub_commands = [("check", checking_metadata)]
    READMES = ("README", "README.txt", "README.rst")

    def initialize_options(self):
        self.template = None
        self.manifest = None
        self.use_defaults = 1
        self.prune = 1
        self.manifest_only = 0
        self.force_manifest = 0
        self.formats = ["gztar"]
        self.keep_temp = 0
        self.dist_dir = None
        self.archive_files = None
        self.metadata_check = 1
        self.owner = None
        self.group = None

    def finalize_options(self):
        if self.manifest is None:
            self.manifest = "MANIFEST"
        if self.template is None:
            self.template = "MANIFEST.in"
        self.ensure_string_list("formats")
        bad_format = archive_util.check_archive_formats(self.formats)
        if bad_format:
            raise DistutilsOptionError(("unknown archive format '%s'" % bad_format))
        if self.dist_dir is None:
            self.dist_dir = "dist"

    def run(self):
        self.filelist = FileList()
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)
        self.get_file_list()
        if self.manifest_only:
            return
        self.make_distribution()

    def check_metadata(self):
        "Deprecated API."
        warn(
            "distutils.command.sdist.check_metadata is deprecated,               use the check command instead",
            PendingDeprecationWarning,
        )
        check = self.distribution.get_command_obj("check")
        check.ensure_finalized()
        check.run()

    def get_file_list(self):
        "Figure out the list of files to include in the source\n        distribution, and put it in 'self.filelist'.  This might involve\n        reading the manifest template (and writing the manifest), or just\n        reading the manifest, or just using the default file set -- it all\n        depends on the user's options.\n        "
        template_exists = os.path.isfile(self.template)
        if (not template_exists) and self._manifest_is_not_generated():
            self.read_manifest()
            self.filelist.sort()
            self.filelist.remove_duplicates()
            return
        if not template_exists:
            self.warn(
                (
                    (
                        "manifest template '%s' does not exist "
                        + "(using default file list)"
                    )
                    % self.template
                )
            )
        self.filelist.findall()
        if self.use_defaults:
            self.add_defaults()
        if template_exists:
            self.read_template()
        if self.prune:
            self.prune_file_list()
        self.filelist.sort()
        self.filelist.remove_duplicates()
        self.write_manifest()

    def add_defaults(self):
        "Add all the default files to self.filelist:\n          - README or README.txt\n          - setup.py\n          - test/test*.py\n          - all pure Python modules mentioned in setup script\n          - all files pointed by package_data (build_py)\n          - all files defined in data_files.\n          - all files defined as scripts.\n          - all C sources listed as part of extensions or C libraries\n            in the setup script (doesn't catch C headers!)\n        Warns if (README or README.txt) or setup.py are missing; everything\n        else is optional.\n        "
        self._add_defaults_standards()
        self._add_defaults_optional()
        self._add_defaults_python()
        self._add_defaults_data_files()
        self._add_defaults_ext()
        self._add_defaults_c_libs()
        self._add_defaults_scripts()

    @staticmethod
    def _cs_path_exists(fspath):
        "\n        Case-sensitive path existence check\n\n        >>> sdist._cs_path_exists(__file__)\n        True\n        >>> sdist._cs_path_exists(__file__.upper())\n        False\n        "
        if not os.path.exists(fspath):
            return False
        abspath = os.path.abspath(fspath)
        (directory, filename) = os.path.split(abspath)
        return filename in os.listdir(directory)

    def _add_defaults_standards(self):
        standards = [self.READMES, self.distribution.script_name]
        for fn in standards:
            if isinstance(fn, tuple):
                alts = fn
                got_it = False
                for fn in alts:
                    if self._cs_path_exists(fn):
                        got_it = True
                        self.filelist.append(fn)
                        break
                if not got_it:
                    self.warn(
                        (
                            "standard file not found: should have one of "
                            + ", ".join(alts)
                        )
                    )
            elif self._cs_path_exists(fn):
                self.filelist.append(fn)
            else:
                self.warn(("standard file '%s' not found" % fn))

    def _add_defaults_optional(self):
        optional = ["test/test*.py", "setup.cfg"]
        for pattern in optional:
            files = filter(os.path.isfile, glob(pattern))
            self.filelist.extend(files)

    def _add_defaults_python(self):
        build_py = self.get_finalized_command("build_py")
        if self.distribution.has_pure_modules():
            self.filelist.extend(build_py.get_source_files())
        for (pkg, src_dir, build_dir, filenames) in build_py.data_files:
            for filename in filenames:
                self.filelist.append(os.path.join(src_dir, filename))

    def _add_defaults_data_files(self):
        if self.distribution.has_data_files():
            for item in self.distribution.data_files:
                if isinstance(item, str):
                    item = convert_path(item)
                    if os.path.isfile(item):
                        self.filelist.append(item)
                else:
                    (dirname, filenames) = item
                    for f in filenames:
                        f = convert_path(f)
                        if os.path.isfile(f):
                            self.filelist.append(f)

    def _add_defaults_ext(self):
        if self.distribution.has_ext_modules():
            build_ext = self.get_finalized_command("build_ext")
            self.filelist.extend(build_ext.get_source_files())

    def _add_defaults_c_libs(self):
        if self.distribution.has_c_libraries():
            build_clib = self.get_finalized_command("build_clib")
            self.filelist.extend(build_clib.get_source_files())

    def _add_defaults_scripts(self):
        if self.distribution.has_scripts():
            build_scripts = self.get_finalized_command("build_scripts")
            self.filelist.extend(build_scripts.get_source_files())

    def read_template(self):
        "Read and parse manifest template file named by self.template.\n\n        (usually \"MANIFEST.in\") The parsing and processing is done by\n        'self.filelist', which updates itself accordingly.\n        "
        log.info("reading manifest template '%s'", self.template)
        template = TextFile(
            self.template,
            strip_comments=1,
            skip_blanks=1,
            join_lines=1,
            lstrip_ws=1,
            rstrip_ws=1,
            collapse_join=1,
        )
        try:
            while True:
                line = template.readline()
                if line is None:
                    break
                try:
                    self.filelist.process_template_line(line)
                except (DistutilsTemplateError, ValueError) as msg:
                    self.warn(
                        (
                            "%s, line %d: %s"
                            % (template.filename, template.current_line, msg)
                        )
                    )
        finally:
            template.close()

    def prune_file_list(self):
        'Prune off branches that might slip into the file list as created\n        by \'read_template()\', but really don\'t belong there:\n          * the build tree (typically "build")\n          * the release tree itself (only an issue if we ran "sdist"\n            previously with --keep-temp, or it aborted)\n          * any RCS, CVS, .svn, .hg, .git, .bzr, _darcs directories\n        '
        build = self.get_finalized_command("build")
        base_dir = self.distribution.get_fullname()
        self.filelist.exclude_pattern(None, prefix=build.build_base)
        self.filelist.exclude_pattern(None, prefix=base_dir)
        if sys.platform == "win32":
            seps = "/|\\\\"
        else:
            seps = "/"
        vcs_dirs = ["RCS", "CVS", "\\.svn", "\\.hg", "\\.git", "\\.bzr", "_darcs"]
        vcs_ptrn = "(^|%s)(%s)(%s).*" % (seps, "|".join(vcs_dirs), seps)
        self.filelist.exclude_pattern(vcs_ptrn, is_regex=1)

    def write_manifest(self):
        "Write the file list in 'self.filelist' (presumably as filled in\n        by 'add_defaults()' and 'read_template()') to the manifest file\n        named by 'self.manifest'.\n        "
        if self._manifest_is_not_generated():
            log.info(
                (
                    "not writing to manually maintained manifest file '%s'"
                    % self.manifest
                )
            )
            return
        content = self.filelist.files[:]
        content.insert(0, "# file GENERATED by distutils, do NOT edit")
        self.execute(
            file_util.write_file,
            (self.manifest, content),
            ("writing manifest file '%s'" % self.manifest),
        )

    def _manifest_is_not_generated(self):
        if not os.path.isfile(self.manifest):
            return False
        fp = open(self.manifest)
        try:
            first_line = fp.readline()
        finally:
            fp.close()
        return first_line != "# file GENERATED by distutils, do NOT edit\n"

    def read_manifest(self):
        "Read the manifest file (named by 'self.manifest') and use it to\n        fill in 'self.filelist', the list of files to include in the source\n        distribution.\n        "
        log.info("reading manifest file '%s'", self.manifest)
        with open(self.manifest) as manifest:
            for line in manifest:
                line = line.strip()
                if line.startswith("#") or (not line):
                    continue
                self.filelist.append(line)

    def make_release_tree(self, base_dir, files):
        "Create the directory tree that will become the source\n        distribution archive.  All directories implied by the filenames in\n        'files' are created under 'base_dir', and then we hard link or copy\n        (if hard linking is unavailable) those files into place.\n        Essentially, this duplicates the developer's source tree, but in a\n        directory named after the distribution, containing only the files\n        to be distributed.\n        "
        self.mkpath(base_dir)
        dir_util.create_tree(base_dir, files, dry_run=self.dry_run)
        if hasattr(os, "link"):
            link = "hard"
            msg = "making hard links in %s..." % base_dir
        else:
            link = None
            msg = "copying files to %s..." % base_dir
        if not files:
            log.warn("no files to distribute -- empty manifest?")
        else:
            log.info(msg)
        for file in files:
            if not os.path.isfile(file):
                log.warn("'%s' not a regular file -- skipping", file)
            else:
                dest = os.path.join(base_dir, file)
                self.copy_file(file, dest, link=link)
        self.distribution.metadata.write_pkg_info(base_dir)

    def make_distribution(self):
        "Create the source distribution(s).  First, we create the release\n        tree with 'make_release_tree()'; then, we create all required\n        archive files (according to 'self.formats') from the release tree.\n        Finally, we clean up by blowing away the release tree (unless\n        'self.keep_temp' is true).  The list of archive files created is\n        stored so it can be retrieved later by 'get_archive_files()'.\n        "
        base_dir = self.distribution.get_fullname()
        base_name = os.path.join(self.dist_dir, base_dir)
        self.make_release_tree(base_dir, self.filelist.files)
        archive_files = []
        if "tar" in self.formats:
            self.formats.append(self.formats.pop(self.formats.index("tar")))
        for fmt in self.formats:
            file = self.make_archive(
                base_name, fmt, base_dir=base_dir, owner=self.owner, group=self.group
            )
            archive_files.append(file)
            self.distribution.dist_files.append(("sdist", "", file))
        self.archive_files = archive_files
        if not self.keep_temp:
            dir_util.remove_tree(base_dir, dry_run=self.dry_run)

    def get_archive_files(self):
        "Return the list of archive files created when the command\n        was run, or None if the command hasn't run yet.\n        "
        return self.archive_files
