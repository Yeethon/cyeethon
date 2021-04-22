"distutils.cmd\n\nProvides the Command class, the base class for the command classes\nin the distutils.command package.\n"
import sys, os, re
from distutils.errors import DistutilsOptionError
from distutils import util, dir_util, file_util, archive_util, dep_util
from distutils import log


class Command:
    'Abstract base class for defining command classes, the "worker bees"\n    of the Distutils.  A useful analogy for command classes is to think of\n    them as subroutines with local variables called "options".  The options\n    are "declared" in \'initialize_options()\' and "defined" (given their\n    final values, aka "finalized") in \'finalize_options()\', both of which\n    must be defined by every command class.  The distinction between the\n    two is necessary because option values might come from the outside\n    world (command line, config file, ...), and any options dependent on\n    other options must be computed *after* these outside influences have\n    been processed -- hence \'finalize_options()\'.  The "body" of the\n    subroutine, where it does all its work based on the values of its\n    options, is the \'run()\' method, which must also be implemented by every\n    command class.\n    '
    sub_commands = []

    def __init__(self, dist):
        "Create and initialize a new Command object.  Most importantly,\n        invokes the 'initialize_options()' method, which is the real\n        initializer and depends on the actual command being\n        instantiated.\n        "
        from distutils.dist import Distribution

        if not isinstance(dist, Distribution):
            raise TypeError("dist must be a Distribution instance")
        if self.__class__ is Command:
            raise RuntimeError("Command is an abstract class")
        self.distribution = dist
        self.initialize_options()
        self._dry_run = None
        self.verbose = dist.verbose
        self.force = None
        self.help = 0
        self.finalized = 0

    def __getattr__(self, attr):
        if attr == "dry_run":
            myval = getattr(self, ("_" + attr))
            if myval is None:
                return getattr(self.distribution, attr)
            else:
                return myval
        else:
            raise AttributeError(attr)

    def ensure_finalized(self):
        if not self.finalized:
            self.finalize_options()
        self.finalized = 1

    def initialize_options(self):
        "Set default values for all the options that this command\n        supports.  Note that these defaults may be overridden by other\n        commands, by the setup script, by config files, or by the\n        command-line.  Thus, this is not the place to code dependencies\n        between options; generally, 'initialize_options()' implementations\n        are just a bunch of \"self.foo = None\" assignments.\n\n        This method must be implemented by all command classes.\n        "
        raise RuntimeError(
            ("abstract method -- subclass %s must override" % self.__class__)
        )

    def finalize_options(self):
        "Set final values for all the options that this command supports.\n        This is always called as late as possible, ie.  after any option\n        assignments from the command-line or from other commands have been\n        done.  Thus, this is the place to code option dependencies: if\n        'foo' depends on 'bar', then it is safe to set 'foo' from 'bar' as\n        long as 'foo' still has the same value it was assigned in\n        'initialize_options()'.\n\n        This method must be implemented by all command classes.\n        "
        raise RuntimeError(
            ("abstract method -- subclass %s must override" % self.__class__)
        )

    def dump_options(self, header=None, indent=""):
        from distutils.fancy_getopt import longopt_xlate

        if header is None:
            header = "command options for '%s':" % self.get_command_name()
        self.announce((indent + header), level=log.INFO)
        indent = indent + "  "
        for (option, _, _) in self.user_options:
            option = option.translate(longopt_xlate)
            if option[(-1)] == "=":
                option = option[:(-1)]
            value = getattr(self, option)
            self.announce((indent + ("%s = %s" % (option, value))), level=log.INFO)

    def run(self):
        "A command's raison d'etre: carry out the action it exists to\n        perform, controlled by the options initialized in\n        'initialize_options()', customized by other commands, the setup\n        script, the command-line, and config files, and finalized in\n        'finalize_options()'.  All terminal output and filesystem\n        interaction should be done by 'run()'.\n\n        This method must be implemented by all command classes.\n        "
        raise RuntimeError(
            ("abstract method -- subclass %s must override" % self.__class__)
        )

    def announce(self, msg, level=1):
        "If the current verbosity level is of greater than or equal to\n        'level' print 'msg' to stdout.\n        "
        log.log(level, msg)

    def debug_print(self, msg):
        "Print 'msg' to stdout if the global DEBUG (taken from the\n        DISTUTILS_DEBUG environment variable) flag is true.\n        "
        from distutils.debug import DEBUG

        if DEBUG:
            print(msg)
            sys.stdout.flush()

    def _ensure_stringlike(self, option, what, default=None):
        val = getattr(self, option)
        if val is None:
            setattr(self, option, default)
            return default
        elif not isinstance(val, str):
            raise DistutilsOptionError(
                ("'%s' must be a %s (got `%s`)" % (option, what, val))
            )
        return val

    def ensure_string(self, option, default=None):
        "Ensure that 'option' is a string; if not defined, set it to\n        'default'.\n        "
        self._ensure_stringlike(option, "string", default)

    def ensure_string_list(self, option):
        'Ensure that \'option\' is a list of strings.  If \'option\' is\n        currently a string, we split it either on /,\\s*/ or /\\s+/, so\n        "foo bar baz", "foo,bar,baz", and "foo,   bar baz" all become\n        ["foo", "bar", "baz"].\n        '
        val = getattr(self, option)
        if val is None:
            return
        elif isinstance(val, str):
            setattr(self, option, re.split(",\\s*|\\s+", val))
        else:
            if isinstance(val, list):
                ok = all((isinstance(v, str) for v in val))
            else:
                ok = False
            if not ok:
                raise DistutilsOptionError(
                    ("'%s' must be a list of strings (got %r)" % (option, val))
                )

    def _ensure_tested_string(self, option, tester, what, error_fmt, default=None):
        val = self._ensure_stringlike(option, what, default)
        if (val is not None) and (not tester(val)):
            raise DistutilsOptionError(
                (("error in '%s' option: " + error_fmt) % (option, val))
            )

    def ensure_filename(self, option):
        "Ensure that 'option' is the name of an existing file."
        self._ensure_tested_string(
            option, os.path.isfile, "filename", "'%s' does not exist or is not a file"
        )

    def ensure_dirname(self, option):
        self._ensure_tested_string(
            option,
            os.path.isdir,
            "directory name",
            "'%s' does not exist or is not a directory",
        )

    def get_command_name(self):
        if hasattr(self, "command_name"):
            return self.command_name
        else:
            return self.__class__.__name__

    def set_undefined_options(self, src_cmd, *option_pairs):
        "Set the values of any \"undefined\" options from corresponding\n        option values in some other command object.  \"Undefined\" here means\n        \"is None\", which is the convention used to indicate that an option\n        has not been changed between 'initialize_options()' and\n        'finalize_options()'.  Usually called from 'finalize_options()' for\n        options that depend on some other command rather than another\n        option of the same command.  'src_cmd' is the other command from\n        which option values will be taken (a command object will be created\n        for it if necessary); the remaining arguments are\n        '(src_option,dst_option)' tuples which mean \"take the value of\n        'src_option' in the 'src_cmd' command object, and copy it to\n        'dst_option' in the current command object\".\n        "
        src_cmd_obj = self.distribution.get_command_obj(src_cmd)
        src_cmd_obj.ensure_finalized()
        for (src_option, dst_option) in option_pairs:
            if getattr(self, dst_option) is None:
                setattr(self, dst_option, getattr(src_cmd_obj, src_option))

    def get_finalized_command(self, command, create=1):
        "Wrapper around Distribution's 'get_command_obj()' method: find\n        (create if necessary and 'create' is true) the command object for\n        'command', call its 'ensure_finalized()' method, and return the\n        finalized command object.\n        "
        cmd_obj = self.distribution.get_command_obj(command, create)
        cmd_obj.ensure_finalized()
        return cmd_obj

    def reinitialize_command(self, command, reinit_subcommands=0):
        return self.distribution.reinitialize_command(command, reinit_subcommands)

    def run_command(self, command):
        "Run some other command: uses the 'run_command()' method of\n        Distribution, which creates and finalizes the command object if\n        necessary and then invokes its 'run()' method.\n        "
        self.distribution.run_command(command)

    def get_sub_commands(self):
        "Determine the sub-commands that are relevant in the current\n        distribution (ie., that need to be run).  This is based on the\n        'sub_commands' class attribute: each tuple in that list may include\n        a method that we call to determine if the subcommand needs to be\n        run for the current distribution.  Return a list of command names.\n        "
        commands = []
        for (cmd_name, method) in self.sub_commands:
            if (method is None) or method(self):
                commands.append(cmd_name)
        return commands

    def warn(self, msg):
        log.warn("warning: %s: %s\n", self.get_command_name(), msg)

    def execute(self, func, args, msg=None, level=1):
        util.execute(func, args, msg, dry_run=self.dry_run)

    def mkpath(self, name, mode=511):
        dir_util.mkpath(name, mode, dry_run=self.dry_run)

    def copy_file(
        self, infile, outfile, preserve_mode=1, preserve_times=1, link=None, level=1
    ):
        "Copy a file respecting verbose, dry-run and force flags.  (The\n        former two default to whatever is in the Distribution object, and\n        the latter defaults to false for commands that don't define it.)"
        return file_util.copy_file(
            infile,
            outfile,
            preserve_mode,
            preserve_times,
            (not self.force),
            link,
            dry_run=self.dry_run,
        )

    def copy_tree(
        self,
        infile,
        outfile,
        preserve_mode=1,
        preserve_times=1,
        preserve_symlinks=0,
        level=1,
    ):
        "Copy an entire directory tree respecting verbose, dry-run,\n        and force flags.\n        "
        return dir_util.copy_tree(
            infile,
            outfile,
            preserve_mode,
            preserve_times,
            preserve_symlinks,
            (not self.force),
            dry_run=self.dry_run,
        )

    def move_file(self, src, dst, level=1):
        "Move a file respecting dry-run flag."
        return file_util.move_file(src, dst, dry_run=self.dry_run)

    def spawn(self, cmd, search_path=1, level=1):
        "Spawn an external command respecting dry-run flag."
        from distutils.spawn import spawn

        spawn(cmd, search_path, dry_run=self.dry_run)

    def make_archive(
        self, base_name, format, root_dir=None, base_dir=None, owner=None, group=None
    ):
        return archive_util.make_archive(
            base_name,
            format,
            root_dir,
            base_dir,
            dry_run=self.dry_run,
            owner=owner,
            group=group,
        )

    def make_file(
        self, infiles, outfile, func, args, exec_msg=None, skip_msg=None, level=1
    ):
        "Special case of 'execute()' for operations that process one or\n        more input files and generate one output file.  Works just like\n        'execute()', except the operation is skipped and a different\n        message printed if 'outfile' already exists and is newer than all\n        files listed in 'infiles'.  If the command defined 'self.force',\n        and it is true, then the command is unconditionally run -- does no\n        timestamp checks.\n        "
        if skip_msg is None:
            skip_msg = "skipping %s (inputs unchanged)" % outfile
        if isinstance(infiles, str):
            infiles = (infiles,)
        elif not isinstance(infiles, (list, tuple)):
            raise TypeError("'infiles' must be a string, or a list or tuple of strings")
        if exec_msg is None:
            exec_msg = "generating %s from %s" % (outfile, ", ".join(infiles))
        if self.force or dep_util.newer_group(infiles, outfile):
            self.execute(func, args, exec_msg, level)
        else:
            log.debug(skip_msg)
