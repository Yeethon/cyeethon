"IDLE Configuration Dialog: support user customization of IDLE by GUI\n\nCustomize font faces, sizes, and colorization attributes.  Set indentation\ndefaults.  Customize keybindings.  Colorization and keybindings can be\nsaved as user defined sets.  Select startup options including shell/editor\nand default window size.  Define additional help sources.\n\nNote that tab width in IDLE is currently fixed at eight due to Tk issues.\nRefer to comments in EditorWindow autoindent code for details.\n\n"
import re
from tkinter import (
    Toplevel,
    Listbox,
    Scale,
    Canvas,
    StringVar,
    BooleanVar,
    IntVar,
    TRUE,
    FALSE,
    TOP,
    BOTTOM,
    RIGHT,
    LEFT,
    SOLID,
    GROOVE,
    NONE,
    BOTH,
    X,
    Y,
    W,
    E,
    EW,
    NS,
    NSEW,
    NW,
    HORIZONTAL,
    VERTICAL,
    ANCHOR,
    ACTIVE,
    END,
)
from tkinter.ttk import (
    Frame,
    LabelFrame,
    Button,
    Checkbutton,
    Entry,
    Label,
    OptionMenu,
    Notebook,
    Radiobutton,
    Scrollbar,
    Style,
)
from tkinter import colorchooser
import tkinter.font as tkfont
from tkinter import messagebox
from idlelib.config import idleConf, ConfigChanges
from idlelib.config_key import GetKeysDialog
from idlelib.dynoption import DynOptionMenu
from idlelib import macosx
from idlelib.query import SectionName, HelpSource
from idlelib.textview import view_text
from idlelib.autocomplete import AutoComplete
from idlelib.codecontext import CodeContext
from idlelib.parenmatch import ParenMatch
from idlelib.format import FormatParagraph
from idlelib.squeezer import Squeezer
from idlelib.textview import ScrollableTextFrame

changes = ConfigChanges()
reloadables = (AutoComplete, CodeContext, ParenMatch, FormatParagraph, Squeezer)


class ConfigDialog(Toplevel):
    "Config dialog for IDLE.\n    "

    def __init__(self, parent, title="", *, _htest=False, _utest=False):
        "Show the tabbed dialog for user configuration.\n\n        Args:\n            parent - parent of this dialog\n            title - string which is the title of this popup dialog\n            _htest - bool, change box location when running htest\n            _utest - bool, don't wait_window when running unittest\n\n        Note: Focus set on font page fontlist.\n\n        Methods:\n            create_widgets\n            cancel: Bound to DELETE_WINDOW protocol.\n        "
        Toplevel.__init__(self, parent)
        self.parent = parent
        if _htest:
            parent.instance_dict = {}
        if not _utest:
            self.withdraw()
        self.title((title or "IDLE Preferences"))
        x = parent.winfo_rootx() + 20
        y = parent.winfo_rooty() + (30 if (not _htest) else 150)
        self.geometry(f"+{x}+{y}")
        self.create_widgets()
        self.resizable(height=FALSE, width=FALSE)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.fontpage.fontlist.focus_set()
        tracers.attach()
        if not _utest:
            self.grab_set()
            self.wm_deiconify()
            self.wait_window()

    def create_widgets(self):
        "Create and place widgets for tabbed dialog.\n\n        Widgets Bound to self:\n            frame: encloses all other widgets\n            note: Notebook\n            highpage: HighPage\n            fontpage: FontPage\n            keyspage: KeysPage\n            genpage: GenPage\n            extpage: self.create_page_extensions\n\n        Methods:\n            create_action_buttons\n            load_configs: Load pages except for extensions.\n            activate_config_changes: Tell editors to reload.\n        "
        self.frame = frame = Frame(self, padding="5px")
        self.frame.grid(sticky="nwes")
        self.note = note = Notebook(frame)
        self.highpage = HighPage(note)
        self.fontpage = FontPage(note, self.highpage)
        self.keyspage = KeysPage(note)
        self.genpage = GenPage(note)
        self.extpage = self.create_page_extensions()
        note.add(self.fontpage, text="Fonts/Tabs")
        note.add(self.highpage, text="Highlights")
        note.add(self.keyspage, text=" Keys ")
        note.add(self.genpage, text=" General ")
        note.add(self.extpage, text="Extensions")
        note.enable_traversal()
        note.pack(side=TOP, expand=TRUE, fill=BOTH)
        self.create_action_buttons().pack(side=BOTTOM)

    def create_action_buttons(self):
        "Return frame of action buttons for dialog.\n\n        Methods:\n            ok\n            apply\n            cancel\n            help\n\n        Widget Structure:\n            outer: Frame\n                buttons: Frame\n                    (no assignment): Button (ok)\n                    (no assignment): Button (apply)\n                    (no assignment): Button (cancel)\n                    (no assignment): Button (help)\n                (no assignment): Frame\n        "
        if macosx.isAquaTk():
            padding_args = {}
        else:
            padding_args = {"padding": (6, 3)}
        outer = Frame(self.frame, padding=2)
        buttons_frame = Frame(outer, padding=2)
        self.buttons = {}
        for (txt, cmd) in (
            ("Ok", self.ok),
            ("Apply", self.apply),
            ("Cancel", self.cancel),
            ("Help", self.help),
        ):
            self.buttons[txt] = Button(
                buttons_frame, text=txt, command=cmd, takefocus=FALSE, **padding_args
            )
            self.buttons[txt].pack(side=LEFT, padx=5)
        Frame(outer, height=2, borderwidth=0).pack(side=TOP)
        buttons_frame.pack(side=BOTTOM)
        return outer

    def ok(self):
        "Apply config changes, then dismiss dialog.\n\n        Methods:\n            apply\n            destroy: inherited\n        "
        self.apply()
        self.destroy()

    def apply(self):
        "Apply config changes and leave dialog open.\n\n        Methods:\n            deactivate_current_config\n            save_all_changed_extensions\n            activate_config_changes\n        "
        self.deactivate_current_config()
        changes.save_all()
        self.save_all_changed_extensions()
        self.activate_config_changes()

    def cancel(self):
        "Dismiss config dialog.\n\n        Methods:\n            destroy: inherited\n        "
        changes.clear()
        self.destroy()

    def destroy(self):
        global font_sample_text
        font_sample_text = self.fontpage.font_sample.get("1.0", "end")
        self.grab_release()
        super().destroy()

    def help(self):
        "Create textview for config dialog help.\n\n        Attributes accessed:\n            note\n        Methods:\n            view_text: Method from textview module.\n        "
        page = self.note.tab(self.note.select(), option="text").strip()
        view_text(
            self,
            title="Help for IDLE preferences",
            contents=(help_common + help_pages.get(page, "")),
        )

    def deactivate_current_config(self):
        "Remove current key bindings.\n        Iterate over window instances defined in parent and remove\n        the keybindings.\n        "
        win_instances = self.parent.instance_dict.keys()
        for instance in win_instances:
            instance.RemoveKeybindings()

    def activate_config_changes(self):
        "Apply configuration changes to current windows.\n\n        Dynamically update the current parent window instances\n        with some of the configuration changes.\n        "
        win_instances = self.parent.instance_dict.keys()
        for instance in win_instances:
            instance.ResetColorizer()
            instance.ResetFont()
            instance.set_notabs_indentwidth()
            instance.ApplyKeybindings()
            instance.reset_help_menu_entries()
            instance.update_cursor_blink()
        for klass in reloadables:
            klass.reload()

    def create_page_extensions(self):
        "Part of the config dialog used for configuring IDLE extensions.\n\n        This code is generic - it works for any and all IDLE extensions.\n\n        IDLE extensions save their configuration options using idleConf.\n        This code reads the current configuration using idleConf, supplies a\n        GUI interface to change the configuration values, and saves the\n        changes using idleConf.\n\n        Not all changes take effect immediately - some may require restarting IDLE.\n        This depends on each extension's implementation.\n\n        All values are treated as text, and it is up to the user to supply\n        reasonable values. The only exception to this are the 'enable*' options,\n        which are boolean, and can be toggled with a True/False button.\n\n        Methods:\n            load_extensions:\n            extension_selected: Handle selection from list.\n            create_extension_frame: Hold widgets for one extension.\n            set_extension_value: Set in userCfg['extensions'].\n            save_all_changed_extensions: Call extension page Save().\n        "
        parent = self.parent
        frame = Frame(self.note)
        self.ext_defaultCfg = idleConf.defaultCfg["extensions"]
        self.ext_userCfg = idleConf.userCfg["extensions"]
        self.is_int = self.register(is_int)
        self.load_extensions()
        self.extension_names = StringVar(self)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)
        self.extension_list = Listbox(
            frame, listvariable=self.extension_names, selectmode="browse"
        )
        self.extension_list.bind("<<ListboxSelect>>", self.extension_selected)
        scroll = Scrollbar(frame, command=self.extension_list.yview)
        self.extension_list.yscrollcommand = scroll.set
        self.details_frame = LabelFrame(frame, width=250, height=250)
        self.extension_list.grid(column=0, row=0, sticky="nws")
        scroll.grid(column=1, row=0, sticky="ns")
        self.details_frame.grid(column=2, row=0, sticky="nsew", padx=[10, 0])
        frame.configure(padding=10)
        self.config_frame = {}
        self.current_extension = None
        self.outerframe = self
        self.tabbed_page_set = self.extension_list
        ext_names = ""
        for ext_name in sorted(self.extensions):
            self.create_extension_frame(ext_name)
            ext_names = ((ext_names + "{") + ext_name) + "} "
        self.extension_names.set(ext_names)
        self.extension_list.selection_set(0)
        self.extension_selected(None)
        return frame

    def load_extensions(self):
        "Fill self.extensions with data from the default and user configs."
        self.extensions = {}
        for ext_name in idleConf.GetExtensions(active_only=False):
            self.extensions[ext_name] = []
        for ext_name in self.extensions:
            opt_list = sorted(self.ext_defaultCfg.GetOptionList(ext_name))
            enables = [
                opt_name for opt_name in opt_list if opt_name.startswith("enable")
            ]
            for opt_name in enables:
                opt_list.remove(opt_name)
            opt_list = enables + opt_list
            for opt_name in opt_list:
                def_str = self.ext_defaultCfg.Get(ext_name, opt_name, raw=True)
                try:
                    def_obj = {"True": True, "False": False}[def_str]
                    opt_type = "bool"
                except KeyError:
                    try:
                        def_obj = int(def_str)
                        opt_type = "int"
                    except ValueError:
                        def_obj = def_str
                        opt_type = None
                try:
                    value = self.ext_userCfg.Get(
                        ext_name, opt_name, type=opt_type, raw=True, default=def_obj
                    )
                except ValueError:
                    value = def_obj
                var = StringVar(self)
                var.set(str(value))
                self.extensions[ext_name].append(
                    {
                        "name": opt_name,
                        "type": opt_type,
                        "default": def_str,
                        "value": value,
                        "var": var,
                    }
                )

    def extension_selected(self, event):
        "Handle selection of an extension from the list."
        newsel = self.extension_list.curselection()
        if newsel:
            newsel = self.extension_list.get(newsel)
        if (newsel is None) or (newsel != self.current_extension):
            if self.current_extension:
                self.details_frame.config(text="")
                self.config_frame[self.current_extension].grid_forget()
                self.current_extension = None
        if newsel:
            self.details_frame.config(text=newsel)
            self.config_frame[newsel].grid(column=0, row=0, sticky="nsew")
            self.current_extension = newsel

    def create_extension_frame(self, ext_name):
        "Create a frame holding the widgets to configure one extension"
        f = VerticalScrolledFrame(self.details_frame, height=250, width=250)
        self.config_frame[ext_name] = f
        entry_area = f.interior
        for (row, opt) in enumerate(self.extensions[ext_name]):
            label = Label(entry_area, text=opt["name"])
            label.grid(row=row, column=0, sticky=NW)
            var = opt["var"]
            if opt["type"] == "bool":
                Checkbutton(
                    entry_area, variable=var, onvalue="True", offvalue="False", width=8
                ).grid(row=row, column=1, sticky=W, padx=7)
            elif opt["type"] == "int":
                Entry(
                    entry_area,
                    textvariable=var,
                    validate="key",
                    validatecommand=(self.is_int, "%P"),
                    width=10,
                ).grid(row=row, column=1, sticky=NSEW, padx=7)
            else:
                Entry(entry_area, textvariable=var, width=15).grid(
                    row=row, column=1, sticky=NSEW, padx=7
                )
        return

    def set_extension_value(self, section, opt):
        "Return True if the configuration was added or changed.\n\n        If the value is the same as the default, then remove it\n        from user config file.\n        "
        name = opt["name"]
        default = opt["default"]
        value = opt["var"].get().strip() or default
        opt["var"].set(value)
        if value == default:
            return self.ext_userCfg.RemoveOption(section, name)
        return self.ext_userCfg.SetOption(section, name, value)

    def save_all_changed_extensions(self):
        "Save configuration changes to the user config file.\n\n        Attributes accessed:\n            extensions\n\n        Methods:\n            set_extension_value\n        "
        has_changes = False
        for ext_name in self.extensions:
            options = self.extensions[ext_name]
            for opt in options:
                if self.set_extension_value(ext_name, opt):
                    has_changes = True
        if has_changes:
            self.ext_userCfg.Save()


