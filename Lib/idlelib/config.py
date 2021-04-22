
"idlelib.config -- Manage IDLE configuration information.\n\nThe comments at the beginning of config-main.def describe the\nconfiguration files and the design implemented to update user\nconfiguration information.  In particular, user configuration choices\nwhich duplicate the defaults will be removed from the user's\nconfiguration files, and if a user file becomes empty, it will be\ndeleted.\n\nThe configuration database maps options to values.  Conceptually, the\ndatabase keys are tuples (config-type, section, item).  As implemented,\nthere are  separate dicts for default and user values.  Each has\nconfig-type keys 'main', 'extensions', 'highlight', and 'keys'.  The\nvalue for each key is a ConfigParser instance that maps section and item\nto values.  For 'main' and 'extensions', user values override\ndefault values.  For 'highlight' and 'keys', user sections augment the\ndefault sections (and must, therefore, have distinct names).\n\nThroughout this module there is an emphasis on returning useable defaults\nwhen a problem occurs in returning a requested configuration value back to\nidle. This is to allow IDLE to continue to function in spite of errors in\nthe retrieval of config information. When a default is returned instead of\na requested config value, a message is printed to stderr to aid in\nconfiguration problem notification and resolution.\n"
from configparser import ConfigParser
import os
import sys
from tkinter.font import Font
import idlelib

class InvalidConfigType(Exception):
    pass

class InvalidConfigSet(Exception):
    pass

class InvalidTheme(Exception):
    pass

class IdleConfParser(ConfigParser):
    '\n    A ConfigParser specialised for idle configuration file handling\n    '

    def __init__(self, cfgFile, cfgDefaults=None):
        '\n        cfgFile - string, fully specified configuration file name\n        '
        self.file = cfgFile
        ConfigParser.__init__(self, defaults=cfgDefaults, strict=False)

    def Get(self, section, option, type=None, default=None, raw=False):
        '\n        Get an option value for given section/option or return default.\n        If type is specified, return as type.\n        '
        if (not self.has_option(section, option)):
            return default
        if (type == 'bool'):
            return self.getboolean(section, option)
        elif (type == 'int'):
            return self.getint(section, option)
        else:
            return self.get(section, option, raw=raw)

    def GetOptionList(self, section):
        'Return a list of options for given section, else [].'
        if self.has_section(section):
            return self.options(section)
        else:
            return []

    def Load(self):
        'Load the configuration file from disk.'
        if self.file:
            self.read(self.file)

class IdleUserConfParser(IdleConfParser):
    '\n    IdleConfigParser specialised for user configuration handling.\n    '

    def SetOption(self, section, option, value):
        'Return True if option is added or changed to value, else False.\n\n        Add section if required.  False means option already had value.\n        '
        if self.has_option(section, option):
            if (self.get(section, option) == value):
                return False
            else:
                self.set(section, option, value)
                return True
        else:
            if (not self.has_section(section)):
                self.add_section(section)
            self.set(section, option, value)
            return True

    def RemoveOption(self, section, option):
        'Return True if option is removed from section, else False.\n\n        False if either section does not exist or did not have option.\n        '
        if self.has_section(section):
            return self.remove_option(section, option)
        return False

    def AddSection(self, section):
        "If section doesn't exist, add it."
        if (not self.has_section(section)):
            self.add_section(section)

    def RemoveEmptySections(self):
        'Remove any sections that have no options.'
        for section in self.sections():
            if (not self.GetOptionList(section)):
                self.remove_section(section)

    def IsEmpty(self):
        'Return True if no sections after removing empty sections.'
        self.RemoveEmptySections()
        return (not self.sections())

    def Save(self):
        'Update user configuration file.\n\n        If self not empty after removing empty sections, write the file\n        to disk. Otherwise, remove the file from disk if it exists.\n        '
        fname = self.file
        if (fname and (fname[0] != '#')):
            if (not self.IsEmpty()):
                try:
                    cfgFile = open(fname, 'w')
                except OSError:
                    os.unlink(fname)
                    cfgFile = open(fname, 'w')
                with cfgFile:
                    self.write(cfgFile)
            elif os.path.exists(self.file):
                os.remove(self.file)

