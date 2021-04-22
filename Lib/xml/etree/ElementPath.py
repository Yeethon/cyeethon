import re

xpath_tokenizer_re = re.compile(
    "('[^']*'|\\\"[^\\\"]*\\\"|::|//?|\\.\\.|\\(\\)|!=|[/.*:\\[\\]\\(\\)@=])|((?:\\{[^}]+\\})?[^/\\[\\]\\(\\)@!=\\s]+)|\\s+"
)


def xpath_tokenizer(pattern, namespaces=None):
    default_namespace = namespaces.get("") if namespaces else None
    parsing_attribute = False
    for token in xpath_tokenizer_re.findall(pattern):
        (ttype, tag) = token
        if tag and (tag[0] != "{"):
            if ":" in tag:
                (prefix, uri) = tag.split(":", 1)
                try:
                    if not namespaces:
                        raise KeyError
                    (yield (ttype, ("{%s}%s" % (namespaces[prefix], uri))))
                except KeyError:
                    raise SyntaxError(
                        ("prefix %r not found in prefix map" % prefix)
                    ) from None
            elif default_namespace and (not parsing_attribute):
                (yield (ttype, ("{%s}%s" % (default_namespace, tag))))
            else:
                (yield token)
            parsing_attribute = False
        else:
            (yield token)
            parsing_attribute = ttype == "@"


def get_parent_map(context):
    parent_map = context.parent_map
    if parent_map is None:
        context.parent_map = parent_map = {}
        for p in context.root.iter():
            for e in p:
                parent_map[e] = p
    return parent_map


def _is_wildcard_tag(tag):
    return (tag[:3] == "{*}") or (tag[(-2):] == "}*")


def _prepare_tag(tag):
    (_isinstance, _str) = (isinstance, str)
    if tag == "{*}*":

        def select(context, result):
            for elem in result:
                if _isinstance(elem.tag, _str):
                    (yield elem)

    elif tag == "{}*":

        def select(context, result):
            for elem in result:
                el_tag = elem.tag
                if _isinstance(el_tag, _str) and (el_tag[0] != "{"):
                    (yield elem)

    elif tag[:3] == "{*}":
        suffix = tag[2:]
        no_ns = slice((-len(suffix)), None)
        tag = tag[3:]

        def select(context, result):
            for elem in result:
                el_tag = elem.tag
                if (el_tag == tag) or (
                    _isinstance(el_tag, _str) and (el_tag[no_ns] == suffix)
                ):
                    (yield elem)

    elif tag[(-2):] == "}*":
        ns = tag[:(-1)]
        ns_only = slice(None, len(ns))

        def select(context, result):
            for elem in result:
                el_tag = elem.tag
                if _isinstance(el_tag, _str) and (el_tag[ns_only] == ns):
                    (yield elem)

    else:
        raise RuntimeError(f"internal parser error, got {tag}")
    return select


def prepare_child(next, token):
    tag = token[1]
    if _is_wildcard_tag(tag):
        select_tag = _prepare_tag(tag)

        def select(context, result):
            def select_child(result):
                for elem in result:
                    (yield from elem)

            return select_tag(context, select_child(result))

    else:
        if tag[:2] == "{}":
            tag = tag[2:]

        def select(context, result):
            for elem in result:
                for e in elem:
                    if e.tag == tag:
                        (yield e)

    return select


def prepare_star(next, token):
    def select(context, result):
        for elem in result:
            (yield from elem)

    return select


def prepare_self(next, token):
    def select(context, result):
        (yield from result)

    return select


def prepare_descendant(next, token):
    try:
        token = next()
    except StopIteration:
        return
    if token[0] == "*":
        tag = "*"
    elif not token[0]:
        tag = token[1]
    else:
        raise SyntaxError("invalid descendant")
    if _is_wildcard_tag(tag):
        select_tag = _prepare_tag(tag)

        def select(context, result):
            def select_child(result):
                for elem in result:
                    for e in elem.iter():
                        if e is not elem:
                            (yield e)

            return select_tag(context, select_child(result))

    else:
        if tag[:2] == "{}":
            tag = tag[2:]

        def select(context, result):
            for elem in result:
                for e in elem.iter(tag):
                    if e is not elem:
                        (yield e)

    return select


def prepare_parent(next, token):
    def select(context, result):
        parent_map = get_parent_map(context)
        result_map = {}
        for elem in result:
            if elem in parent_map:
                parent = parent_map[elem]
                if parent not in result_map:
                    result_map[parent] = None
                    (yield parent)

    return select


