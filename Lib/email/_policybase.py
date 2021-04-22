"Policy framework for the email package.\n\nAllows fine grained feature control of how the package parses and emits data.\n"
import abc
from email import header
from email import charset as _charset
from email.utils import _has_surrogates

__all__ = ["Policy", "Compat32", "compat32"]


class _PolicyBase:
    "Policy Object basic framework.\n\n    This class is useless unless subclassed.  A subclass should define\n    class attributes with defaults for any values that are to be\n    managed by the Policy object.  The constructor will then allow\n    non-default values to be set for these attributes at instance\n    creation time.  The instance will be callable, taking these same\n    attributes keyword arguments, and returning a new instance\n    identical to the called instance except for those values changed\n    by the keyword arguments.  Instances may be added, yielding new\n    instances with any non-default values from the right hand\n    operand overriding those in the left hand operand.  That is,\n\n        A + B == A(<non-default values of B>)\n\n    The repr of an instance can be used to reconstruct the object\n    if and only if the repr of the values can be used to reconstruct\n    those values.\n\n    "

    def __init__(self, **kw):
        "Create new Policy, possibly overriding some defaults.\n\n        See class docstring for a list of overridable attributes.\n\n        "
        for (name, value) in kw.items():
            if hasattr(self, name):
                super(_PolicyBase, self).__setattr__(name, value)
            else:
                raise TypeError(
                    "{!r} is an invalid keyword argument for {}".format(
                        name, self.__class__.__name__
                    )
                )

    def __repr__(self):
        args = [
            "{}={!r}".format(name, value) for (name, value) in self.__dict__.items()
        ]
        return "{}({})".format(self.__class__.__name__, ", ".join(args))

    def clone(self, **kw):
        "Return a new instance with specified attributes changed.\n\n        The new instance has the same attribute values as the current object,\n        except for the changes passed in as keyword arguments.\n\n        "
        newpolicy = self.__class__.__new__(self.__class__)
        for (attr, value) in self.__dict__.items():
            object.__setattr__(newpolicy, attr, value)
        for (attr, value) in kw.items():
            if not hasattr(self, attr):
                raise TypeError(
                    "{!r} is an invalid keyword argument for {}".format(
                        attr, self.__class__.__name__
                    )
                )
            object.__setattr__(newpolicy, attr, value)
        return newpolicy

    def __setattr__(self, name, value):
        if hasattr(self, name):
            msg = "{!r} object attribute {!r} is read-only"
        else:
            msg = "{!r} object has no attribute {!r}"
        raise AttributeError(msg.format(self.__class__.__name__, name))

    def __add__(self, other):
        "Non-default values from right operand override those from left.\n\n        The object returned is a new instance of the subclass.\n\n        "
        return self.clone(**other.__dict__)


def _append_doc(doc, added_doc):
    doc = doc.rsplit("\n", 1)[0]
    added_doc = added_doc.split("\n", 1)[1]
    return (doc + "\n") + added_doc


def _extend_docstrings(cls):
    if cls.__doc__ and cls.__doc__.startswith("+"):
        cls.__doc__ = _append_doc(cls.__bases__[0].__doc__, cls.__doc__)
    for (name, attr) in cls.__dict__.items():
        if attr.__doc__ and attr.__doc__.startswith("+"):
            for c in (c for base in cls.__bases__ for c in base.mro()):
                doc = getattr(getattr(c, name), "__doc__")
                if doc:
                    attr.__doc__ = _append_doc(doc, attr.__doc__)
                    break
    return cls


