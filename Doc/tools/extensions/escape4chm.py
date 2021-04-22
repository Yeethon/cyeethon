"\nEscape the `body` part of .chm source file to 7-bit ASCII, to fix visual\neffect on some MBCS Windows systems.\n\nhttps://bugs.python.org/issue32174\n"
import re
from html.entities import codepoint2name
from sphinx.util.logging import getLogger


def _process(string):
    def escape(matchobj):
        codepoint = ord(matchobj.group(0))
        name = codepoint2name.get(codepoint)
        if name is None:
            return "&#%d;" % codepoint
        else:
            return "&%s;" % name

    return re.sub("[^\\x00-\\x7F]", escape, string)


def escape_for_chm(app, pagename, templatename, context, doctree):
    if getattr(app.builder, "name", "") != "htmlhelp":
        return
    body = context.get("body")
    if body is not None:
        context["body"] = _process(body)


def fixup_keywords(app, exception):
    if (getattr(app.builder, "name", "") != "htmlhelp") or exception:
        return
    getLogger(__name__).info("fixing HTML escapes in keywords file...")
    outdir = app.builder.outdir
    outname = app.builder.config.htmlhelp_basename
    with app.builder.open_file(outdir, (outname + ".hhk"), "r") as f:
        index = f.read()
    with app.builder.open_file(outdir, (outname + ".hhk"), "w") as f:
        f.write(index.replace("&#x27;", "&#39;"))


def setup(app):
    app.connect("html-page-context", escape_for_chm)
    app.connect("build-finished", fixup_keywords)
    return {"version": "1.0", "parallel_read_safe": True}