font_sample_text = "<ASCII/Latin1>\nAaBbCcDdEeFfGgHhIiJj\n1234567890#:+=(){}[]\n¢£¥§©«®¶½ĞÀÁÂÃÄÅÇÐØß\n\n<IPA,Greek,Cyrillic>\nɐɕɘɞɟɤɫɮɰɷɻʁʃʆʎʞʢʫʭʯ\nΑαΒβΓγΔδΕεΖζΗηΘθΙιΚκ\nБбДдЖжПпФфЧчЪъЭэѠѤѬӜ\n\n<Hebrew, Arabic>\nאבגדהוזחטיךכלםמןנסעף\nابجدهوزحطي٠١٢٣٤٥٦٧٨٩\n\n<Devanagari, Tamil>\n०१२३४५६७८९अआइईउऊएऐओऔ\n௦௧௨௩௪௫௬௭௮௯அஇஉஎ\n\n<East Asian>\n〇一二三四五六七八九\n汉字漢字人木火土金水\n가냐더려모뵤수유즈치\nあいうえおアイウエオ\n"


class FontPage(Frame):
    def __init__(self, master, highpage):
        super().__init__(master)
        self.highlight_sample = highpage.highlight_sample
        self.create_page_font_tab()
        self.load_font_cfg()
        self.load_tab_cfg()

    def create_page_font_tab(self):
        "Return frame of widgets for Font/Tabs tab.\n\n        Fonts: Enable users to provisionally change font face, size, or\n        boldness and to see the consequence of proposed choices.  Each\n        action set 3 options in changes structuree and changes the\n        corresponding aspect of the font sample on this page and\n        highlight sample on highlight page.\n\n        Function load_font_cfg initializes font vars and widgets from\n        idleConf entries and tk.\n\n        Fontlist: mouse button 1 click or up or down key invoke\n        on_fontlist_select(), which sets var font_name.\n\n        Sizelist: clicking the menubutton opens the dropdown menu. A\n        mouse button 1 click or return key sets var font_size.\n\n        Bold_toggle: clicking the box toggles var font_bold.\n\n        Changing any of the font vars invokes var_changed_font, which\n        adds all 3 font options to changes and calls set_samples.\n        Set_samples applies a new font constructed from the font vars to\n        font_sample and to highlight_sample on the highlight page.\n\n        Tabs: Enable users to change spaces entered for indent tabs.\n        Changing indent_scale value with the mouse sets Var space_num,\n        which invokes the default callback to add an entry to\n        changes.  Load_tab_cfg initializes space_num to default.\n\n        Widgets for FontPage(Frame):  (*) widgets bound to self\n            frame_font: LabelFrame\n                frame_font_name: Frame\n                    font_name_title: Label\n                    (*)fontlist: ListBox - font_name\n                    scroll_font: Scrollbar\n                frame_font_param: Frame\n                    font_size_title: Label\n                    (*)sizelist: DynOptionMenu - font_size\n                    (*)bold_toggle: Checkbutton - font_bold\n            frame_sample: LabelFrame\n                (*)font_sample: Label\n            frame_indent: LabelFrame\n                    indent_title: Label\n                    (*)indent_scale: Scale - space_num\n        "
        self.font_name = tracers.add(StringVar(self), self.var_changed_font)
        self.font_size = tracers.add(StringVar(self), self.var_changed_font)
        self.font_bold = tracers.add(BooleanVar(self), self.var_changed_font)
        self.space_num = tracers.add(IntVar(self), ("main", "Indent", "num-spaces"))
        frame_font = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Shell/Editor Font "
        )
        frame_sample = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Font Sample (Editable) "
        )
        frame_indent = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Indentation Width "
        )
        frame_font_name = Frame(frame_font)
        frame_font_param = Frame(frame_font)
        font_name_title = Label(frame_font_name, justify=LEFT, text="Font Face :")
        self.fontlist = Listbox(
            frame_font_name, height=15, takefocus=True, exportselection=FALSE
        )
        self.fontlist.bind("<ButtonRelease-1>", self.on_fontlist_select)
        self.fontlist.bind("<KeyRelease-Up>", self.on_fontlist_select)
        self.fontlist.bind("<KeyRelease-Down>", self.on_fontlist_select)
        scroll_font = Scrollbar(frame_font_name)
        scroll_font.config(command=self.fontlist.yview)
        self.fontlist.config(yscrollcommand=scroll_font.set)
        font_size_title = Label(frame_font_param, text="Size :")
        self.sizelist = DynOptionMenu(frame_font_param, self.font_size, None)
        self.bold_toggle = Checkbutton(
            frame_font_param,
            variable=self.font_bold,
            onvalue=1,
            offvalue=0,
            text="Bold",
        )
        font_sample_frame = ScrollableTextFrame(frame_sample)
        self.font_sample = font_sample_frame.text
        self.font_sample.config(wrap=NONE, width=1, height=1)
        self.font_sample.insert(END, font_sample_text)
        indent_title = Label(
            frame_indent, justify=LEFT, text="Python Standard: 4 Spaces!"
        )
        self.indent_scale = Scale(
            frame_indent,
            variable=self.space_num,
            orient="horizontal",
            tickinterval=2,
            from_=2,
            to=16,
        )
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        frame_font.grid(row=0, column=0, padx=5, pady=5)
        frame_sample.grid(row=0, column=1, rowspan=3, padx=5, pady=5, sticky="nsew")
        frame_indent.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        frame_font_name.pack(side=TOP, padx=5, pady=5, fill=X)
        frame_font_param.pack(side=TOP, padx=5, pady=5, fill=X)
        font_name_title.pack(side=TOP, anchor=W)
        self.fontlist.pack(side=LEFT, expand=TRUE, fill=X)
        scroll_font.pack(side=LEFT, fill=Y)
        font_size_title.pack(side=LEFT, anchor=W)
        self.sizelist.pack(side=LEFT, anchor=W)
        self.bold_toggle.pack(side=LEFT, anchor=W, padx=20)
        font_sample_frame.pack(expand=TRUE, fill=BOTH)
        indent_title.pack(side=TOP, anchor=W, padx=5)
        self.indent_scale.pack(side=TOP, padx=5, fill=X)

    def load_font_cfg(self):
        "Load current configuration settings for the font options.\n\n        Retrieve current font with idleConf.GetFont and font families\n        from tk. Setup fontlist and set font_name.  Setup sizelist,\n        which sets font_size.  Set font_bold.  Call set_samples.\n        "
        configured_font = idleConf.GetFont(self, "main", "EditorWindow")
        font_name = configured_font[0].lower()
        font_size = configured_font[1]
        font_bold = configured_font[2] == "bold"
        fonts = sorted(set(tkfont.families(self)))
        for font in fonts:
            self.fontlist.insert(END, font)
        self.font_name.set(font_name)
        lc_fonts = [s.lower() for s in fonts]
        try:
            current_font_index = lc_fonts.index(font_name)
            self.fontlist.see(current_font_index)
            self.fontlist.select_set(current_font_index)
            self.fontlist.select_anchor(current_font_index)
            self.fontlist.activate(current_font_index)
        except ValueError:
            pass
        self.sizelist.SetMenu(
            (
                "7",
                "8",
                "9",
                "10",
                "11",
                "12",
                "13",
                "14",
                "16",
                "18",
                "20",
                "22",
                "25",
                "29",
                "34",
                "40",
            ),
            font_size,
        )
        self.font_bold.set(font_bold)
        self.set_samples()

    def var_changed_font(self, *params):
        "Store changes to font attributes.\n\n        When one font attribute changes, save them all, as they are\n        not independent from each other. In particular, when we are\n        overriding the default font, we need to write out everything.\n        "
        value = self.font_name.get()
        changes.add_option("main", "EditorWindow", "font", value)
        value = self.font_size.get()
        changes.add_option("main", "EditorWindow", "font-size", value)
        value = self.font_bold.get()
        changes.add_option("main", "EditorWindow", "font-bold", value)
        self.set_samples()

    def on_fontlist_select(self, event):
        "Handle selecting a font from the list.\n\n        Event can result from either mouse click or Up or Down key.\n        Set font_name and example displays to selection.\n        "
        font = self.fontlist.get(
            (ACTIVE if (event.type.name == "KeyRelease") else ANCHOR)
        )
        self.font_name.set(font.lower())

    def set_samples(self, event=None):
        "Update update both screen samples with the font settings.\n\n        Called on font initialization and change events.\n        Accesses font_name, font_size, and font_bold Variables.\n        Updates font_sample and highlight page highlight_sample.\n        "
        font_name = self.font_name.get()
        font_weight = tkfont.BOLD if self.font_bold.get() else tkfont.NORMAL
        new_font = (font_name, self.font_size.get(), font_weight)
        self.font_sample["font"] = new_font
        self.highlight_sample["font"] = new_font

    def load_tab_cfg(self):
        "Load current configuration settings for the tab options.\n\n        Attributes updated:\n            space_num: Set to value from idleConf.\n        "
        space_num = idleConf.GetOption(
            "main", "Indent", "num-spaces", default=4, type="int"
        )
        self.space_num.set(space_num)

    def var_changed_space_num(self, *params):
        "Store change to indentation size."
        value = self.space_num.get()
        changes.add_option("main", "Indent", "num-spaces", value)


