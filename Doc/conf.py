import sys, os, time

sys.path.append(os.path.abspath("tools/extensions"))
sys.path.append(os.path.abspath("includes"))
extensions = [
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "pyspecific",
    "c_annotations",
    "escape4chm",
    "asdl_highlight",
    "peg_highlight",
    "glossary_search",
]
doctest_global_setup = (
    "\ntry:\n    import _tkinter\nexcept ImportError:\n    _tkinter = None\n"
)
manpages_url = "https://manpages.debian.org/{path}"
project = "Python"
copyright = "2001-%s, Python Software Foundation" % time.strftime("%Y")
import patchlevel

(version, release) = patchlevel.get_version_info()
today = ""
today_fmt = "%B %d, %Y"
highlight_language = "python3"
needs_sphinx = "1.8"
exclude_patterns = ["venv/*", "README.rst"]
venvdir = os.getenv("VENVDIR")
if venvdir is not None:
    exclude_patterns.append((venvdir + "/*"))
smartquotes_excludes = {
    "languages": ["ja", "fr", "zh_TW", "zh_CN"],
    "builders": ["man", "text"],
}
master_doc = "contents"
html_theme = "python_docs_theme"
html_theme_path = ["tools"]
html_theme_options = {
    "collapsiblesidebar": True,
    "issues_url": "https://docs.python.org/3/bugs.html",
    "root_include_title": False,
}
html_short_title = "%s Documentation" % release
html_last_updated_fmt = "%b %d, %Y"
templates_path = ["tools/templates"]
html_sidebars = {
    "**": ["localtoc.html", "relations.html", "customsourcelink.html"],
    "index": ["indexsidebar.html"],
}
html_additional_pages = {"download": "download.html", "index": "indexcontent.html"}
html_use_opensearch = "https://docs.python.org/" + version
html_static_path = ["tools/static"]
htmlhelp_basename = "python" + release.replace(".", "")
html_split_index = True
latex_engine = "xelatex"
latex_elements = {}
latex_elements[
    "preamble"
] = "\n\\authoraddress{\n  \\sphinxstrong{Python Software Foundation}\\\\\n  Email: \\sphinxemail{docs@python.org}\n}\n\\let\\Verbatim=\\OriginalVerbatim\n\\let\\endVerbatim=\\endOriginalVerbatim\n\\setcounter{tocdepth}{2}\n"
latex_elements["papersize"] = "a4"
latex_elements["pointsize"] = "10pt"
_stdauthor = "Guido van Rossum\\\\and the Python development team"
latex_documents = [
    ("c-api/index", "c-api.tex", "The Python/C API", _stdauthor, "manual"),
    (
        "distributing/index",
        "distributing.tex",
        "Distributing Python Modules",
        _stdauthor,
        "manual",
    ),
    (
        "extending/index",
        "extending.tex",
        "Extending and Embedding Python",
        _stdauthor,
        "manual",
    ),
    (
        "installing/index",
        "installing.tex",
        "Installing Python Modules",
        _stdauthor,
        "manual",
    ),
    (
        "library/index",
        "library.tex",
        "The Python Library Reference",
        _stdauthor,
        "manual",
    ),
    (
        "reference/index",
        "reference.tex",
        "The Python Language Reference",
        _stdauthor,
        "manual",
    ),
    ("tutorial/index", "tutorial.tex", "Python Tutorial", _stdauthor, "manual"),
    ("using/index", "using.tex", "Python Setup and Usage", _stdauthor, "manual"),
    ("faq/index", "faq.tex", "Python Frequently Asked Questions", _stdauthor, "manual"),
    (
        ("whatsnew/" + version),
        "whatsnew.tex",
        "What's New in Python",
        "A. M. Kuchling",
        "howto",
    ),
]
latex_documents.extend(
    (
        (
            ("howto/" + fn[:(-4)]),
            (("howto-" + fn[:(-4)]) + ".tex"),
            "",
            _stdauthor,
            "howto",
        )
        for fn in os.listdir("howto")
        if (fn.endswith(".rst") and (fn != "index.rst"))
    )
)
latex_appendices = ["glossary", "about", "license", "copyright"]
epub_author = "Python Documentation Authors"
epub_publisher = "Python Software Foundation"
coverage_ignore_modules = ["[T|t][k|K]", "Tix", "distutils.*"]
coverage_ignore_functions = ["test($|_)"]
coverage_ignore_classes = []
coverage_c_path = ["../Include/*.h"]
coverage_c_regexes = {
    "cfunction": "^PyAPI_FUNC\\(.*\\)\\s+([^_][\\w_]+)",
    "data": "^PyAPI_DATA\\(.*\\)\\s+([^_][\\w_]+)",
    "macro": "^#define ([^_][\\w_]+)\\(.*\\)[\\s|\\\\]",
}
coverage_ignore_c_items = {}
linkcheck_ignore = [
    "https://bugs.python.org/(issue)?\\d+",
    "http://www.python.org/dev/peps/pep-\\d+",
]
refcount_file = "data/refcounts.dat"
c_allow_pre_v3 = True
c_warn_on_allowed_pre_v3 = False
strip_signature_backslash = True
