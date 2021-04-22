import copy
from . import ElementTree
from urllib.parse import urljoin

XINCLUDE = "{http://www.w3.org/2001/XInclude}"
XINCLUDE_INCLUDE = XINCLUDE + "include"
XINCLUDE_FALLBACK = XINCLUDE + "fallback"
DEFAULT_MAX_INCLUSION_DEPTH = 6


class FatalIncludeError(SyntaxError):
    pass


class LimitedRecursiveIncludeError(FatalIncludeError):
    pass


def default_loader(href, parse, encoding=None):
    if parse == "xml":
        with open(href, "rb") as file:
            data = ElementTree.parse(file).getroot()
    else:
        if not encoding:
            encoding = "UTF-8"
        with open(href, "r", encoding=encoding) as file:
            data = file.read()
    return data


def include(elem, loader=None, base_url=None, max_depth=DEFAULT_MAX_INCLUSION_DEPTH):
    if max_depth is None:
        max_depth = -1
    elif max_depth < 0:
        raise ValueError(
            ("expected non-negative depth or None for 'max_depth', got %r" % max_depth)
        )
    if hasattr(elem, "getroot"):
        elem = elem.getroot()
    if loader is None:
        loader = default_loader
    _include(elem, loader, base_url, max_depth, set())


def _include(elem, loader, base_url, max_depth, _parent_hrefs):
    i = 0
    while i < len(elem):
        e = elem[i]
        if e.tag == XINCLUDE_INCLUDE:
            href = e.get("href")
            if base_url:
                href = urljoin(base_url, href)
            parse = e.get("parse", "xml")
            if parse == "xml":
                if href in _parent_hrefs:
                    raise FatalIncludeError(("recursive include of %s" % href))
                if max_depth == 0:
                    raise LimitedRecursiveIncludeError(
                        ("maximum xinclude depth reached when including file %s" % href)
                    )
                _parent_hrefs.add(href)
                node = loader(href, parse)
                if node is None:
                    raise FatalIncludeError(("cannot load %r as %r" % (href, parse)))
                node = copy.copy(node)
                _include(node, loader, href, (max_depth - 1), _parent_hrefs)
                _parent_hrefs.remove(href)
                if e.tail:
                    node.tail = (node.tail or "") + e.tail
                elem[i] = node
            elif parse == "text":
                text = loader(href, parse, e.get("encoding"))
                if text is None:
                    raise FatalIncludeError(("cannot load %r as %r" % (href, parse)))
                if e.tail:
                    text += e.tail
                if i:
                    node = elem[(i - 1)]
                    node.tail = (node.tail or "") + text
                else:
                    elem.text = (elem.text or "") + text
                del elem[i]
                continue
            else:
                raise FatalIncludeError(
                    ("unknown parse type in xi:include tag (%r)" % parse)
                )
        elif e.tag == XINCLUDE_FALLBACK:
            raise FatalIncludeError(
                ("xi:fallback tag must be child of xi:include (%r)" % e.tag)
            )
        else:
            _include(e, loader, base_url, max_depth, _parent_hrefs)
        i += 1