class IdleConf():
    'Hold config parsers for all idle config files in singleton instance.\n\n    Default config files, self.defaultCfg --\n        for config_type in self.config_types:\n            (idle install dir)/config-{config-type}.def\n\n    User config files, self.userCfg --\n        for config_type in self.config_types:\n        (user home dir)/.idlerc/config-{config-type}.cfg\n    '

    def __init__(self, _utest=False):
        self.config_types = ('main', 'highlight', 'keys', 'extensions')
        self.defaultCfg = {}
        self.userCfg = {}
        self.cfg = {}
        if (not _utest):
            self.CreateConfigHandlers()
            self.LoadCfgFiles()

    def CreateConfigHandlers(self):
        'Populate default and user config parser dictionaries.'
        idledir = os.path.dirname(__file__)
        self.userdir = userdir = ('' if idlelib.testing else self.GetUserCfgDir())
        for cfg_type in self.config_types:
            self.defaultCfg[cfg_type] = IdleConfParser(os.path.join(idledir, f'config-{cfg_type}.def'))
            self.userCfg[cfg_type] = IdleUserConfParser(os.path.join((userdir or '#'), f'config-{cfg_type}.cfg'))

    def GetUserCfgDir(self):
        'Return a filesystem directory for storing user config files.\n\n        Creates it if required.\n        '
        cfgDir = '.idlerc'
        userDir = os.path.expanduser('~')
        if (userDir != '~'):
            if (not os.path.exists(userDir)):
                if (not idlelib.testing):
                    warn = (('\n Warning: os.path.expanduser("~") points to\n ' + userDir) + ',\n but the path does not exist.')
                    try:
                        print(warn, file=sys.stderr)
                    except OSError:
                        pass
                userDir = '~'
        if (userDir == '~'):
            userDir = os.getcwd()
        userDir = os.path.join(userDir, cfgDir)
        if (not os.path.exists(userDir)):
            try:
                os.mkdir(userDir)
            except OSError:
                if (not idlelib.testing):
                    warn = (('\n Warning: unable to create user config directory\n' + userDir) + '\n Check path and permissions.\n Exiting!\n')
                    try:
                        print(warn, file=sys.stderr)
                    except OSError:
                        pass
                raise SystemExit
        return userDir

    def GetOption(self, configType, section, option, default=None, type=None, warn_on_default=True, raw=False):
        'Return a value for configType section option, or default.\n\n        If type is not None, return a value of that type.  Also pass raw\n        to the config parser.  First try to return a valid value\n        (including type) from a user configuration. If that fails, try\n        the default configuration. If that fails, return default, with a\n        default of None.\n\n        Warn if either user or default configurations have an invalid value.\n        Warn if default is returned and warn_on_default is True.\n        '
        try:
            if self.userCfg[configType].has_option(section, option):
                return self.userCfg[configType].Get(section, option, type=type, raw=raw)
        except ValueError:
            warning = ('\n Warning: config.py - IdleConf.GetOption -\n invalid %r value for configuration option %r\n from section %r: %r' % (type, option, section, self.userCfg[configType].Get(section, option, raw=raw)))
            _warn(warning, configType, section, option)
        try:
            if self.defaultCfg[configType].has_option(section, option):
                return self.defaultCfg[configType].Get(section, option, type=type, raw=raw)
        except ValueError:
            pass
        if warn_on_default:
            warning = ('\n Warning: config.py - IdleConf.GetOption -\n problem retrieving configuration option %r\n from section %r.\n returning default value: %r' % (option, section, default))
            _warn(warning, configType, section, option)
        return default

    def SetOption(self, configType, section, option, value):
        'Set section option to value in user config file.'
        self.userCfg[configType].SetOption(section, option, value)

    def GetSectionList(self, configSet, configType):
        "Return sections for configSet configType configuration.\n\n        configSet must be either 'user' or 'default'\n        configType must be in self.config_types.\n        "
        if (not (configType in self.config_types)):
            raise InvalidConfigType('Invalid configType specified')
        if (configSet == 'user'):
            cfgParser = self.userCfg[configType]
        elif (configSet == 'default'):
            cfgParser = self.defaultCfg[configType]
        else:
            raise InvalidConfigSet('Invalid configSet specified')
        return cfgParser.sections()

    def GetHighlight(self, theme, element):
        "Return dict of theme element highlight colors.\n\n        The keys are 'foreground' and 'background'.  The values are\n        tkinter color strings for configuring backgrounds and tags.\n        "
        cfg = ('default' if self.defaultCfg['highlight'].has_section(theme) else 'user')
        theme_dict = self.GetThemeDict(cfg, theme)
        fore = theme_dict[(element + '-foreground')]
        if (element == 'cursor'):
            element = 'normal'
        back = theme_dict[(element + '-background')]
        return {'foreground': fore, 'background': back}

    def GetThemeDict(self, type, themeName):
        "Return {option:value} dict for elements in themeName.\n\n        type - string, 'default' or 'user' theme type\n        themeName - string, theme name\n        Values are loaded over ultimate fallback defaults to guarantee\n        that all theme elements are present in a newly created theme.\n        "
        if (type == 'user'):
            cfgParser = self.userCfg['highlight']
        elif (type == 'default'):
            cfgParser = self.defaultCfg['highlight']
        else:
            raise InvalidTheme('Invalid theme type specified')
        theme = {'normal-foreground': '#000000', 'normal-background': '#ffffff', 'keyword-foreground': '#000000', 'keyword-background': '#ffffff', 'builtin-foreground': '#000000', 'builtin-background': '#ffffff', 'comment-foreground': '#000000', 'comment-background': '#ffffff', 'string-foreground': '#000000', 'string-background': '#ffffff', 'definition-foreground': '#000000', 'definition-background': '#ffffff', 'hilite-foreground': '#000000', 'hilite-background': 'gray', 'break-foreground': '#ffffff', 'break-background': '#000000', 'hit-foreground': '#ffffff', 'hit-background': '#000000', 'error-foreground': '#ffffff', 'error-background': '#000000', 'context-foreground': '#000000', 'context-background': '#ffffff', 'linenumber-foreground': '#000000', 'linenumber-background': '#ffffff', 'cursor-foreground': '#000000', 'stdout-foreground': '#000000', 'stdout-background': '#ffffff', 'stderr-foreground': '#000000', 'stderr-background': '#ffffff', 'console-foreground': '#000000', 'console-background': '#ffffff'}
        for element in theme:
            if (not (cfgParser.has_option(themeName, element) or element.startswith(('context-', 'linenumber-')))):
                warning = ('\n Warning: config.IdleConf.GetThemeDict -\n problem retrieving theme element %r\n from theme %r.\n returning default color: %r' % (element, themeName, theme[element]))
                _warn(warning, 'highlight', themeName, element)
            theme[element] = cfgParser.Get(themeName, element, default=theme[element])
        return theme

    def CurrentTheme(self):
        'Return the name of the currently active text color theme.'
        return self.current_colors_and_keys('Theme')

    def CurrentKeys(self):
        'Return the name of the currently active key set.'
        return self.current_colors_and_keys('Keys')

    def current_colors_and_keys(self, section):
        "Return the currently active name for Theme or Keys section.\n\n        idlelib.config-main.def ('default') includes these sections\n\n        [Theme]\n        default= 1\n        name= IDLE Classic\n        name2=\n\n        [Keys]\n        default= 1\n        name=\n        name2=\n\n        Item 'name2', is used for built-in ('default') themes and keys\n        added after 2015 Oct 1 and 2016 July 1.  This kludge is needed\n        because setting 'name' to a builtin not defined in older IDLEs\n        to display multiple error messages or quit.\n        See https://bugs.python.org/issue25313.\n        When default = True, 'name2' takes precedence over 'name',\n        while older IDLEs will just use name.  When default = False,\n        'name2' may still be set, but it is ignored.\n        "
        cfgname = ('highlight' if (section == 'Theme') else 'keys')
        default = self.GetOption('main', section, 'default', type='bool', default=True)
        name = ''
        if default:
            name = self.GetOption('main', section, 'name2', default='')
        if (not name):
            name = self.GetOption('main', section, 'name', default='')
        if name:
            source = (self.defaultCfg if default else self.userCfg)
            if source[cfgname].has_section(name):
                return name
        return ('IDLE Classic' if (section == 'Theme') else self.default_keys())

    @staticmethod
    def default_keys():
        if (sys.platform[:3] == 'win'):
            return 'IDLE Classic Windows'
        elif (sys.platform == 'darwin'):
            return 'IDLE Classic OSX'
        else:
            return 'IDLE Modern Unix'

    def GetExtensions(self, active_only=True, editor_only=False, shell_only=False):
        'Return extensions in default and user config-extensions files.\n\n        If active_only True, only return active (enabled) extensions\n        and optionally only editor or shell extensions.\n        If active_only False, return all extensions.\n        '
        extns = self.RemoveKeyBindNames(self.GetSectionList('default', 'extensions'))
        userExtns = self.RemoveKeyBindNames(self.GetSectionList('user', 'extensions'))
        for extn in userExtns:
            if (extn not in extns):
                extns.append(extn)
        for extn in ('AutoComplete', 'CodeContext', 'FormatParagraph', 'ParenMatch'):
            extns.remove(extn)
        if active_only:
            activeExtns = []
            for extn in extns:
                if self.GetOption('extensions', extn, 'enable', default=True, type='bool'):
                    if (editor_only or shell_only):
                        if editor_only:
                            option = 'enable_editor'
                        else:
                            option = 'enable_shell'
                        if self.GetOption('extensions', extn, option, default=True, type='bool', warn_on_default=False):
                            activeExtns.append(extn)
                    else:
                        activeExtns.append(extn)
            return activeExtns
        else:
            return extns

    def RemoveKeyBindNames(self, extnNameList):
        'Return extnNameList with keybinding section names removed.'
        return [n for n in extnNameList if (not n.endswith(('_bindings', '_cfgBindings')))]

    def GetExtnNameForEvent(self, virtualEvent):
        "Return the name of the extension binding virtualEvent, or None.\n\n        virtualEvent - string, name of the virtual event to test for,\n                       without the enclosing '<< >>'\n        "
        extName = None
        vEvent = (('<<' + virtualEvent) + '>>')
        for extn in self.GetExtensions(active_only=0):
            for event in self.GetExtensionKeys(extn):
                if (event == vEvent):
                    extName = extn
        return extName

    def GetExtensionKeys(self, extensionName):
        'Return dict: {configurable extensionName event : active keybinding}.\n\n        Events come from default config extension_cfgBindings section.\n        Keybindings come from GetCurrentKeySet() active key dict,\n        where previously used bindings are disabled.\n        '
        keysName = (extensionName + '_cfgBindings')
        activeKeys = self.GetCurrentKeySet()
        extKeys = {}
        if self.defaultCfg['extensions'].has_section(keysName):
            eventNames = self.defaultCfg['extensions'].GetOptionList(keysName)
            for eventName in eventNames:
                event = (('<<' + eventName) + '>>')
                binding = activeKeys[event]
                extKeys[event] = binding
        return extKeys

    def __GetRawExtensionKeys(self, extensionName):
        'Return dict {configurable extensionName event : keybinding list}.\n\n        Events come from default config extension_cfgBindings section.\n        Keybindings list come from the splitting of GetOption, which\n        tries user config before default config.\n        '
        keysName = (extensionName + '_cfgBindings')
        extKeys = {}
        if self.defaultCfg['extensions'].has_section(keysName):
            eventNames = self.defaultCfg['extensions'].GetOptionList(keysName)
            for eventName in eventNames:
                binding = self.GetOption('extensions', keysName, eventName, default='').split()
                event = (('<<' + eventName) + '>>')
                extKeys[event] = binding
        return extKeys

    def GetExtensionBindings(self, extensionName):
        'Return dict {extensionName event : active or defined keybinding}.\n\n        Augment self.GetExtensionKeys(extensionName) with mapping of non-\n        configurable events (from default config) to GetOption splits,\n        as in self.__GetRawExtensionKeys.\n        '
        bindsName = (extensionName + '_bindings')
        extBinds = self.GetExtensionKeys(extensionName)
        if self.defaultCfg['extensions'].has_section(bindsName):
            eventNames = self.defaultCfg['extensions'].GetOptionList(bindsName)
            for eventName in eventNames:
                binding = self.GetOption('extensions', bindsName, eventName, default='').split()
                event = (('<<' + eventName) + '>>')
                extBinds[event] = binding
        return extBinds

    def GetKeyBinding(self, keySetName, eventStr):
        "Return the keybinding list for keySetName eventStr.\n\n        keySetName - name of key binding set (config-keys section).\n        eventStr - virtual event, including brackets, as in '<<event>>'.\n        "
        eventName = eventStr[2:(- 2)]
        binding = self.GetOption('keys', keySetName, eventName, default='', warn_on_default=False).split()
        return binding

    def GetCurrentKeySet(self):
        "Return CurrentKeys with 'darwin' modifications."
        result = self.GetKeySet(self.CurrentKeys())
        if (sys.platform == 'darwin'):
            for (k, v) in result.items():
                v2 = [x.replace('<Alt-', '<Option-') for x in v]
                if (v != v2):
                    result[k] = v2
        return result

    def GetKeySet(self, keySetName):
        "Return event-key dict for keySetName core plus active extensions.\n\n        If a binding defined in an extension is already in use, the\n        extension binding is disabled by being set to ''\n        "
        keySet = self.GetCoreKeys(keySetName)
        activeExtns = self.GetExtensions(active_only=1)
        for extn in activeExtns:
            extKeys = self.__GetRawExtensionKeys(extn)
            if extKeys:
                for event in extKeys:
                    if (extKeys[event] in keySet.values()):
                        extKeys[event] = ''
                    keySet[event] = extKeys[event]
        return keySet

    def IsCoreBinding(self, virtualEvent):
        "Return True if the virtual event is one of the core idle key events.\n\n        virtualEvent - string, name of the virtual event to test for,\n                       without the enclosing '<< >>'\n        "
        return ((('<<' + virtualEvent) + '>>') in self.GetCoreKeys())
    former_extension_events = {'<<force-open-completions>>', '<<expand-word>>', '<<force-open-calltip>>', '<<flash-paren>>', '<<format-paragraph>>', '<<run-module>>', '<<check-module>>', '<<zoom-height>>', '<<run-custom>>'}

    def GetCoreKeys(self, keySetName=None):
        "Return dict of core virtual-key keybindings for keySetName.\n\n        The default keySetName None corresponds to the keyBindings base\n        dict. If keySetName is not None, bindings from the config\n        file(s) are loaded _over_ these defaults, so if there is a\n        problem getting any core binding there will be an 'ultimate last\n        resort fallback' to the CUA-ish bindings defined here.\n        "
        keyBindings = {'<<copy>>': ['<Control-c>', '<Control-C>'], '<<cut>>': ['<Control-x>', '<Control-X>'], '<<paste>>': ['<Control-v>', '<Control-V>'], '<<beginning-of-line>>': ['<Control-a>', '<Home>'], '<<center-insert>>': ['<Control-l>'], '<<close-all-windows>>': ['<Control-q>'], '<<close-window>>': ['<Alt-F4>'], '<<do-nothing>>': ['<Control-x>'], '<<end-of-file>>': ['<Control-d>'], '<<python-docs>>': ['<F1>'], '<<python-context-help>>': ['<Shift-F1>'], '<<history-next>>': ['<Alt-n>'], '<<history-previous>>': ['<Alt-p>'], '<<interrupt-execution>>': ['<Control-c>'], '<<view-restart>>': ['<F6>'], '<<restart-shell>>': ['<Control-F6>'], '<<open-class-browser>>': ['<Alt-c>'], '<<open-module>>': ['<Alt-m>'], '<<open-new-window>>': ['<Control-n>'], '<<open-window-from-file>>': ['<Control-o>'], '<<plain-newline-and-indent>>': ['<Control-j>'], '<<print-window>>': ['<Control-p>'], '<<redo>>': ['<Control-y>'], '<<remove-selection>>': ['<Escape>'], '<<save-copy-of-window-as-file>>': ['<Alt-Shift-S>'], '<<save-window-as-file>>': ['<Alt-s>'], '<<save-window>>': ['<Control-s>'], '<<select-all>>': ['<Alt-a>'], '<<toggle-auto-coloring>>': ['<Control-slash>'], '<<undo>>': ['<Control-z>'], '<<find-again>>': ['<Control-g>', '<F3>'], '<<find-in-files>>': ['<Alt-F3>'], '<<find-selection>>': ['<Control-F3>'], '<<find>>': ['<Control-f>'], '<<replace>>': ['<Control-h>'], '<<goto-line>>': ['<Alt-g>'], '<<smart-backspace>>': ['<Key-BackSpace>'], '<<newline-and-indent>>': ['<Key-Return>', '<Key-KP_Enter>'], '<<smart-indent>>': ['<Key-Tab>'], '<<indent-region>>': ['<Control-Key-bracketright>'], '<<dedent-region>>': ['<Control-Key-bracketleft>'], '<<comment-region>>': ['<Alt-Key-3>'], '<<uncomment-region>>': ['<Alt-Key-4>'], '<<tabify-region>>': ['<Alt-Key-5>'], '<<untabify-region>>': ['<Alt-Key-6>'], '<<toggle-tabs>>': ['<Alt-Key-t>'], '<<change-indentwidth>>': ['<Alt-Key-u>'], '<<del-word-left>>': ['<Control-Key-BackSpace>'], '<<del-word-right>>': ['<Control-Key-Delete>'], '<<force-open-completions>>': ['<Control-Key-space>'], '<<expand-word>>': ['<Alt-Key-slash>'], '<<force-open-calltip>>': ['<Control-Key-backslash>'], '<<flash-paren>>': ['<Control-Key-0>'], '<<format-paragraph>>': ['<Alt-Key-q>'], '<<run-module>>': ['<Key-F5>'], '<<run-custom>>': ['<Shift-Key-F5>'], '<<check-module>>': ['<Alt-Key-x>'], '<<zoom-height>>': ['<Alt-Key-2>']}
        if keySetName:
            if (not (self.userCfg['keys'].has_section(keySetName) or self.defaultCfg['keys'].has_section(keySetName))):
                warning = ('\n Warning: config.py - IdleConf.GetCoreKeys -\n key set %r is not defined, using default bindings.' % (keySetName,))
                _warn(warning, 'keys', keySetName)
            else:
                for event in keyBindings:
                    binding = self.GetKeyBinding(keySetName, event)
                    if binding:
                        keyBindings[event] = binding
                    elif (event not in self.former_extension_events):
                        warning = ('\n Warning: config.py - IdleConf.GetCoreKeys -\n problem retrieving key binding for event %r\n from key set %r.\n returning default value: %r' % (event, keySetName, keyBindings[event]))
                        _warn(warning, 'keys', keySetName, event)
        return keyBindings

    def GetExtraHelpSourceList(self, configSet):
        "Return list of extra help sources from a given configSet.\n\n        Valid configSets are 'user' or 'default'.  Return a list of tuples of\n        the form (menu_item , path_to_help_file , option), or return the empty\n        list.  'option' is the sequence number of the help resource.  'option'\n        values determine the position of the menu items on the Help menu,\n        therefore the returned list must be sorted by 'option'.\n\n        "
        helpSources = []
        if (configSet == 'user'):
            cfgParser = self.userCfg['main']
        elif (configSet == 'default'):
            cfgParser = self.defaultCfg['main']
        else:
            raise InvalidConfigSet('Invalid configSet specified')
        options = cfgParser.GetOptionList('HelpFiles')
        for option in options:
            value = cfgParser.Get('HelpFiles', option, default=';')
            if (value.find(';') == (- 1)):
                menuItem = ''
                helpPath = ''
            else:
                value = value.split(';')
                menuItem = value[0].strip()
                helpPath = value[1].strip()
            if (menuItem and helpPath):
                helpSources.append((menuItem, helpPath, option))
        helpSources.sort(key=(lambda x: x[2]))
        return helpSources

    def GetAllExtraHelpSourcesList(self):
        'Return a list of the details of all additional help sources.\n\n        Tuples in the list are those of GetExtraHelpSourceList.\n        '
        allHelpSources = (self.GetExtraHelpSourceList('default') + self.GetExtraHelpSourceList('user'))
        return allHelpSources

    def GetFont(self, root, configType, section):
        "Retrieve a font from configuration (font, font-size, font-bold)\n        Intercept the special value 'TkFixedFont' and substitute\n        the actual font, factoring in some tweaks if needed for\n        appearance sakes.\n\n        The 'root' parameter can normally be any valid Tkinter widget.\n\n        Return a tuple (family, size, weight) suitable for passing\n        to tkinter.Font\n        "
        family = self.GetOption(configType, section, 'font', default='courier')
        size = self.GetOption(configType, section, 'font-size', type='int', default='10')
        bold = self.GetOption(configType, section, 'font-bold', default=0, type='bool')
        if (family == 'TkFixedFont'):
            f = Font(name='TkFixedFont', exists=True, root=root)
            actualFont = Font.actual(f)
            family = actualFont['family']
            size = actualFont['size']
            if (size <= 0):
                size = 10
            bold = (actualFont['weight'] == 'bold')
        return (family, size, ('bold' if bold else 'normal'))

    def LoadCfgFiles(self):
        'Load all configuration files.'
        for key in self.defaultCfg:
            self.defaultCfg[key].Load()
            self.userCfg[key].Load()

    def SaveUserCfgFiles(self):
        'Write all loaded user configuration files to disk.'
        for key in self.userCfg:
            self.userCfg[key].Save()