class HighPage(Frame):
    def __init__(self, master):
        super().__init__(master)
        self.cd = master.winfo_toplevel()
        self.style = Style(master)
        self.create_page_highlight()
        self.load_theme_cfg()

    def create_page_highlight(self):
        "Return frame of widgets for Highlighting tab.\n\n        Enable users to provisionally change foreground and background\n        colors applied to textual tags.  Color mappings are stored in\n        complete listings called themes.  Built-in themes in\n        idlelib/config-highlight.def are fixed as far as the dialog is\n        concerned. Any theme can be used as the base for a new custom\n        theme, stored in .idlerc/config-highlight.cfg.\n\n        Function load_theme_cfg() initializes tk variables and theme\n        lists and calls paint_theme_sample() and set_highlight_target()\n        for the current theme.  Radiobuttons builtin_theme_on and\n        custom_theme_on toggle var theme_source, which controls if the\n        current set of colors are from a builtin or custom theme.\n        DynOptionMenus builtinlist and customlist contain lists of the\n        builtin and custom themes, respectively, and the current item\n        from each list is stored in vars builtin_name and custom_name.\n\n        Function paint_theme_sample() applies the colors from the theme\n        to the tags in text widget highlight_sample and then invokes\n        set_color_sample().  Function set_highlight_target() sets the state\n        of the radiobuttons fg_on and bg_on based on the tag and it also\n        invokes set_color_sample().\n\n        Function set_color_sample() sets the background color for the frame\n        holding the color selector.  This provides a larger visual of the\n        color for the current tag and plane (foreground/background).\n\n        Note: set_color_sample() is called from many places and is often\n        called more than once when a change is made.  It is invoked when\n        foreground or background is selected (radiobuttons), from\n        paint_theme_sample() (theme is changed or load_cfg is called), and\n        from set_highlight_target() (target tag is changed or load_cfg called).\n\n        Button delete_custom invokes delete_custom() to delete\n        a custom theme from idleConf.userCfg['highlight'] and changes.\n        Button save_custom invokes save_as_new_theme() which calls\n        get_new_theme_name() and create_new() to save a custom theme\n        and its colors to idleConf.userCfg['highlight'].\n\n        Radiobuttons fg_on and bg_on toggle var fg_bg_toggle to control\n        if the current selected color for a tag is for the foreground or\n        background.\n\n        DynOptionMenu targetlist contains a readable description of the\n        tags applied to Python source within IDLE.  Selecting one of the\n        tags from this list populates highlight_target, which has a callback\n        function set_highlight_target().\n\n        Text widget highlight_sample displays a block of text (which is\n        mock Python code) in which is embedded the defined tags and reflects\n        the color attributes of the current theme and changes for those tags.\n        Mouse button 1 allows for selection of a tag and updates\n        highlight_target with that tag value.\n\n        Note: The font in highlight_sample is set through the config in\n        the fonts tab.\n\n        In other words, a tag can be selected either from targetlist or\n        by clicking on the sample text within highlight_sample.  The\n        plane (foreground/background) is selected via the radiobutton.\n        Together, these two (tag and plane) control what color is\n        shown in set_color_sample() for the current theme.  Button set_color\n        invokes get_color() which displays a ColorChooser to change the\n        color for the selected tag/plane.  If a new color is picked,\n        it will be saved to changes and the highlight_sample and\n        frame background will be updated.\n\n        Tk Variables:\n            color: Color of selected target.\n            builtin_name: Menu variable for built-in theme.\n            custom_name: Menu variable for custom theme.\n            fg_bg_toggle: Toggle for foreground/background color.\n                Note: this has no callback.\n            theme_source: Selector for built-in or custom theme.\n            highlight_target: Menu variable for the highlight tag target.\n\n        Instance Data Attributes:\n            theme_elements: Dictionary of tags for text highlighting.\n                The key is the display name and the value is a tuple of\n                (tag name, display sort order).\n\n        Methods [attachment]:\n            load_theme_cfg: Load current highlight colors.\n            get_color: Invoke colorchooser [button_set_color].\n            set_color_sample_binding: Call set_color_sample [fg_bg_toggle].\n            set_highlight_target: set fg_bg_toggle, set_color_sample().\n            set_color_sample: Set frame background to target.\n            on_new_color_set: Set new color and add option.\n            paint_theme_sample: Recolor sample.\n            get_new_theme_name: Get from popup.\n            create_new: Combine theme with changes and save.\n            save_as_new_theme: Save [button_save_custom].\n            set_theme_type: Command for [theme_source].\n            delete_custom: Activate default [button_delete_custom].\n            save_new: Save to userCfg['theme'] (is function).\n\n        Widgets of highlights page frame:  (*) widgets bound to self\n            frame_custom: LabelFrame\n                (*)highlight_sample: Text\n                (*)frame_color_set: Frame\n                    (*)button_set_color: Button\n                    (*)targetlist: DynOptionMenu - highlight_target\n                frame_fg_bg_toggle: Frame\n                    (*)fg_on: Radiobutton - fg_bg_toggle\n                    (*)bg_on: Radiobutton - fg_bg_toggle\n                (*)button_save_custom: Button\n            frame_theme: LabelFrame\n                theme_type_title: Label\n                (*)builtin_theme_on: Radiobutton - theme_source\n                (*)custom_theme_on: Radiobutton - theme_source\n                (*)builtinlist: DynOptionMenu - builtin_name\n                (*)customlist: DynOptionMenu - custom_name\n                (*)button_delete_custom: Button\n                (*)theme_message: Label\n        "
        self.theme_elements = {
            "Normal Code or Text": ("normal", "00"),
            "Code Context": ("context", "01"),
            "Python Keywords": ("keyword", "02"),
            "Python Definitions": ("definition", "03"),
            "Python Builtins": ("builtin", "04"),
            "Python Comments": ("comment", "05"),
            "Python Strings": ("string", "06"),
            "Selected Text": ("hilite", "07"),
            "Found Text": ("hit", "08"),
            "Cursor": ("cursor", "09"),
            "Editor Breakpoint": ("break", "10"),
            "Shell Prompt": ("console", "11"),
            "Error Text": ("error", "12"),
            "Shell User Output": ("stdout", "13"),
            "Shell User Exception": ("stderr", "14"),
            "Line Number": ("linenumber", "16"),
        }
        self.builtin_name = tracers.add(StringVar(self), self.var_changed_builtin_name)
        self.custom_name = tracers.add(StringVar(self), self.var_changed_custom_name)
        self.fg_bg_toggle = BooleanVar(self)
        self.color = tracers.add(StringVar(self), self.var_changed_color)
        self.theme_source = tracers.add(BooleanVar(self), self.var_changed_theme_source)
        self.highlight_target = tracers.add(
            StringVar(self), self.var_changed_highlight_target
        )
        frame_custom = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Custom Highlighting "
        )
        frame_theme = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Highlighting Theme "
        )
        sample_frame = ScrollableTextFrame(frame_custom, relief=SOLID, borderwidth=1)
        text = self.highlight_sample = sample_frame.text
        text.configure(
            font=("courier", 12, ""),
            cursor="hand2",
            width=1,
            height=1,
            takefocus=FALSE,
            highlightthickness=0,
            wrap=NONE,
        )
        text.bind("<Double-Button-1>", (lambda e: "break"))
        text.bind("<B1-Motion>", (lambda e: "break"))
        string_tags = (
            ("# Click selects item.", "comment"),
            ("\n", "normal"),
            ("code context section", "context"),
            ("\n", "normal"),
            ("| cursor", "cursor"),
            ("\n", "normal"),
            ("def", "keyword"),
            (" ", "normal"),
            ("func", "definition"),
            ("(param):\n  ", "normal"),
            ('"Return None."', "string"),
            ("\n  var0 = ", "normal"),
            ("'string'", "string"),
            ("\n  var1 = ", "normal"),
            ("'selected'", "hilite"),
            ("\n  var2 = ", "normal"),
            ("'found'", "hit"),
            ("\n  var3 = ", "normal"),
            ("list", "builtin"),
            ("(", "normal"),
            ("None", "keyword"),
            (")\n", "normal"),
            ('  breakpoint("line")', "break"),
            ("\n\n", "normal"),
            (">>>", "console"),
            (" 3.14**2\n", "normal"),
            ("9.8596", "stdout"),
            ("\n", "normal"),
            (">>>", "console"),
            (" pri ", "normal"),
            ("n", "error"),
            ("t(\n", "normal"),
            ("SyntaxError", "stderr"),
            ("\n", "normal"),
        )
        for (string, tag) in string_tags:
            text.insert(END, string, tag)
        n_lines = len(text.get("1.0", END).splitlines())
        for lineno in range(1, n_lines):
            text.insert(f"{lineno}.0", f"{lineno:{len(str(n_lines))}d} ", "linenumber")
        for element in self.theme_elements:

            def tem(event, elem=element):
                self.highlight_target.set(elem)

            text.tag_bind(self.theme_elements[element][0], "<ButtonPress-1>", tem)
        text["state"] = "disabled"
        self.style.configure("frame_color_set.TFrame", borderwidth=1, relief="solid")
        self.frame_color_set = Frame(frame_custom, style="frame_color_set.TFrame")
        frame_fg_bg_toggle = Frame(frame_custom)
        self.button_set_color = Button(
            self.frame_color_set, text="Choose Color for :", command=self.get_color
        )
        self.targetlist = DynOptionMenu(
            self.frame_color_set, self.highlight_target, None, highlightthickness=0
        )
        self.fg_on = Radiobutton(
            frame_fg_bg_toggle,
            variable=self.fg_bg_toggle,
            value=1,
            text="Foreground",
            command=self.set_color_sample_binding,
        )
        self.bg_on = Radiobutton(
            frame_fg_bg_toggle,
            variable=self.fg_bg_toggle,
            value=0,
            text="Background",
            command=self.set_color_sample_binding,
        )
        self.fg_bg_toggle.set(1)
        self.button_save_custom = Button(
            frame_custom,
            text="Save as New Custom Theme",
            command=self.save_as_new_theme,
        )
        theme_type_title = Label(frame_theme, text="Select : ")
        self.builtin_theme_on = Radiobutton(
            frame_theme,
            variable=self.theme_source,
            value=1,
            command=self.set_theme_type,
            text="a Built-in Theme",
        )
        self.custom_theme_on = Radiobutton(
            frame_theme,
            variable=self.theme_source,
            value=0,
            command=self.set_theme_type,
            text="a Custom Theme",
        )
        self.builtinlist = DynOptionMenu(
            frame_theme, self.builtin_name, None, command=None
        )
        self.customlist = DynOptionMenu(
            frame_theme, self.custom_name, None, command=None
        )
        self.button_delete_custom = Button(
            frame_theme, text="Delete Custom Theme", command=self.delete_custom
        )
        self.theme_message = Label(frame_theme, borderwidth=2)
        frame_custom.pack(side=LEFT, padx=5, pady=5, expand=TRUE, fill=BOTH)
        frame_theme.pack(side=TOP, padx=5, pady=5, fill=X)
        self.frame_color_set.pack(side=TOP, padx=5, pady=5, fill=X)
        frame_fg_bg_toggle.pack(side=TOP, padx=5, pady=0)
        sample_frame.pack(side=TOP, padx=5, pady=5, expand=TRUE, fill=BOTH)
        self.button_set_color.pack(side=TOP, expand=TRUE, fill=X, padx=8, pady=4)
        self.targetlist.pack(side=TOP, expand=TRUE, fill=X, padx=8, pady=3)
        self.fg_on.pack(side=LEFT, anchor=E)
        self.bg_on.pack(side=RIGHT, anchor=W)
        self.button_save_custom.pack(side=BOTTOM, fill=X, padx=5, pady=5)
        theme_type_title.pack(side=TOP, anchor=W, padx=5, pady=5)
        self.builtin_theme_on.pack(side=TOP, anchor=W, padx=5)
        self.custom_theme_on.pack(side=TOP, anchor=W, padx=5, pady=2)
        self.builtinlist.pack(side=TOP, fill=X, padx=5, pady=5)
        self.customlist.pack(side=TOP, fill=X, anchor=W, padx=5, pady=5)
        self.button_delete_custom.pack(side=TOP, fill=X, padx=5, pady=5)
        self.theme_message.pack(side=TOP, fill=X, pady=5)

    def load_theme_cfg(self):
        "Load current configuration settings for the theme options.\n\n        Based on the theme_source toggle, the theme is set as\n        either builtin or custom and the initial widget values\n        reflect the current settings from idleConf.\n\n        Attributes updated:\n            theme_source: Set from idleConf.\n            builtinlist: List of default themes from idleConf.\n            customlist: List of custom themes from idleConf.\n            custom_theme_on: Disabled if there are no custom themes.\n            custom_theme: Message with additional information.\n            targetlist: Create menu from self.theme_elements.\n\n        Methods:\n            set_theme_type\n            paint_theme_sample\n            set_highlight_target\n        "
        self.theme_source.set(
            idleConf.GetOption("main", "Theme", "default", type="bool", default=1)
        )
        current_option = idleConf.CurrentTheme()
        if self.theme_source.get():
            item_list = idleConf.GetSectionList("default", "highlight")
            item_list.sort()
            self.builtinlist.SetMenu(item_list, current_option)
            item_list = idleConf.GetSectionList("user", "highlight")
            item_list.sort()
            if not item_list:
                self.custom_theme_on.state(("disabled",))
                self.custom_name.set("- no custom themes -")
            else:
                self.customlist.SetMenu(item_list, item_list[0])
        else:
            item_list = idleConf.GetSectionList("user", "highlight")
            item_list.sort()
            self.customlist.SetMenu(item_list, current_option)
            item_list = idleConf.GetSectionList("default", "highlight")
            item_list.sort()
            self.builtinlist.SetMenu(item_list, item_list[0])
        self.set_theme_type()
        theme_names = list(self.theme_elements.keys())
        theme_names.sort(key=(lambda x: self.theme_elements[x][1]))
        self.targetlist.SetMenu(theme_names, theme_names[0])
        self.paint_theme_sample()
        self.set_highlight_target()

    def var_changed_builtin_name(self, *params):
        "Process new builtin theme selection.\n\n        Add the changed theme's name to the changed_items and recreate\n        the sample with the values from the selected theme.\n        "
        old_themes = ("IDLE Classic", "IDLE New")
        value = self.builtin_name.get()
        if value not in old_themes:
            if idleConf.GetOption("main", "Theme", "name") not in old_themes:
                changes.add_option("main", "Theme", "name", old_themes[0])
            changes.add_option("main", "Theme", "name2", value)
            self.theme_message["text"] = "New theme, see Help"
        else:
            changes.add_option("main", "Theme", "name", value)
            changes.add_option("main", "Theme", "name2", "")
            self.theme_message["text"] = ""
        self.paint_theme_sample()

    def var_changed_custom_name(self, *params):
        "Process new custom theme selection.\n\n        If a new custom theme is selected, add the name to the\n        changed_items and apply the theme to the sample.\n        "
        value = self.custom_name.get()
        if value != "- no custom themes -":
            changes.add_option("main", "Theme", "name", value)
            self.paint_theme_sample()

    def var_changed_theme_source(self, *params):
        "Process toggle between builtin and custom theme.\n\n        Update the default toggle value and apply the newly\n        selected theme type.\n        "
        value = self.theme_source.get()
        changes.add_option("main", "Theme", "default", value)
        if value:
            self.var_changed_builtin_name()
        else:
            self.var_changed_custom_name()

    def var_changed_color(self, *params):
        "Process change to color choice."
        self.on_new_color_set()

    def var_changed_highlight_target(self, *params):
        "Process selection of new target tag for highlighting."
        self.set_highlight_target()

    def set_theme_type(self):
        "Set available screen options based on builtin or custom theme.\n\n        Attributes accessed:\n            theme_source\n\n        Attributes updated:\n            builtinlist\n            customlist\n            button_delete_custom\n            custom_theme_on\n\n        Called from:\n            handler for builtin_theme_on and custom_theme_on\n            delete_custom\n            create_new\n            load_theme_cfg\n        "
        if self.theme_source.get():
            self.builtinlist["state"] = "normal"
            self.customlist["state"] = "disabled"
            self.button_delete_custom.state(("disabled",))
        else:
            self.builtinlist["state"] = "disabled"
            self.custom_theme_on.state(("!disabled",))
            self.customlist["state"] = "normal"
            self.button_delete_custom.state(("!disabled",))

    def get_color(self):
        "Handle button to select a new color for the target tag.\n\n        If a new color is selected while using a builtin theme, a\n        name must be supplied to create a custom theme.\n\n        Attributes accessed:\n            highlight_target\n            frame_color_set\n            theme_source\n\n        Attributes updated:\n            color\n\n        Methods:\n            get_new_theme_name\n            create_new\n        "
        target = self.highlight_target.get()
        prev_color = self.style.lookup(self.frame_color_set["style"], "background")
        (rgbTuplet, color_string) = colorchooser.askcolor(
            parent=self,
            title=("Pick new color for : " + target),
            initialcolor=prev_color,
        )
        if color_string and (color_string != prev_color):
            if self.theme_source.get():
                message = "Your changes will be saved as a new Custom Theme. Enter a name for your new Custom Theme below."
                new_theme = self.get_new_theme_name(message)
                if not new_theme:
                    return
                else:
                    self.create_new(new_theme)
                    self.color.set(color_string)
            else:
                self.color.set(color_string)

    def on_new_color_set(self):
        "Display sample of new color selection on the dialog."
        new_color = self.color.get()
        self.style.configure("frame_color_set.TFrame", background=new_color)
        plane = "foreground" if self.fg_bg_toggle.get() else "background"
        sample_element = self.theme_elements[self.highlight_target.get()][0]
        self.highlight_sample.tag_config(sample_element, **{plane: new_color})
        theme = self.custom_name.get()
        theme_element = (sample_element + "-") + plane
        changes.add_option("highlight", theme, theme_element, new_color)

    def get_new_theme_name(self, message):
        "Return name of new theme from query popup."
        used_names = idleConf.GetSectionList(
            "user", "highlight"
        ) + idleConf.GetSectionList("default", "highlight")
        new_theme = SectionName(self, "New Custom Theme", message, used_names).result
        return new_theme

    def save_as_new_theme(self):
        "Prompt for new theme name and create the theme.\n\n        Methods:\n            get_new_theme_name\n            create_new\n        "
        new_theme_name = self.get_new_theme_name("New Theme Name:")
        if new_theme_name:
            self.create_new(new_theme_name)

    def create_new(self, new_theme_name):
        "Create a new custom theme with the given name.\n\n        Create the new theme based on the previously active theme\n        with the current changes applied.  Once it is saved, then\n        activate the new theme.\n\n        Attributes accessed:\n            builtin_name\n            custom_name\n\n        Attributes updated:\n            customlist\n            theme_source\n\n        Method:\n            save_new\n            set_theme_type\n        "
        if self.theme_source.get():
            theme_type = "default"
            theme_name = self.builtin_name.get()
        else:
            theme_type = "user"
            theme_name = self.custom_name.get()
        new_theme = idleConf.GetThemeDict(theme_type, theme_name)
        if theme_name in changes["highlight"]:
            theme_changes = changes["highlight"][theme_name]
            for element in theme_changes:
                new_theme[element] = theme_changes[element]
        self.save_new(new_theme_name, new_theme)
        custom_theme_list = idleConf.GetSectionList("user", "highlight")
        custom_theme_list.sort()
        self.customlist.SetMenu(custom_theme_list, new_theme_name)
        self.theme_source.set(0)
        self.set_theme_type()

    def set_highlight_target(self):
        "Set fg/bg toggle and color based on highlight tag target.\n\n        Instance variables accessed:\n            highlight_target\n\n        Attributes updated:\n            fg_on\n            bg_on\n            fg_bg_toggle\n\n        Methods:\n            set_color_sample\n\n        Called from:\n            var_changed_highlight_target\n            load_theme_cfg\n        "
        if self.highlight_target.get() == "Cursor":
            self.fg_on.state(("disabled",))
            self.bg_on.state(("disabled",))
            self.fg_bg_toggle.set(1)
        else:
            self.fg_on.state(("!disabled",))
            self.bg_on.state(("!disabled",))
            self.fg_bg_toggle.set(1)
        self.set_color_sample()

    def set_color_sample_binding(self, *args):
        "Change color sample based on foreground/background toggle.\n\n        Methods:\n            set_color_sample\n        "
        self.set_color_sample()

    def set_color_sample(self):
        "Set the color of the frame background to reflect the selected target.\n\n        Instance variables accessed:\n            theme_elements\n            highlight_target\n            fg_bg_toggle\n            highlight_sample\n\n        Attributes updated:\n            frame_color_set\n        "
        tag = self.theme_elements[self.highlight_target.get()][0]
        plane = "foreground" if self.fg_bg_toggle.get() else "background"
        color = self.highlight_sample.tag_cget(tag, plane)
        self.style.configure("frame_color_set.TFrame", background=color)

    def paint_theme_sample(self):
        "Apply the theme colors to each element tag in the sample text.\n\n        Instance attributes accessed:\n            theme_elements\n            theme_source\n            builtin_name\n            custom_name\n\n        Attributes updated:\n            highlight_sample: Set the tag elements to the theme.\n\n        Methods:\n            set_color_sample\n\n        Called from:\n            var_changed_builtin_name\n            var_changed_custom_name\n            load_theme_cfg\n        "
        if self.theme_source.get():
            theme = self.builtin_name.get()
        else:
            theme = self.custom_name.get()
        for element_title in self.theme_elements:
            element = self.theme_elements[element_title][0]
            colors = idleConf.GetHighlight(theme, element)
            if element == "cursor":
                colors["background"] = idleConf.GetHighlight(theme, "normal")[
                    "background"
                ]
            if theme in changes["highlight"]:
                theme_dict = changes["highlight"][theme]
                if (element + "-foreground") in theme_dict:
                    colors["foreground"] = theme_dict[(element + "-foreground")]
                if (element + "-background") in theme_dict:
                    colors["background"] = theme_dict[(element + "-background")]
            self.highlight_sample.tag_config(element, **colors)
        self.set_color_sample()

    def save_new(self, theme_name, theme):
        "Save a newly created theme to idleConf.\n\n        theme_name - string, the name of the new theme\n        theme - dictionary containing the new theme\n        "
        idleConf.userCfg["highlight"].AddSection(theme_name)
        for element in theme:
            value = theme[element]
            idleConf.userCfg["highlight"].SetOption(theme_name, element, value)

    def askyesno(self, *args, **kwargs):
        return messagebox.askyesno(*args, **kwargs)

    def delete_custom(self):
        "Handle event to delete custom theme.\n\n        The current theme is deactivated and the default theme is\n        activated.  The custom theme is permanently removed from\n        the config file.\n\n        Attributes accessed:\n            custom_name\n\n        Attributes updated:\n            custom_theme_on\n            customlist\n            theme_source\n            builtin_name\n\n        Methods:\n            deactivate_current_config\n            save_all_changed_extensions\n            activate_config_changes\n            set_theme_type\n        "
        theme_name = self.custom_name.get()
        delmsg = "Are you sure you wish to delete the theme %r ?"
        if not self.askyesno("Delete Theme", (delmsg % theme_name), parent=self):
            return
        self.cd.deactivate_current_config()
        changes.delete_section("highlight", theme_name)
        item_list = idleConf.GetSectionList("user", "highlight")
        item_list.sort()
        if not item_list:
            self.custom_theme_on.state(("disabled",))
            self.customlist.SetMenu(item_list, "- no custom themes -")
        else:
            self.customlist.SetMenu(item_list, item_list[0])
        self.theme_source.set(idleConf.defaultCfg["main"].Get("Theme", "default"))
        self.builtin_name.set(idleConf.defaultCfg["main"].Get("Theme", "name"))
        changes.save_all()
        self.cd.save_all_changed_extensions()
        self.cd.activate_config_changes()
        self.set_theme_type()