def prepare_predicate(next, token):
    signature = []
    predicate = []
    while 1:
        try:
            token = next()
        except StopIteration:
            return
        if token[0] == "]":
            break
        if token == ("", ""):
            continue
        if token[0] and (token[0][:1] in "'\""):
            token = ("'", token[0][1:(-1)])
        signature.append((token[0] or "-"))
        predicate.append(token[1])
    signature = "".join(signature)
    if signature == "@-":
        key = predicate[1]

        def select(context, result):
            for elem in result:
                if elem.get(key) is not None:
                    (yield elem)

        return select
    if (signature == "@-='") or (signature == "@-!='"):
        key = predicate[1]
        value = predicate[(-1)]

        def select(context, result):
            for elem in result:
                if elem.get(key) == value:
                    (yield elem)

        def select_negated(context, result):
            for elem in result:
                if ((attr_value := elem.get(key)) is not None) and (
                    attr_value != value
                ):
                    (yield elem)

        return select_negated if ("!=" in signature) else select
    if (signature == "-") and (not re.match("\\-?\\d+$", predicate[0])):
        tag = predicate[0]

        def select(context, result):
            for elem in result:
                if elem.find(tag) is not None:
                    (yield elem)

        return select
    if (
        (signature == ".='")
        or (signature == ".!='")
        or (
            ((signature == "-='") or (signature == "-!='"))
            and (not re.match("\\-?\\d+$", predicate[0]))
        )
    ):
        tag = predicate[0]
        value = predicate[(-1)]
        if tag:

            def select(context, result):
                for elem in result:
                    for e in elem.findall(tag):
                        if "".join(e.itertext()) == value:
                            (yield elem)
                            break

            def select_negated(context, result):
                for elem in result:
                    for e in elem.iterfind(tag):
                        if "".join(e.itertext()) != value:
                            (yield elem)
                            break

        else:

            def select(context, result):
                for elem in result:
                    if "".join(elem.itertext()) == value:
                        (yield elem)

            def select_negated(context, result):
                for elem in result:
                    if "".join(elem.itertext()) != value:
                        (yield elem)

        return select_negated if ("!=" in signature) else select
    if (signature == "-") or (signature == "-()") or (signature == "-()-"):
        if signature == "-":
            index = int(predicate[0]) - 1
            if index < 0:
                raise SyntaxError("XPath position >= 1 expected")
        else:
            if predicate[0] != "last":
                raise SyntaxError("unsupported function")
            if signature == "-()-":
                try:
                    index = int(predicate[2]) - 1
                except ValueError:
                    raise SyntaxError("unsupported expression")
                if index > (-2):
                    raise SyntaxError("XPath offset from last() must be negative")
            else:
                index = -1

        def select(context, result):
            parent_map = get_parent_map(context)
            for elem in result:
                try:
                    parent = parent_map[elem]
                    elems = list(parent.findall(elem.tag))
                    if elems[index] is elem:
                        (yield elem)
                except (IndexError, KeyError):
                    pass

        return select
    raise SyntaxError("invalid predicate")


ops = {
    "": prepare_child,
    "*": prepare_star,
    ".": prepare_self,
    "..": prepare_parent,
    "//": prepare_descendant,
    "[": prepare_predicate,
}
_cache = {}


class _SelectorContext:
    parent_map = None

    def __init__(self, root):
        self.root = root


def iterfind(elem, path, namespaces=None):
    if path[(-1):] == "/":
        path = path + "*"
    cache_key = (path,)
    if namespaces:
        cache_key += tuple(sorted(namespaces.items()))
    try:
        selector = _cache[cache_key]
    except KeyError:
        if len(_cache) > 100:
            _cache.clear()
        if path[:1] == "/":
            raise SyntaxError("cannot use absolute path on element")
        next = iter(xpath_tokenizer(path, namespaces)).__next__
        try:
            token = next()
        except StopIteration:
            return
        selector = []
        while 1:
            try:
                selector.append(ops[token[0]](next, token))
            except StopIteration:
                raise SyntaxError("invalid path") from None
            try:
                token = next()
                if token[0] == "/":
                    token = next()
            except StopIteration:
                break
        _cache[cache_key] = selector
    result = [elem]
    context = _SelectorContext(elem)
    for select in selector:
        result = select(context, result)
    return result


def find(elem, path, namespaces=None):
    return next(iterfind(elem, path, namespaces), None)


def findall(elem, path, namespaces=None):
    return list(iterfind(elem, path, namespaces))


def findtext(elem, path, default=None, namespaces=None):
    try:
        elem = next(iterfind(elem, path, namespaces))
        return elem.text or ""
    except StopIteration:
        return default