idleConf = IdleConf()
_warned = set()

def _warn(msg, *key):
    key = ((msg,) + key)
    if (key not in _warned):
        try:
            print(msg, file=sys.stderr)
        except OSError:
            pass
        _warned.add(key)

class ConfigChanges(dict):
    "Manage a user's proposed configuration option changes.\n\n    Names used across multiple methods:\n        page -- one of the 4 top-level dicts representing a\n                .idlerc/config-x.cfg file.\n        config_type -- name of a page.\n        section -- a section within a page/file.\n        option -- name of an option within a section.\n        value -- value for the option.\n\n    Methods\n        add_option: Add option and value to changes.\n        save_option: Save option and value to config parser.\n        save_all: Save all the changes to the config parser and file.\n        delete_section: If section exists,\n                        delete from changes, userCfg, and file.\n        clear: Clear all changes by clearing each page.\n    "

    def __init__(self):
        'Create a page for each configuration file'
        self.pages = []
        for config_type in idleConf.config_types:
            self[config_type] = {}
            self.pages.append(self[config_type])

    def add_option(self, config_type, section, item, value):
        'Add item/value pair for config_type and section.'
        page = self[config_type]
        value = str(value)
        if (section not in page):
            page[section] = {}
        page[section][item] = value

    @staticmethod
    def save_option(config_type, section, item, value):
        'Return True if the configuration value was added or changed.\n\n        Helper for save_all.\n        '
        if idleConf.defaultCfg[config_type].has_option(section, item):
            if (idleConf.defaultCfg[config_type].Get(section, item) == value):
                return idleConf.userCfg[config_type].RemoveOption(section, item)
        return idleConf.userCfg[config_type].SetOption(section, item, value)

    def save_all(self):
        'Save configuration changes to the user config file.\n\n        Clear self in preparation for additional changes.\n        Return changed for testing.\n        '
        idleConf.userCfg['main'].Save()
        changed = False
        for config_type in self:
            cfg_type_changed = False
            page = self[config_type]
            for section in page:
                if (section == 'HelpFiles'):
                    idleConf.userCfg['main'].remove_section('HelpFiles')
                    cfg_type_changed = True
                for (item, value) in page[section].items():
                    if self.save_option(config_type, section, item, value):
                        cfg_type_changed = True
            if cfg_type_changed:
                idleConf.userCfg[config_type].Save()
                changed = True
        for config_type in ['keys', 'highlight']:
            idleConf.userCfg[config_type].Save()
        self.clear()
        return changed

    def delete_section(self, config_type, section):
        'Delete a section from self, userCfg, and file.\n\n        Used to delete custom themes and keysets.\n        '
        if (section in self[config_type]):
            del self[config_type][section]
        configpage = idleConf.userCfg[config_type]
        configpage.remove_section(section)
        configpage.Save()

    def clear(self):
        'Clear all 4 pages.\n\n        Called in save_all after saving to idleConf.\n        XXX Mark window *title* when there are changes; unmark here.\n        '
        for page in self.pages:
            page.clear()

def _dump():
    from zlib import crc32
    (line, crc) = (0, 0)

    def sprint(obj):
        global line, crc
        txt = str(obj)
        line += 1
        crc = crc32(txt.encode(encoding='utf-8'), crc)
        print(txt)

    def dumpCfg(cfg):
        print('\n', cfg, '\n')
        for key in sorted(cfg.keys()):
            sections = cfg[key].sections()
            sprint(key)
            sprint(sections)
            for section in sections:
                options = cfg[key].options(section)
                sprint(section)
                sprint(options)
                for option in options:
                    sprint(((option + ' = ') + cfg[key].Get(section, option)))
    dumpCfg(idleConf.defaultCfg)
    dumpCfg(idleConf.userCfg)
    print('\nlines = ', line, ', crc = ', crc, sep='')
if (__name__ == '__main__'):
    from unittest import main
    main('idlelib.idle_test.test_config', verbosity=2, exit=False)