class KeysPage(Frame):
    def __init__(self, master):
        super().__init__(master)
        self.cd = master.winfo_toplevel()
        self.create_page_keys()
        self.load_key_cfg()

    def create_page_keys(self):
        "Return frame of widgets for Keys tab.\n\n        Enable users to provisionally change both individual and sets of\n        keybindings (shortcut keys). Except for features implemented as\n        extensions, keybindings are stored in complete sets called\n        keysets. Built-in keysets in idlelib/config-keys.def are fixed\n        as far as the dialog is concerned. Any keyset can be used as the\n        base for a new custom keyset, stored in .idlerc/config-keys.cfg.\n\n        Function load_key_cfg() initializes tk variables and keyset\n        lists and calls load_keys_list for the current keyset.\n        Radiobuttons builtin_keyset_on and custom_keyset_on toggle var\n        keyset_source, which controls if the current set of keybindings\n        are from a builtin or custom keyset. DynOptionMenus builtinlist\n        and customlist contain lists of the builtin and custom keysets,\n        respectively, and the current item from each list is stored in\n        vars builtin_name and custom_name.\n\n        Button delete_custom_keys invokes delete_custom_keys() to delete\n        a custom keyset from idleConf.userCfg['keys'] and changes.  Button\n        save_custom_keys invokes save_as_new_key_set() which calls\n        get_new_keys_name() and create_new_key_set() to save a custom keyset\n        and its keybindings to idleConf.userCfg['keys'].\n\n        Listbox bindingslist contains all of the keybindings for the\n        selected keyset.  The keybindings are loaded in load_keys_list()\n        and are pairs of (event, [keys]) where keys can be a list\n        of one or more key combinations to bind to the same event.\n        Mouse button 1 click invokes on_bindingslist_select(), which\n        allows button_new_keys to be clicked.\n\n        So, an item is selected in listbindings, which activates\n        button_new_keys, and clicking button_new_keys calls function\n        get_new_keys().  Function get_new_keys() gets the key mappings from the\n        current keyset for the binding event item that was selected.  The\n        function then displays another dialog, GetKeysDialog, with the\n        selected binding event and current keys and allows new key sequences\n        to be entered for that binding event.  If the keys aren't\n        changed, nothing happens.  If the keys are changed and the keyset\n        is a builtin, function get_new_keys_name() will be called\n        for input of a custom keyset name.  If no name is given, then the\n        change to the keybinding will abort and no updates will be made.  If\n        a custom name is entered in the prompt or if the current keyset was\n        already custom (and thus didn't require a prompt), then\n        idleConf.userCfg['keys'] is updated in function create_new_key_set()\n        with the change to the event binding.  The item listing in bindingslist\n        is updated with the new keys.  Var keybinding is also set which invokes\n        the callback function, var_changed_keybinding, to add the change to\n        the 'keys' or 'extensions' changes tracker based on the binding type.\n\n        Tk Variables:\n            keybinding: Action/key bindings.\n\n        Methods:\n            load_keys_list: Reload active set.\n            create_new_key_set: Combine active keyset and changes.\n            set_keys_type: Command for keyset_source.\n            save_new_key_set: Save to idleConf.userCfg['keys'] (is function).\n            deactivate_current_config: Remove keys bindings in editors.\n\n        Widgets for KeysPage(frame):  (*) widgets bound to self\n            frame_key_sets: LabelFrame\n                frames[0]: Frame\n                    (*)builtin_keyset_on: Radiobutton - var keyset_source\n                    (*)custom_keyset_on: Radiobutton - var keyset_source\n                    (*)builtinlist: DynOptionMenu - var builtin_name,\n                            func keybinding_selected\n                    (*)customlist: DynOptionMenu - var custom_name,\n                            func keybinding_selected\n                    (*)keys_message: Label\n                frames[1]: Frame\n                    (*)button_delete_custom_keys: Button - delete_custom_keys\n                    (*)button_save_custom_keys: Button -  save_as_new_key_set\n            frame_custom: LabelFrame\n                frame_target: Frame\n                    target_title: Label\n                    scroll_target_y: Scrollbar\n                    scroll_target_x: Scrollbar\n                    (*)bindingslist: ListBox - on_bindingslist_select\n                    (*)button_new_keys: Button - get_new_keys & ..._name\n        "
        self.builtin_name = tracers.add(StringVar(self), self.var_changed_builtin_name)
        self.custom_name = tracers.add(StringVar(self), self.var_changed_custom_name)
        self.keyset_source = tracers.add(
            BooleanVar(self), self.var_changed_keyset_source
        )
        self.keybinding = tracers.add(StringVar(self), self.var_changed_keybinding)
        frame_custom = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Custom Key Bindings "
        )
        frame_key_sets = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Key Set "
        )
        frame_target = Frame(frame_custom)
        target_title = Label(frame_target, text="Action - Key(s)")
        scroll_target_y = Scrollbar(frame_target)
        scroll_target_x = Scrollbar(frame_target, orient=HORIZONTAL)
        self.bindingslist = Listbox(
            frame_target, takefocus=FALSE, exportselection=FALSE
        )
        self.bindingslist.bind("<ButtonRelease-1>", self.on_bindingslist_select)
        scroll_target_y["command"] = self.bindingslist.yview
        scroll_target_x["command"] = self.bindingslist.xview
        self.bindingslist["yscrollcommand"] = scroll_target_y.set
        self.bindingslist["xscrollcommand"] = scroll_target_x.set
        self.button_new_keys = Button(
            frame_custom,
            text="Get New Keys for Selection",
            command=self.get_new_keys,
            state="disabled",
        )
        frames = [Frame(frame_key_sets, padding=2, borderwidth=0) for i in range(2)]
        self.builtin_keyset_on = Radiobutton(
            frames[0],
            variable=self.keyset_source,
            value=1,
            command=self.set_keys_type,
            text="Use a Built-in Key Set",
        )
        self.custom_keyset_on = Radiobutton(
            frames[0],
            variable=self.keyset_source,
            value=0,
            command=self.set_keys_type,
            text="Use a Custom Key Set",
        )
        self.builtinlist = DynOptionMenu(
            frames[0], self.builtin_name, None, command=None
        )
        self.customlist = DynOptionMenu(frames[0], self.custom_name, None, command=None)
        self.button_delete_custom_keys = Button(
            frames[1], text="Delete Custom Key Set", command=self.delete_custom_keys
        )
        self.button_save_custom_keys = Button(
            frames[1],
            text="Save as New Custom Key Set",
            command=self.save_as_new_key_set,
        )
        self.keys_message = Label(frames[0], borderwidth=2)
        frame_custom.pack(side=BOTTOM, padx=5, pady=5, expand=TRUE, fill=BOTH)
        frame_key_sets.pack(side=BOTTOM, padx=5, pady=5, fill=BOTH)
        self.button_new_keys.pack(side=BOTTOM, fill=X, padx=5, pady=5)
        frame_target.pack(side=LEFT, padx=5, pady=5, expand=TRUE, fill=BOTH)
        frame_target.columnconfigure(0, weight=1)
        frame_target.rowconfigure(1, weight=1)
        target_title.grid(row=0, column=0, columnspan=2, sticky=W)
        self.bindingslist.grid(row=1, column=0, sticky=NSEW)
        scroll_target_y.grid(row=1, column=1, sticky=NS)
        scroll_target_x.grid(row=2, column=0, sticky=EW)
        self.builtin_keyset_on.grid(row=0, column=0, sticky=(W + NS))
        self.custom_keyset_on.grid(row=1, column=0, sticky=(W + NS))
        self.builtinlist.grid(row=0, column=1, sticky=NSEW)
        self.customlist.grid(row=1, column=1, sticky=NSEW)
        self.keys_message.grid(row=0, column=2, sticky=NSEW, padx=5, pady=5)
        self.button_delete_custom_keys.pack(side=LEFT, fill=X, expand=True, padx=2)
        self.button_save_custom_keys.pack(side=LEFT, fill=X, expand=True, padx=2)
        frames[0].pack(side=TOP, fill=BOTH, expand=True)
        frames[1].pack(side=TOP, fill=X, expand=True, pady=2)

    def load_key_cfg(self):
        "Load current configuration settings for the keybinding options."
        self.keyset_source.set(
            idleConf.GetOption("main", "Keys", "default", type="bool", default=1)
        )
        current_option = idleConf.CurrentKeys()
        if self.keyset_source.get():
            item_list = idleConf.GetSectionList("default", "keys")
            item_list.sort()
            self.builtinlist.SetMenu(item_list, current_option)
            item_list = idleConf.GetSectionList("user", "keys")
            item_list.sort()
            if not item_list:
                self.custom_keyset_on.state(("disabled",))
                self.custom_name.set("- no custom keys -")
            else:
                self.customlist.SetMenu(item_list, item_list[0])
        else:
            item_list = idleConf.GetSectionList("user", "keys")
            item_list.sort()
            self.customlist.SetMenu(item_list, current_option)
            item_list = idleConf.GetSectionList("default", "keys")
            item_list.sort()
            self.builtinlist.SetMenu(item_list, idleConf.default_keys())
        self.set_keys_type()
        keyset_name = idleConf.CurrentKeys()
        self.load_keys_list(keyset_name)

    def var_changed_builtin_name(self, *params):
        "Process selection of builtin key set."
        old_keys = (
            "IDLE Classic Windows",
            "IDLE Classic Unix",
            "IDLE Classic Mac",
            "IDLE Classic OSX",
        )
        value = self.builtin_name.get()
        if value not in old_keys:
            if idleConf.GetOption("main", "Keys", "name") not in old_keys:
                changes.add_option("main", "Keys", "name", old_keys[0])
            changes.add_option("main", "Keys", "name2", value)
            self.keys_message["text"] = "New key set, see Help"
        else:
            changes.add_option("main", "Keys", "name", value)
            changes.add_option("main", "Keys", "name2", "")
            self.keys_message["text"] = ""
        self.load_keys_list(value)

    def var_changed_custom_name(self, *params):
        "Process selection of custom key set."
        value = self.custom_name.get()
        if value != "- no custom keys -":
            changes.add_option("main", "Keys", "name", value)
            self.load_keys_list(value)

    def var_changed_keyset_source(self, *params):
        "Process toggle between builtin key set and custom key set."
        value = self.keyset_source.get()
        changes.add_option("main", "Keys", "default", value)
        if value:
            self.var_changed_builtin_name()
        else:
            self.var_changed_custom_name()

    def var_changed_keybinding(self, *params):
        "Store change to a keybinding."
        value = self.keybinding.get()
        key_set = self.custom_name.get()
        event = self.bindingslist.get(ANCHOR).split()[0]
        if idleConf.IsCoreBinding(event):
            changes.add_option("keys", key_set, event, value)
        else:
            ext_name = idleConf.GetExtnNameForEvent(event)
            ext_keybind_section = ext_name + "_cfgBindings"
            changes.add_option("extensions", ext_keybind_section, event, value)

    def set_keys_type(self):
        "Set available screen options based on builtin or custom key set."
        if self.keyset_source.get():
            self.builtinlist["state"] = "normal"
            self.customlist["state"] = "disabled"
            self.button_delete_custom_keys.state(("disabled",))
        else:
            self.builtinlist["state"] = "disabled"
            self.custom_keyset_on.state(("!disabled",))
            self.customlist["state"] = "normal"
            self.button_delete_custom_keys.state(("!disabled",))

    def get_new_keys(self):
        "Handle event to change key binding for selected line.\n\n        A selection of a key/binding in the list of current\n        bindings pops up a dialog to enter a new binding.  If\n        the current key set is builtin and a binding has\n        changed, then a name for a custom key set needs to be\n        entered for the change to be applied.\n        "
        list_index = self.bindingslist.index(ANCHOR)
        binding = self.bindingslist.get(list_index)
        bind_name = binding.split()[0]
        if self.keyset_source.get():
            current_key_set_name = self.builtin_name.get()
        else:
            current_key_set_name = self.custom_name.get()
        current_bindings = idleConf.GetCurrentKeySet()
        if current_key_set_name in changes["keys"]:
            key_set_changes = changes["keys"][current_key_set_name]
            for event in key_set_changes:
                current_bindings[event] = key_set_changes[event].split()
        current_key_sequences = list(current_bindings.values())
        new_keys = GetKeysDialog(
            self, "Get New Keys", bind_name, current_key_sequences
        ).result
        if new_keys:
            if self.keyset_source.get():
                message = "Your changes will be saved as a new Custom Key Set. Enter a name for your new Custom Key Set below."
                new_keyset = self.get_new_keys_name(message)
                if not new_keyset:
                    self.bindingslist.select_set(list_index)
                    self.bindingslist.select_anchor(list_index)
                    return
                else:
                    self.create_new_key_set(new_keyset)
            self.bindingslist.delete(list_index)
            self.bindingslist.insert(list_index, ((bind_name + " - ") + new_keys))
            self.bindingslist.select_set(list_index)
            self.bindingslist.select_anchor(list_index)
            self.keybinding.set(new_keys)
        else:
            self.bindingslist.select_set(list_index)
            self.bindingslist.select_anchor(list_index)

    def get_new_keys_name(self, message):
        "Return new key set name from query popup."
        used_names = idleConf.GetSectionList("user", "keys") + idleConf.GetSectionList(
            "default", "keys"
        )
        new_keyset = SectionName(self, "New Custom Key Set", message, used_names).result
        return new_keyset

    def save_as_new_key_set(self):
        "Prompt for name of new key set and save changes using that name."
        new_keys_name = self.get_new_keys_name("New Key Set Name:")
        if new_keys_name:
            self.create_new_key_set(new_keys_name)

    def on_bindingslist_select(self, event):
        "Activate button to assign new keys to selected action."
        self.button_new_keys.state(("!disabled",))

    def create_new_key_set(self, new_key_set_name):
        "Create a new custom key set with the given name.\n\n        Copy the bindings/keys from the previously active keyset\n        to the new keyset and activate the new custom keyset.\n        "
        if self.keyset_source.get():
            prev_key_set_name = self.builtin_name.get()
        else:
            prev_key_set_name = self.custom_name.get()
        prev_keys = idleConf.GetCoreKeys(prev_key_set_name)
        new_keys = {}
        for event in prev_keys:
            event_name = event[2:(-2)]
            binding = " ".join(prev_keys[event])
            new_keys[event_name] = binding
        if prev_key_set_name in changes["keys"]:
            key_set_changes = changes["keys"][prev_key_set_name]
            for event in key_set_changes:
                new_keys[event] = key_set_changes[event]
        self.save_new_key_set(new_key_set_name, new_keys)
        custom_key_list = idleConf.GetSectionList("user", "keys")
        custom_key_list.sort()
        self.customlist.SetMenu(custom_key_list, new_key_set_name)
        self.keyset_source.set(0)
        self.set_keys_type()

    def load_keys_list(self, keyset_name):
        "Reload the list of action/key binding pairs for the active key set.\n\n        An action/key binding can be selected to change the key binding.\n        "
        reselect = False
        if self.bindingslist.curselection():
            reselect = True
            list_index = self.bindingslist.index(ANCHOR)
        keyset = idleConf.GetKeySet(keyset_name)
        bind_names = list(keyset.keys())
        bind_names.sort()
        self.bindingslist.delete(0, END)
        for bind_name in bind_names:
            key = " ".join(keyset[bind_name])
            bind_name = bind_name[2:(-2)]
            if keyset_name in changes["keys"]:
                if bind_name in changes["keys"][keyset_name]:
                    key = changes["keys"][keyset_name][bind_name]
            self.bindingslist.insert(END, ((bind_name + " - ") + key))
        if reselect:
            self.bindingslist.see(list_index)
            self.bindingslist.select_set(list_index)
            self.bindingslist.select_anchor(list_index)

    @staticmethod
    def save_new_key_set(keyset_name, keyset):
        "Save a newly created core key set.\n\n        Add keyset to idleConf.userCfg['keys'], not to disk.\n        If the keyset doesn't exist, it is created.  The\n        binding/keys are taken from the keyset argument.\n\n        keyset_name - string, the name of the new key set\n        keyset - dictionary containing the new keybindings\n        "
        idleConf.userCfg["keys"].AddSection(keyset_name)
        for event in keyset:
            value = keyset[event]
            idleConf.userCfg["keys"].SetOption(keyset_name, event, value)

    def askyesno(self, *args, **kwargs):
        return messagebox.askyesno(*args, **kwargs)

    def delete_custom_keys(self):
        "Handle event to delete a custom key set.\n\n        Applying the delete deactivates the current configuration and\n        reverts to the default.  The custom key set is permanently\n        deleted from the config file.\n        "
        keyset_name = self.custom_name.get()
        delmsg = "Are you sure you wish to delete the key set %r ?"
        if not self.askyesno("Delete Key Set", (delmsg % keyset_name), parent=self):
            return
        self.cd.deactivate_current_config()
        changes.delete_section("keys", keyset_name)
        item_list = idleConf.GetSectionList("user", "keys")
        item_list.sort()
        if not item_list:
            self.custom_keyset_on.state(("disabled",))
            self.customlist.SetMenu(item_list, "- no custom keys -")
        else:
            self.customlist.SetMenu(item_list, item_list[0])
        self.keyset_source.set(idleConf.defaultCfg["main"].Get("Keys", "default"))
        self.builtin_name.set(
            (idleConf.defaultCfg["main"].Get("Keys", "name") or idleConf.default_keys())
        )
        changes.save_all()
        self.cd.save_all_changed_extensions()
        self.cd.activate_config_changes()
        self.set_keys_type()