class Policy(_PolicyBase, metaclass=abc.ABCMeta):
    "Controls for how messages are interpreted and formatted.\n\n    Most of the classes and many of the methods in the email package accept\n    Policy objects as parameters.  A Policy object contains a set of values and\n    functions that control how input is interpreted and how output is rendered.\n    For example, the parameter 'raise_on_defect' controls whether or not an RFC\n    violation results in an error being raised or not, while 'max_line_length'\n    controls the maximum length of output lines when a Message is serialized.\n\n    Any valid attribute may be overridden when a Policy is created by passing\n    it as a keyword argument to the constructor.  Policy objects are immutable,\n    but a new Policy object can be created with only certain values changed by\n    calling the Policy instance with keyword arguments.  Policy objects can\n    also be added, producing a new Policy object in which the non-default\n    attributes set in the right hand operand overwrite those specified in the\n    left operand.\n\n    Settable attributes:\n\n    raise_on_defect     -- If true, then defects should be raised as errors.\n                           Default: False.\n\n    linesep             -- string containing the value to use as separation\n                           between output lines.  Default '\\n'.\n\n    cte_type            -- Type of allowed content transfer encodings\n\n                           7bit  -- ASCII only\n                           8bit  -- Content-Transfer-Encoding: 8bit is allowed\n\n                           Default: 8bit.  Also controls the disposition of\n                           (RFC invalid) binary data in headers; see the\n                           documentation of the binary_fold method.\n\n    max_line_length     -- maximum length of lines, excluding 'linesep',\n                           during serialization.  None or 0 means no line\n                           wrapping is done.  Default is 78.\n\n    mangle_from_        -- a flag that, when True escapes From_ lines in the\n                           body of the message by putting a `>' in front of\n                           them. This is used when the message is being\n                           serialized by a generator. Default: True.\n\n    message_factory     -- the class to use to create new message objects.\n                           If the value is None, the default is Message.\n\n    "
    raise_on_defect = False
    linesep = "\n"
    cte_type = "8bit"
    max_line_length = 78
    mangle_from_ = False
    message_factory = None

    def handle_defect(self, obj, defect):
        "Based on policy, either raise defect or call register_defect.\n\n            handle_defect(obj, defect)\n\n        defect should be a Defect subclass, but in any case must be an\n        Exception subclass.  obj is the object on which the defect should be\n        registered if it is not raised.  If the raise_on_defect is True, the\n        defect is raised as an error, otherwise the object and the defect are\n        passed to register_defect.\n\n        This method is intended to be called by parsers that discover defects.\n        The email package parsers always call it with Defect instances.\n\n        "
        if self.raise_on_defect:
            raise defect
        self.register_defect(obj, defect)

    def register_defect(self, obj, defect):
        "Record 'defect' on 'obj'.\n\n        Called by handle_defect if raise_on_defect is False.  This method is\n        part of the Policy API so that Policy subclasses can implement custom\n        defect handling.  The default implementation calls the append method of\n        the defects attribute of obj.  The objects used by the email package by\n        default that get passed to this method will always have a defects\n        attribute with an append method.\n\n        "
        obj.defects.append(defect)

    def header_max_count(self, name):
        "Return the maximum allowed number of headers named 'name'.\n\n        Called when a header is added to a Message object.  If the returned\n        value is not 0 or None, and there are already a number of headers with\n        the name 'name' equal to the value returned, a ValueError is raised.\n\n        Because the default behavior of Message's __setitem__ is to append the\n        value to the list of headers, it is easy to create duplicate headers\n        without realizing it.  This method allows certain headers to be limited\n        in the number of instances of that header that may be added to a\n        Message programmatically.  (The limit is not observed by the parser,\n        which will faithfully produce as many headers as exist in the message\n        being parsed.)\n\n        The default implementation returns None for all header names.\n        "
        return None

    @abc.abstractmethod
    def header_source_parse(self, sourcelines):
        "Given a list of linesep terminated strings constituting the lines of\n        a single header, return the (name, value) tuple that should be stored\n        in the model.  The input lines should retain their terminating linesep\n        characters.  The lines passed in by the email package may contain\n        surrogateescaped binary data.\n        "
        raise NotImplementedError

    @abc.abstractmethod
    def header_store_parse(self, name, value):
        "Given the header name and the value provided by the application\n        program, return the (name, value) that should be stored in the model.\n        "
        raise NotImplementedError

    @abc.abstractmethod
    def header_fetch_parse(self, name, value):
        "Given the header name and the value from the model, return the value\n        to be returned to the application program that is requesting that\n        header.  The value passed in by the email package may contain\n        surrogateescaped binary data if the lines were parsed by a BytesParser.\n        The returned value should not contain any surrogateescaped data.\n\n        "
        raise NotImplementedError

    @abc.abstractmethod
    def fold(self, name, value):
        "Given the header name and the value from the model, return a string\n        containing linesep characters that implement the folding of the header\n        according to the policy controls.  The value passed in by the email\n        package may contain surrogateescaped binary data if the lines were\n        parsed by a BytesParser.  The returned value should not contain any\n        surrogateescaped data.\n\n        "
        raise NotImplementedError

    @abc.abstractmethod
    def fold_binary(self, name, value):
        "Given the header name and the value from the model, return binary\n        data containing linesep characters that implement the folding of the\n        header according to the policy controls.  The value passed in by the\n        email package may contain surrogateescaped binary data.\n\n        "
        raise NotImplementedError