class GenPage(Frame):
    def __init__(self, master):
        super().__init__(master)
        self.init_validators()
        self.create_page_general()
        self.load_general_cfg()

    def init_validators(self):
        digits_or_empty_re = re.compile("[0-9]*")

        def is_digits_or_empty(s):
            "Return 's is blank or contains only digits'"
            return digits_or_empty_re.fullmatch(s) is not None

        self.digits_only = (self.register(is_digits_or_empty), "%P")

    def create_page_general(self):
        "Return frame of widgets for General tab.\n\n        Enable users to provisionally change general options. Function\n        load_general_cfg initializes tk variables and helplist using\n        idleConf.  Radiobuttons startup_shell_on and startup_editor_on\n        set var startup_edit. Radiobuttons save_ask_on and save_auto_on\n        set var autosave. Entry boxes win_width_int and win_height_int\n        set var win_width and win_height.  Setting var_name invokes the\n        default callback that adds option to changes.\n\n        Helplist: load_general_cfg loads list user_helplist with\n        name, position pairs and copies names to listbox helplist.\n        Clicking a name invokes help_source selected. Clicking\n        button_helplist_name invokes helplist_item_name, which also\n        changes user_helplist.  These functions all call\n        set_add_delete_state. All but load call update_help_changes to\n        rewrite changes['main']['HelpFiles'].\n\n        Widgets for GenPage(Frame):  (*) widgets bound to self\n            frame_window: LabelFrame\n                frame_run: Frame\n                    startup_title: Label\n                    (*)startup_editor_on: Radiobutton - startup_edit\n                    (*)startup_shell_on: Radiobutton - startup_edit\n                frame_win_size: Frame\n                    win_size_title: Label\n                    win_width_title: Label\n                    (*)win_width_int: Entry - win_width\n                    win_height_title: Label\n                    (*)win_height_int: Entry - win_height\n                frame_cursor_blink: Frame\n                    cursor_blink_title: Label\n                    (*)cursor_blink_bool: Checkbutton - cursor_blink\n                frame_autocomplete: Frame\n                    auto_wait_title: Label\n                    (*)auto_wait_int: Entry - autocomplete_wait\n                frame_paren1: Frame\n                    paren_style_title: Label\n                    (*)paren_style_type: OptionMenu - paren_style\n                frame_paren2: Frame\n                    paren_time_title: Label\n                    (*)paren_flash_time: Entry - flash_delay\n                    (*)bell_on: Checkbutton - paren_bell\n            frame_editor: LabelFrame\n                frame_save: Frame\n                    run_save_title: Label\n                    (*)save_ask_on: Radiobutton - autosave\n                    (*)save_auto_on: Radiobutton - autosave\n                frame_format: Frame\n                    format_width_title: Label\n                    (*)format_width_int: Entry - format_width\n                frame_line_numbers_default: Frame\n                    line_numbers_default_title: Label\n                    (*)line_numbers_default_bool: Checkbutton - line_numbers_default\n                frame_context: Frame\n                    context_title: Label\n                    (*)context_int: Entry - context_lines\n            frame_shell: LabelFrame\n                frame_auto_squeeze_min_lines: Frame\n                    auto_squeeze_min_lines_title: Label\n                    (*)auto_squeeze_min_lines_int: Entry - auto_squeeze_min_lines\n            frame_help: LabelFrame\n                frame_helplist: Frame\n                    frame_helplist_buttons: Frame\n                        (*)button_helplist_edit\n                        (*)button_helplist_add\n                        (*)button_helplist_remove\n                    (*)helplist: ListBox\n                    scroll_helplist: Scrollbar\n        "
        self.startup_edit = tracers.add(
            IntVar(self), ("main", "General", "editor-on-startup")
        )
        self.win_width = tracers.add(StringVar(self), ("main", "EditorWindow", "width"))
        self.win_height = tracers.add(
            StringVar(self), ("main", "EditorWindow", "height")
        )
        self.cursor_blink = tracers.add(
            BooleanVar(self), ("main", "EditorWindow", "cursor-blink")
        )
        self.autocomplete_wait = tracers.add(
            StringVar(self), ("extensions", "AutoComplete", "popupwait")
        )
        self.paren_style = tracers.add(
            StringVar(self), ("extensions", "ParenMatch", "style")
        )
        self.flash_delay = tracers.add(
            StringVar(self), ("extensions", "ParenMatch", "flash-delay")
        )
        self.paren_bell = tracers.add(
            BooleanVar(self), ("extensions", "ParenMatch", "bell")
        )
        self.auto_squeeze_min_lines = tracers.add(
            StringVar(self), ("main", "PyShell", "auto-squeeze-min-lines")
        )
        self.autosave = tracers.add(IntVar(self), ("main", "General", "autosave"))
        self.format_width = tracers.add(
            StringVar(self), ("extensions", "FormatParagraph", "max-width")
        )
        self.line_numbers_default = tracers.add(
            BooleanVar(self), ("main", "EditorWindow", "line-numbers-default")
        )
        self.context_lines = tracers.add(
            StringVar(self), ("extensions", "CodeContext", "maxlines")
        )
        frame_window = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Window Preferences"
        )
        frame_editor = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Editor Preferences"
        )
        frame_shell = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Shell Preferences"
        )
        frame_help = LabelFrame(
            self, borderwidth=2, relief=GROOVE, text=" Additional Help Sources "
        )
        frame_run = Frame(frame_window, borderwidth=0)
        startup_title = Label(frame_run, text="At Startup")
        self.startup_editor_on = Radiobutton(
            frame_run, variable=self.startup_edit, value=1, text="Open Edit Window"
        )
        self.startup_shell_on = Radiobutton(
            frame_run, variable=self.startup_edit, value=0, text="Open Shell Window"
        )
        frame_win_size = Frame(frame_window, borderwidth=0)
        win_size_title = Label(
            frame_win_size, text="Initial Window Size  (in characters)"
        )
        win_width_title = Label(frame_win_size, text="Width")
        self.win_width_int = Entry(
            frame_win_size,
            textvariable=self.win_width,
            width=3,
            validatecommand=self.digits_only,
            validate="key",
        )
        win_height_title = Label(frame_win_size, text="Height")
        self.win_height_int = Entry(
            frame_win_size,
            textvariable=self.win_height,
            width=3,
            validatecommand=self.digits_only,
            validate="key",
        )
        frame_cursor_blink = Frame(frame_window, borderwidth=0)
        cursor_blink_title = Label(frame_cursor_blink, text="Cursor Blink")
        self.cursor_blink_bool = Checkbutton(
            frame_cursor_blink, variable=self.cursor_blink, width=1
        )
        frame_autocomplete = Frame(frame_window, borderwidth=0)
        auto_wait_title = Label(
            frame_autocomplete, text="Completions Popup Wait (milliseconds)"
        )
        self.auto_wait_int = Entry(
            frame_autocomplete,
            width=6,
            textvariable=self.autocomplete_wait,
            validatecommand=self.digits_only,
            validate="key",
        )
        frame_paren1 = Frame(frame_window, borderwidth=0)
        paren_style_title = Label(frame_paren1, text="Paren Match Style")
        self.paren_style_type = OptionMenu(
            frame_paren1,
            self.paren_style,
            "expression",
            "opener",
            "parens",
            "expression",
        )
        frame_paren2 = Frame(frame_window, borderwidth=0)
        paren_time_title = Label(
            frame_paren2,
            text="Time Match Displayed (milliseconds)\n(0 is until next input)",
        )
        self.paren_flash_time = Entry(
            frame_paren2, textvariable=self.flash_delay, width=6
        )
        self.bell_on = Checkbutton(
            frame_paren2, text="Bell on Mismatch", variable=self.paren_bell
        )
        frame_save = Frame(frame_editor, borderwidth=0)
        run_save_title = Label(frame_save, text="At Start of Run (F5)  ")
        self.save_ask_on = Radiobutton(
            frame_save, variable=self.autosave, value=0, text="Prompt to Save"
        )
        self.save_auto_on = Radiobutton(
            frame_save, variable=self.autosave, value=1, text="No Prompt"
        )
        frame_format = Frame(frame_editor, borderwidth=0)
        format_width_title = Label(frame_format, text="Format Paragraph Max Width")
        self.format_width_int = Entry(
            frame_format,
            textvariable=self.format_width,
            width=4,
            validatecommand=self.digits_only,
            validate="key",
        )
        frame_line_numbers_default = Frame(frame_editor, borderwidth=0)
        line_numbers_default_title = Label(
            frame_line_numbers_default, text="Show line numbers in new windows"
        )
        self.line_numbers_default_bool = Checkbutton(
            frame_line_numbers_default, variable=self.line_numbers_default, width=1
        )
        frame_context = Frame(frame_editor, borderwidth=0)
        context_title = Label(frame_context, text="Max Context Lines :")
        self.context_int = Entry(
            frame_context,
            textvariable=self.context_lines,
            width=3,
            validatecommand=self.digits_only,
            validate="key",
        )
        frame_auto_squeeze_min_lines = Frame(frame_shell, borderwidth=0)
        auto_squeeze_min_lines_title = Label(
            frame_auto_squeeze_min_lines, text="Auto-Squeeze Min. Lines:"
        )
        self.auto_squeeze_min_lines_int = Entry(
            frame_auto_squeeze_min_lines,
            width=4,
            textvariable=self.auto_squeeze_min_lines,
            validatecommand=self.digits_only,
            validate="key",
        )
        frame_helplist = Frame(frame_help)
        frame_helplist_buttons = Frame(frame_helplist)
        self.helplist = Listbox(
            frame_helplist, height=5, takefocus=True, exportselection=FALSE
        )
        scroll_helplist = Scrollbar(frame_helplist)
        scroll_helplist["command"] = self.helplist.yview
        self.helplist["yscrollcommand"] = scroll_helplist.set
        self.helplist.bind("<ButtonRelease-1>", self.help_source_selected)
        self.button_helplist_edit = Button(
            frame_helplist_buttons,
            text="Edit",
            state="disabled",
            width=8,
            command=self.helplist_item_edit,
        )
        self.button_helplist_add = Button(
            frame_helplist_buttons, text="Add", width=8, command=self.helplist_item_add
        )
        self.button_helplist_remove = Button(
            frame_helplist_buttons,
            text="Remove",
            state="disabled",
            width=8,
            command=self.helplist_item_remove,
        )
        frame_window.pack(side=TOP, padx=5, pady=5, expand=TRUE, fill=BOTH)
        frame_editor.pack(side=TOP, padx=5, pady=5, expand=TRUE, fill=BOTH)
        frame_shell.pack(side=TOP, padx=5, pady=5, expand=TRUE, fill=BOTH)
        frame_help.pack(side=TOP, padx=5, pady=5, expand=TRUE, fill=BOTH)
        frame_run.pack(side=TOP, padx=5, pady=0, fill=X)
        startup_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.startup_shell_on.pack(side=RIGHT, anchor=W, padx=5, pady=5)
        self.startup_editor_on.pack(side=RIGHT, anchor=W, padx=5, pady=5)
        frame_win_size.pack(side=TOP, padx=5, pady=0, fill=X)
        win_size_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.win_height_int.pack(side=RIGHT, anchor=E, padx=10, pady=5)
        win_height_title.pack(side=RIGHT, anchor=E, pady=5)
        self.win_width_int.pack(side=RIGHT, anchor=E, padx=10, pady=5)
        win_width_title.pack(side=RIGHT, anchor=E, pady=5)
        frame_cursor_blink.pack(side=TOP, padx=5, pady=0, fill=X)
        cursor_blink_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.cursor_blink_bool.pack(side=LEFT, padx=5, pady=5)
        frame_autocomplete.pack(side=TOP, padx=5, pady=0, fill=X)
        auto_wait_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.auto_wait_int.pack(side=TOP, padx=10, pady=5)
        frame_paren1.pack(side=TOP, padx=5, pady=0, fill=X)
        paren_style_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.paren_style_type.pack(side=TOP, padx=10, pady=5)
        frame_paren2.pack(side=TOP, padx=5, pady=0, fill=X)
        paren_time_title.pack(side=LEFT, anchor=W, padx=5)
        self.bell_on.pack(side=RIGHT, anchor=E, padx=15, pady=5)
        self.paren_flash_time.pack(side=TOP, anchor=W, padx=15, pady=5)
        frame_save.pack(side=TOP, padx=5, pady=0, fill=X)
        run_save_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.save_auto_on.pack(side=RIGHT, anchor=W, padx=5, pady=5)
        self.save_ask_on.pack(side=RIGHT, anchor=W, padx=5, pady=5)
        frame_format.pack(side=TOP, padx=5, pady=0, fill=X)
        format_width_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.format_width_int.pack(side=TOP, padx=10, pady=5)
        frame_line_numbers_default.pack(side=TOP, padx=5, pady=0, fill=X)
        line_numbers_default_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.line_numbers_default_bool.pack(side=LEFT, padx=5, pady=5)
        frame_context.pack(side=TOP, padx=5, pady=0, fill=X)
        context_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.context_int.pack(side=TOP, padx=5, pady=5)
        frame_auto_squeeze_min_lines.pack(side=TOP, padx=5, pady=0, fill=X)
        auto_squeeze_min_lines_title.pack(side=LEFT, anchor=W, padx=5, pady=5)
        self.auto_squeeze_min_lines_int.pack(side=TOP, padx=5, pady=5)
        frame_helplist_buttons.pack(side=RIGHT, padx=5, pady=5, fill=Y)
        frame_helplist.pack(side=TOP, padx=5, pady=5, expand=TRUE, fill=BOTH)
        scroll_helplist.pack(side=RIGHT, anchor=W, fill=Y)
        self.helplist.pack(side=LEFT, anchor=E, expand=TRUE, fill=BOTH)
        self.button_helplist_edit.pack(side=TOP, anchor=W, pady=5)
        self.button_helplist_add.pack(side=TOP, anchor=W)
        self.button_helplist_remove.pack(side=TOP, anchor=W, pady=5)

    def load_general_cfg(self):
        "Load current configuration settings for the general options."
        self.startup_edit.set(
            idleConf.GetOption("main", "General", "editor-on-startup", type="bool")
        )
        self.win_width.set(
            idleConf.GetOption("main", "EditorWindow", "width", type="int")
        )
        self.win_height.set(
            idleConf.GetOption("main", "EditorWindow", "height", type="int")
        )
        self.cursor_blink.set(
            idleConf.GetOption("main", "EditorWindow", "cursor-blink", type="bool")
        )
        self.autocomplete_wait.set(
            idleConf.GetOption("extensions", "AutoComplete", "popupwait", type="int")
        )
        self.paren_style.set(idleConf.GetOption("extensions", "ParenMatch", "style"))
        self.flash_delay.set(
            idleConf.GetOption("extensions", "ParenMatch", "flash-delay", type="int")
        )
        self.paren_bell.set(idleConf.GetOption("extensions", "ParenMatch", "bell"))
        self.autosave.set(
            idleConf.GetOption("main", "General", "autosave", default=0, type="bool")
        )
        self.format_width.set(
            idleConf.GetOption("extensions", "FormatParagraph", "max-width", type="int")
        )
        self.line_numbers_default.set(
            idleConf.GetOption(
                "main", "EditorWindow", "line-numbers-default", type="bool"
            )
        )
        self.context_lines.set(
            idleConf.GetOption("extensions", "CodeContext", "maxlines", type="int")
        )
        self.auto_squeeze_min_lines.set(
            idleConf.GetOption("main", "PyShell", "auto-squeeze-min-lines", type="int")
        )
        self.user_helplist = idleConf.GetAllExtraHelpSourcesList()
        self.helplist.delete(0, "end")
        for help_item in self.user_helplist:
            self.helplist.insert(END, help_item[0])
        self.set_add_delete_state()

    def help_source_selected(self, event):
        "Handle event for selecting additional help."
        self.set_add_delete_state()

    def set_add_delete_state(self):
        "Toggle the state for the help list buttons based on list entries."
        if self.helplist.size() < 1:
            self.button_helplist_edit.state(("disabled",))
            self.button_helplist_remove.state(("disabled",))
        elif self.helplist.curselection():
            self.button_helplist_edit.state(("!disabled",))
            self.button_helplist_remove.state(("!disabled",))
        else:
            self.button_helplist_edit.state(("disabled",))
            self.button_helplist_remove.state(("disabled",))

    def helplist_item_add(self):
        "Handle add button for the help list.\n\n        Query for name and location of new help sources and add\n        them to the list.\n        "
        help_source = HelpSource(self, "New Help Source").result
        if help_source:
            self.user_helplist.append(help_source)
            self.helplist.insert(END, help_source[0])
            self.update_help_changes()

    def helplist_item_edit(self):
        "Handle edit button for the help list.\n\n        Query with existing help source information and update\n        config if the values are changed.\n        "
        item_index = self.helplist.index(ANCHOR)
        help_source = self.user_helplist[item_index]
        new_help_source = HelpSource(
            self, "Edit Help Source", menuitem=help_source[0], filepath=help_source[1]
        ).result
        if new_help_source and (new_help_source != help_source):
            self.user_helplist[item_index] = new_help_source
            self.helplist.delete(item_index)
            self.helplist.insert(item_index, new_help_source[0])
            self.update_help_changes()
            self.set_add_delete_state()

    def helplist_item_remove(self):
        "Handle remove button for the help list.\n\n        Delete the help list item from config.\n        "
        item_index = self.helplist.index(ANCHOR)
        del self.user_helplist[item_index]
        self.helplist.delete(item_index)
        self.update_help_changes()
        self.set_add_delete_state()

    def update_help_changes(self):
        "Clear and rebuild the HelpFiles section in changes"
        changes["main"]["HelpFiles"] = {}
        for num in range(1, (len(self.user_helplist) + 1)):
            changes.add_option(
                "main",
                "HelpFiles",
                str(num),
                ";".join(self.user_helplist[(num - 1)][:2]),
            )


class VarTrace:
    "Maintain Tk variables trace state."

    def __init__(self):
        "Store Tk variables and callbacks.\n\n        untraced: List of tuples (var, callback)\n            that do not have the callback attached\n            to the Tk var.\n        traced: List of tuples (var, callback) where\n            that callback has been attached to the var.\n        "
        self.untraced = []
        self.traced = []

    def clear(self):
        "Clear lists (for tests)."
        self.untraced.clear()
        self.traced.clear()

    def add(self, var, callback):
        "Add (var, callback) tuple to untraced list.\n\n        Args:\n            var: Tk variable instance.\n            callback: Either function name to be used as a callback\n                or a tuple with IdleConf config-type, section, and\n                option names used in the default callback.\n\n        Return:\n            Tk variable instance.\n        "
        if isinstance(callback, tuple):
            callback = self.make_callback(var, callback)
        self.untraced.append((var, callback))
        return var

    @staticmethod
    def make_callback(var, config):
        "Return default callback function to add values to changes instance."

        def default_callback(*params):
            "Add config values to changes instance."
            changes.add_option(*config, var.get())

        return default_callback

    def attach(self):
        "Attach callback to all vars that are not traced."
        while self.untraced:
            (var, callback) = self.untraced.pop()
            var.trace_add("write", callback)
            self.traced.append((var, callback))

    def detach(self):
        "Remove callback from traced vars."
        while self.traced:
            (var, callback) = self.traced.pop()
            var.trace_remove("write", var.trace_info()[0][1])
            self.untraced.append((var, callback))