@_extend_docstrings
class Compat32(Policy):
    "+\n    This particular policy is the backward compatibility Policy.  It\n    replicates the behavior of the email package version 5.1.\n    "
    mangle_from_ = True

    def _sanitize_header(self, name, value):
        if not isinstance(value, str):
            return value
        if _has_surrogates(value):
            return header.Header(value, charset=_charset.UNKNOWN8BIT, header_name=name)
        else:
            return value

    def header_source_parse(self, sourcelines):
        "+\n        The name is parsed as everything up to the ':' and returned unmodified.\n        The value is determined by stripping leading whitespace off the\n        remainder of the first line, joining all subsequent lines together, and\n        stripping any trailing carriage return or linefeed characters.\n\n        "
        (name, value) = sourcelines[0].split(":", 1)
        value = value.lstrip(" \t") + "".join(sourcelines[1:])
        return (name, value.rstrip("\r\n"))

    def header_store_parse(self, name, value):
        "+\n        The name and value are returned unmodified.\n        "
        return (name, value)

    def header_fetch_parse(self, name, value):
        "+\n        If the value contains binary data, it is converted into a Header object\n        using the unknown-8bit charset.  Otherwise it is returned unmodified.\n        "
        return self._sanitize_header(name, value)

    def fold(self, name, value):
        "+\n        Headers are folded using the Header folding algorithm, which preserves\n        existing line breaks in the value, and wraps each resulting line to the\n        max_line_length.  Non-ASCII binary data are CTE encoded using the\n        unknown-8bit charset.\n\n        "
        return self._fold(name, value, sanitize=True)

    def fold_binary(self, name, value):
        "+\n        Headers are folded using the Header folding algorithm, which preserves\n        existing line breaks in the value, and wraps each resulting line to the\n        max_line_length.  If cte_type is 7bit, non-ascii binary data is CTE\n        encoded using the unknown-8bit charset.  Otherwise the original source\n        header is used, with its existing line breaks and/or binary data.\n\n        "
        folded = self._fold(name, value, sanitize=(self.cte_type == "7bit"))
        return folded.encode("ascii", "surrogateescape")

    def _fold(self, name, value, sanitize):
        parts = []
        parts.append(("%s: " % name))
        if isinstance(value, str):
            if _has_surrogates(value):
                if sanitize:
                    h = header.Header(
                        value, charset=_charset.UNKNOWN8BIT, header_name=name
                    )
                else:
                    parts.append(value)
                    h = None
            else:
                h = header.Header(value, header_name=name)
        else:
            h = value
        if h is not None:
            maxlinelen = 0
            if self.max_line_length is not None:
                maxlinelen = self.max_line_length
            parts.append(h.encode(linesep=self.linesep, maxlinelen=maxlinelen))
        parts.append(self.linesep)
        return "".join(parts)


compat32 = Compat32()