tracers = VarTrace()
help_common = "When you click either the Apply or Ok buttons, settings in this\ndialog that are different from IDLE's default are saved in\na .idlerc directory in your home directory. Except as noted,\nthese changes apply to all versions of IDLE installed on this\nmachine. [Cancel] only cancels changes made since the last save.\n"
help_pages = {
    "Fonts/Tabs": "\nFont sample: This shows what a selection of Basic Multilingual Plane\nunicode characters look like for the current font selection.  If the\nselected font does not define a character, Tk attempts to find another\nfont that does.  Substitute glyphs depend on what is available on a\nparticular system and will not necessarily have the same size as the\nfont selected.  Line contains 20 characters up to Devanagari, 14 for\nTamil, and 10 for East Asia.\n\nHebrew and Arabic letters should display right to left, starting with\nalef, א and ا.  Arabic digits display left to right.  The\nDevanagari and Tamil lines start with digits.  The East Asian lines\nare Chinese digits, Chinese Hanzi, Korean Hangul, and Japanese\nHiragana and Katakana.\n\nYou can edit the font sample. Changes remain until IDLE is closed.\n",
    "Highlights": "\nHighlighting:\nThe IDLE Dark color theme is new in October 2015.  It can only\nbe used with older IDLE releases if it is saved as a custom\ntheme, with a different name.\n",
    "Keys": "\nKeys:\nThe IDLE Modern Unix key set is new in June 2016.  It can only\nbe used with older IDLE releases if it is saved as a custom\nkey set, with a different name.\n",
    "General": "\nGeneral:\n\nAutoComplete: Popupwait is milliseconds to wait after key char, without\ncursor movement, before popping up completion box.  Key char is '.' after\nidentifier or a '/' (or '\\' on Windows) within a string.\n\nFormatParagraph: Max-width is max chars in lines after re-formatting.\nUse with paragraphs in both strings and comment blocks.\n\nParenMatch: Style indicates what is highlighted when closer is entered:\n'opener' - opener '({[' corresponding to closer; 'parens' - both chars;\n'expression' (default) - also everything in between.  Flash-delay is how\nlong to highlight if cursor is not moved (0 means forever).\n\nCodeContext: Maxlines is the maximum number of code context lines to\ndisplay when Code Context is turned on for an editor window.\n\nShell Preferences: Auto-Squeeze Min. Lines is the minimum number of lines\nof output to automatically \"squeeze\".\n",
    "Extensions": "\nZzDummy: This extension is provided as an example for how to create and\nuse an extension.  Enable indicates whether the extension is active or\nnot; likewise enable_editor and enable_shell indicate which windows it\nwill be active on.  For this extension, z-text is the text that will be\ninserted at or removed from the beginning of the lines of selected text,\nor the current line if no selection.\n",
}


def is_int(s):
    "Return 's is blank or represents an int'"
    if not s:
        return True
    try:
        int(s)
        return True
    except ValueError:
        return False


class VerticalScrolledFrame(Frame):
    "A pure Tkinter vertically scrollable frame.\n\n    * Use the 'interior' attribute to place widgets inside the scrollable frame\n    * Construct and pack/place/grid normally\n    * This frame only allows vertical scrolling\n    "

    def __init__(self, parent, *args, **kw):
        Frame.__init__(self, parent, *args, **kw)
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(
            self,
            borderwidth=0,
            highlightthickness=0,
            yscrollcommand=vscrollbar.set,
            width=240,
        )
        canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)
        self.interior = interior = Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior, anchor=NW)

        def _configure_interior(event):
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            canvas.config(scrollregion=("0 0 %s %s" % size))

        interior.bind("<Configure>", _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())

        canvas.bind("<Configure>", _configure_canvas)
        return


if __name__ == "__main__":
    from unittest import main

    main("idlelib.idle_test.test_configdialog", verbosity=2, exit=False)
    from idlelib.idle_test.htest import run

    run(ConfigDialog)
