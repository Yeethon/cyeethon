"Basic message object for the email package object model."
__all__ = ["Message", "EmailMessage"]
import re
import uu
import quopri
from io import BytesIO, StringIO
from email import utils
from email import errors
from email._policybase import Policy, compat32
from email import charset as _charset
from email._encoded_words import decode_b

Charset = _charset.Charset
SEMISPACE = "; "
tspecials = re.compile('[ \\(\\)<>@,;:\\\\"/\\[\\]\\?=]')


def _splitparam(param):
    (a, sep, b) = str(param).partition(";")
    if not sep:
        return (a.strip(), None)
    return (a.strip(), b.strip())


def _formatparam(param, value=None, quote=True):
    "Convenience function to format and return a key=value pair.\n\n    This will quote the value if needed or if quote is true.  If value is a\n    three tuple (charset, language, value), it will be encoded according\n    to RFC2231 rules.  If it contains non-ascii characters it will likewise\n    be encoded according to RFC2231 rules, using the utf-8 charset and\n    a null language.\n    "
    if (value is not None) and (len(value) > 0):
        if isinstance(value, tuple):
            param += "*"
            value = utils.encode_rfc2231(value[2], value[0], value[1])
            return "%s=%s" % (param, value)
        else:
            try:
                value.encode("ascii")
            except UnicodeEncodeError:
                param += "*"
                value = utils.encode_rfc2231(value, "utf-8", "")
                return "%s=%s" % (param, value)
        if quote or tspecials.search(value):
            return '%s="%s"' % (param, utils.quote(value))
        else:
            return "%s=%s" % (param, value)
    else:
        return param


def _parseparam(s):
    s = ";" + str(s)
    plist = []
    while s[:1] == ";":
        s = s[1:]
        end = s.find(";")
        while (end > 0) and ((s.count('"', 0, end) - s.count('\\"', 0, end)) % 2):
            end = s.find(";", (end + 1))
        if end < 0:
            end = len(s)
        f = s[:end]
        if "=" in f:
            i = f.index("=")
            f = (f[:i].strip().lower() + "=") + f[(i + 1) :].strip()
        plist.append(f.strip())
        s = s[end:]
    return plist


def _unquotevalue(value):
    if isinstance(value, tuple):
        return (value[0], value[1], utils.unquote(value[2]))
    else:
        return utils.unquote(value)


class Message:
    "Basic message object.\n\n    A message object is defined as something that has a bunch of RFC 2822\n    headers and a payload.  It may optionally have an envelope header\n    (a.k.a. Unix-From or From_ header).  If the message is a container (i.e. a\n    multipart or a message/rfc822), then the payload is a list of Message\n    objects, otherwise it is a string.\n\n    Message objects implement part of the `mapping' interface, which assumes\n    there is exactly one occurrence of the header per message.  Some headers\n    do in fact appear multiple times (e.g. Received) and for those headers,\n    you must use the explicit API to set or get all the headers.  Not all of\n    the mapping methods are implemented.\n    "

    def __init__(self, policy=compat32):
        self.policy = policy
        self._headers = []
        self._unixfrom = None
        self._payload = None
        self._charset = None
        self.preamble = self.epilogue = None
        self.defects = []
        self._default_type = "text/plain"

    def __str__(self):
        "Return the entire formatted message as a string.\n        "
        return self.as_string()

    def as_string(self, unixfrom=False, maxheaderlen=0, policy=None):
        "Return the entire formatted message as a string.\n\n        Optional 'unixfrom', when true, means include the Unix From_ envelope\n        header.  For backward compatibility reasons, if maxheaderlen is\n        not specified it defaults to 0, so you must override it explicitly\n        if you want a different maxheaderlen.  'policy' is passed to the\n        Generator instance used to serialize the message; if it is not\n        specified the policy associated with the message instance is used.\n\n        If the message object contains binary data that is not encoded\n        according to RFC standards, the non-compliant data will be replaced by\n        unicode \"unknown character\" code points.\n        "
        from email.generator import Generator

        policy = self.policy if (policy is None) else policy
        fp = StringIO()
        g = Generator(fp, mangle_from_=False, maxheaderlen=maxheaderlen, policy=policy)
        g.flatten(self, unixfrom=unixfrom)
        return fp.getvalue()

    def __bytes__(self):
        "Return the entire formatted message as a bytes object.\n        "
        return self.as_bytes()

    def as_bytes(self, unixfrom=False, policy=None):
        "Return the entire formatted message as a bytes object.\n\n        Optional 'unixfrom', when true, means include the Unix From_ envelope\n        header.  'policy' is passed to the BytesGenerator instance used to\n        serialize the message; if not specified the policy associated with\n        the message instance is used.\n        "
        from email.generator import BytesGenerator

        policy = self.policy if (policy is None) else policy
        fp = BytesIO()
        g = BytesGenerator(fp, mangle_from_=False, policy=policy)
        g.flatten(self, unixfrom=unixfrom)
        return fp.getvalue()

    def is_multipart(self):
        "Return True if the message consists of multiple parts."
        return isinstance(self._payload, list)

    def set_unixfrom(self, unixfrom):
        self._unixfrom = unixfrom

    def get_unixfrom(self):
        return self._unixfrom

    def attach(self, payload):
        "Add the given payload to the current payload.\n\n        The current payload will always be a list of objects after this method\n        is called.  If you want to set the payload to a scalar object, use\n        set_payload() instead.\n        "
        if self._payload is None:
            self._payload = [payload]
        else:
            try:
                self._payload.append(payload)
            except AttributeError:
                raise TypeError(
                    "Attach is not valid on a message with a non-multipart payload"
                )

    def get_payload(self, i=None, decode=False):
        "Return a reference to the payload.\n\n        The payload will either be a list object or a string.  If you mutate\n        the list object, you modify the message's payload in place.  Optional\n        i returns that index into the payload.\n\n        Optional decode is a flag indicating whether the payload should be\n        decoded or not, according to the Content-Transfer-Encoding header\n        (default is False).\n\n        When True and the message is not a multipart, the payload will be\n        decoded if this header's value is `quoted-printable' or `base64'.  If\n        some other encoding is used, or the header is missing, or if the\n        payload has bogus data (i.e. bogus base64 or uuencoded data), the\n        payload is returned as-is.\n\n        If the message is a multipart and the decode flag is True, then None\n        is returned.\n        "
        if self.is_multipart():
            if decode:
                return None
            if i is None:
                return self._payload
            else:
                return self._payload[i]
        if (i is not None) and (not isinstance(self._payload, list)):
            raise TypeError(("Expected list, got %s" % type(self._payload)))
        payload = self._payload
        cte = str(self.get("content-transfer-encoding", "")).lower()
        if isinstance(payload, str):
            if utils._has_surrogates(payload):
                bpayload = payload.encode("ascii", "surrogateescape")
                if not decode:
                    try:
                        payload = bpayload.decode(
                            self.get_param("charset", "ascii"), "replace"
                        )
                    except LookupError:
                        payload = bpayload.decode("ascii", "replace")
            elif decode:
                try:
                    bpayload = payload.encode("ascii")
                except UnicodeError:
                    bpayload = payload.encode("raw-unicode-escape")
        if not decode:
            return payload
        if cte == "quoted-printable":
            return quopri.decodestring(bpayload)
        elif cte == "base64":
            (value, defects) = decode_b(b"".join(bpayload.splitlines()))
            for defect in defects:
                self.policy.handle_defect(self, defect)
            return value
        elif cte in ("x-uuencode", "uuencode", "uue", "x-uue"):
            in_file = BytesIO(bpayload)
            out_file = BytesIO()
            try:
                uu.decode(in_file, out_file, quiet=True)
                return out_file.getvalue()
            except uu.Error:
                return bpayload
        if isinstance(payload, str):
            return bpayload
        return payload

    def set_payload(self, payload, charset=None):
        "Set the payload to the given value.\n\n        Optional charset sets the message's default character set.  See\n        set_charset() for details.\n        "
        if hasattr(payload, "encode"):
            if charset is None:
                self._payload = payload
                return
            if not isinstance(charset, Charset):
                charset = Charset(charset)
            payload = payload.encode(charset.output_charset)
        if hasattr(payload, "decode"):
            self._payload = payload.decode("ascii", "surrogateescape")
        else:
            self._payload = payload
        if charset is not None:
            self.set_charset(charset)

    def set_charset(self, charset):
        "Set the charset of the payload to a given character set.\n\n        charset can be a Charset instance, a string naming a character set, or\n        None.  If it is a string it will be converted to a Charset instance.\n        If charset is None, the charset parameter will be removed from the\n        Content-Type field.  Anything else will generate a TypeError.\n\n        The message will be assumed to be of type text/* encoded with\n        charset.input_charset.  It will be converted to charset.output_charset\n        and encoded properly, if needed, when generating the plain text\n        representation of the message.  MIME headers (MIME-Version,\n        Content-Type, Content-Transfer-Encoding) will be added as needed.\n        "
        if charset is None:
            self.del_param("charset")
            self._charset = None
            return
        if not isinstance(charset, Charset):
            charset = Charset(charset)
        self._charset = charset
        if "MIME-Version" not in self:
            self.add_header("MIME-Version", "1.0")
        if "Content-Type" not in self:
            self.add_header(
                "Content-Type", "text/plain", charset=charset.get_output_charset()
            )
        else:
            self.set_param("charset", charset.get_output_charset())
        if charset != charset.get_output_charset():
            self._payload = charset.body_encode(self._payload)
        if "Content-Transfer-Encoding" not in self:
            cte = charset.get_body_encoding()
            try:
                cte(self)
            except TypeError:
                payload = self._payload
                if payload:
                    try:
                        payload = payload.encode("ascii", "surrogateescape")
                    except UnicodeError:
                        payload = payload.encode(charset.output_charset)
                self._payload = charset.body_encode(payload)
                self.add_header("Content-Transfer-Encoding", cte)

    def get_charset(self):
        "Return the Charset instance associated with the message's payload.\n        "
        return self._charset

    def __len__(self):
        "Return the total number of headers, including duplicates."
        return len(self._headers)

    def __getitem__(self, name):
        "Get a header value.\n\n        Return None if the header is missing instead of raising an exception.\n\n        Note that if the header appeared multiple times, exactly which\n        occurrence gets returned is undefined.  Use get_all() to get all\n        the values matching a header field name.\n        "
        return self.get(name)

    def __setitem__(self, name, val):
        "Set the value of a header.\n\n        Note: this does not overwrite an existing header with the same field\n        name.  Use __delitem__() first to delete any existing headers.\n        "
        max_count = self.policy.header_max_count(name)
        if max_count:
            lname = name.lower()
            found = 0
            for (k, v) in self._headers:
                if k.lower() == lname:
                    found += 1
                    if found >= max_count:
                        raise ValueError(
                            "There may be at most {} {} headers in a message".format(
                                max_count, name
                            )
                        )
        self._headers.append(self.policy.header_store_parse(name, val))

    def __delitem__(self, name):
        "Delete all occurrences of a header, if present.\n\n        Does not raise an exception if the header is missing.\n        "
        name = name.lower()
        newheaders = []
        for (k, v) in self._headers:
            if k.lower() != name:
                newheaders.append((k, v))
        self._headers = newheaders

    def __contains__(self, name):
        return name.lower() in [k.lower() for (k, v) in self._headers]

    def __iter__(self):
        for (field, value) in self._headers:
            (yield field)

    def keys(self):
        "Return a list of all the message's header field names.\n\n        These will be sorted in the order they appeared in the original\n        message, or were added to the message, and may contain duplicates.\n        Any fields deleted and re-inserted are always appended to the header\n        list.\n        "
        return [k for (k, v) in self._headers]

    def values(self):
        "Return a list of all the message's header values.\n\n        These will be sorted in the order they appeared in the original\n        message, or were added to the message, and may contain duplicates.\n        Any fields deleted and re-inserted are always appended to the header\n        list.\n        "
        return [self.policy.header_fetch_parse(k, v) for (k, v) in self._headers]

    def items(self):
        "Get all the message's header fields and values.\n\n        These will be sorted in the order they appeared in the original\n        message, or were added to the message, and may contain duplicates.\n        Any fields deleted and re-inserted are always appended to the header\n        list.\n        "
        return [(k, self.policy.header_fetch_parse(k, v)) for (k, v) in self._headers]

    def get(self, name, failobj=None):
        "Get a header value.\n\n        Like __getitem__() but return failobj instead of None when the field\n        is missing.\n        "
        name = name.lower()
        for (k, v) in self._headers:
            if k.lower() == name:
                return self.policy.header_fetch_parse(k, v)
        return failobj

    def set_raw(self, name, value):
        'Store name and value in the model without modification.\n\n        This is an "internal" API, intended only for use by a parser.\n        '
        self._headers.append((name, value))

    def raw_items(self):
        'Return the (name, value) header pairs without modification.\n\n        This is an "internal" API, intended only for use by a generator.\n        '
        return iter(self._headers.copy())

    def get_all(self, name, failobj=None):
        "Return a list of all the values for the named field.\n\n        These will be sorted in the order they appeared in the original\n        message, and may contain duplicates.  Any fields deleted and\n        re-inserted are always appended to the header list.\n\n        If no such fields exist, failobj is returned (defaults to None).\n        "
        values = []
        name = name.lower()
        for (k, v) in self._headers:
            if k.lower() == name:
                values.append(self.policy.header_fetch_parse(k, v))
        if not values:
            return failobj
        return values

    def add_header(self, _name, _value, **_params):
        "Extended header setting.\n\n        name is the header field to add.  keyword arguments can be used to set\n        additional parameters for the header field, with underscores converted\n        to dashes.  Normally the parameter will be added as key=\"value\" unless\n        value is None, in which case only the key will be added.  If a\n        parameter value contains non-ASCII characters it can be specified as a\n        three-tuple of (charset, language, value), in which case it will be\n        encoded according to RFC2231 rules.  Otherwise it will be encoded using\n        the utf-8 charset and a language of ''.\n\n        Examples:\n\n        msg.add_header('content-disposition', 'attachment', filename='bud.gif')\n        msg.add_header('content-disposition', 'attachment',\n                       filename=('utf-8', '', Fußballer.ppt'))\n        msg.add_header('content-disposition', 'attachment',\n                       filename='Fußballer.ppt'))\n        "
        parts = []
        for (k, v) in _params.items():
            if v is None:
                parts.append(k.replace("_", "-"))
            else:
                parts.append(_formatparam(k.replace("_", "-"), v))
        if _value is not None:
            parts.insert(0, _value)
        self[_name] = SEMISPACE.join(parts)

    def replace_header(self, _name, _value):
        "Replace a header.\n\n        Replace the first matching header found in the message, retaining\n        header order and case.  If no matching header was found, a KeyError is\n        raised.\n        "
        _name = _name.lower()
        for (i, (k, v)) in zip(range(len(self._headers)), self._headers):
            if k.lower() == _name:
                self._headers[i] = self.policy.header_store_parse(k, _value)
                break
        else:
            raise KeyError(_name)

    def get_content_type(self):
        "Return the message's content type.\n\n        The returned string is coerced to lower case of the form\n        `maintype/subtype'.  If there was no Content-Type header in the\n        message, the default type as given by get_default_type() will be\n        returned.  Since according to RFC 2045, messages always have a default\n        type this will always return a value.\n\n        RFC 2045 defines a message's default type to be text/plain unless it\n        appears inside a multipart/digest container, in which case it would be\n        message/rfc822.\n        "
        missing = object()
        value = self.get("content-type", missing)
        if value is missing:
            return self.get_default_type()
        ctype = _splitparam(value)[0].lower()
        if ctype.count("/") != 1:
            return "text/plain"
        return ctype

    def get_content_maintype(self):
        "Return the message's main content type.\n\n        This is the `maintype' part of the string returned by\n        get_content_type().\n        "
        ctype = self.get_content_type()
        return ctype.split("/")[0]

    def get_content_subtype(self):
        "Returns the message's sub-content type.\n\n        This is the `subtype' part of the string returned by\n        get_content_type().\n        "
        ctype = self.get_content_type()
        return ctype.split("/")[1]

    def get_default_type(self):
        "Return the `default' content type.\n\n        Most messages have a default content type of text/plain, except for\n        messages that are subparts of multipart/digest containers.  Such\n        subparts have a default content type of message/rfc822.\n        "
        return self._default_type

    def set_default_type(self, ctype):
        'Set the `default\' content type.\n\n        ctype should be either "text/plain" or "message/rfc822", although this\n        is not enforced.  The default content type is not stored in the\n        Content-Type header.\n        '
        self._default_type = ctype

    def _get_params_preserve(self, failobj, header):
        missing = object()
        value = self.get(header, missing)
        if value is missing:
            return failobj
        params = []
        for p in _parseparam(value):
            try:
                (name, val) = p.split("=", 1)
                name = name.strip()
                val = val.strip()
            except ValueError:
                name = p.strip()
                val = ""
            params.append((name, val))
        params = utils.decode_params(params)
        return params

    def get_params(self, failobj=None, header="content-type", unquote=True):
        "Return the message's Content-Type parameters, as a list.\n\n        The elements of the returned list are 2-tuples of key/value pairs, as\n        split on the `=' sign.  The left hand side of the `=' is the key,\n        while the right hand side is the value.  If there is no `=' sign in\n        the parameter the value is the empty string.  The value is as\n        described in the get_param() method.\n\n        Optional failobj is the object to return if there is no Content-Type\n        header.  Optional header is the header to search instead of\n        Content-Type.  If unquote is True, the value is unquoted.\n        "
        missing = object()
        params = self._get_params_preserve(missing, header)
        if params is missing:
            return failobj
        if unquote:
            return [(k, _unquotevalue(v)) for (k, v) in params]
        else:
            return params

    def get_param(self, param, failobj=None, header="content-type", unquote=True):
        "Return the parameter value if found in the Content-Type header.\n\n        Optional failobj is the object to return if there is no Content-Type\n        header, or the Content-Type header has no such parameter.  Optional\n        header is the header to search instead of Content-Type.\n\n        Parameter keys are always compared case insensitively.  The return\n        value can either be a string, or a 3-tuple if the parameter was RFC\n        2231 encoded.  When it's a 3-tuple, the elements of the value are of\n        the form (CHARSET, LANGUAGE, VALUE).  Note that both CHARSET and\n        LANGUAGE can be None, in which case you should consider VALUE to be\n        encoded in the us-ascii charset.  You can usually ignore LANGUAGE.\n        The parameter value (either the returned string, or the VALUE item in\n        the 3-tuple) is always unquoted, unless unquote is set to False.\n\n        If your application doesn't care whether the parameter was RFC 2231\n        encoded, it can turn the return value into a string as follows:\n\n            rawparam = msg.get_param('foo')\n            param = email.utils.collapse_rfc2231_value(rawparam)\n\n        "
        if header not in self:
            return failobj
        for (k, v) in self._get_params_preserve(failobj, header):
            if k.lower() == param.lower():
                if unquote:
                    return _unquotevalue(v)
                else:
                    return v
        return failobj

    def set_param(
        self,
        param,
        value,
        header="Content-Type",
        requote=True,
        charset=None,
        language="",
        replace=False,
    ):
        'Set a parameter in the Content-Type header.\n\n        If the parameter already exists in the header, its value will be\n        replaced with the new value.\n\n        If header is Content-Type and has not yet been defined for this\n        message, it will be set to "text/plain" and the new parameter and\n        value will be appended as per RFC 2045.\n\n        An alternate header can be specified in the header argument, and all\n        parameters will be quoted as necessary unless requote is False.\n\n        If charset is specified, the parameter will be encoded according to RFC\n        2231.  Optional language specifies the RFC 2231 language, defaulting\n        to the empty string.  Both charset and language should be strings.\n        '
        if (not isinstance(value, tuple)) and charset:
            value = (charset, language, value)
        if (header not in self) and (header.lower() == "content-type"):
            ctype = "text/plain"
        else:
            ctype = self.get(header)
        if not self.get_param(param, header=header):
            if not ctype:
                ctype = _formatparam(param, value, requote)
            else:
                ctype = SEMISPACE.join([ctype, _formatparam(param, value, requote)])
        else:
            ctype = ""
            for (old_param, old_value) in self.get_params(
                header=header, unquote=requote
            ):
                append_param = ""
                if old_param.lower() == param.lower():
                    append_param = _formatparam(param, value, requote)
                else:
                    append_param = _formatparam(old_param, old_value, requote)
                if not ctype:
                    ctype = append_param
                else:
                    ctype = SEMISPACE.join([ctype, append_param])
        if ctype != self.get(header):
            if replace:
                self.replace_header(header, ctype)
            else:
                del self[header]
                self[header] = ctype

    def del_param(self, param, header="content-type", requote=True):
        "Remove the given parameter completely from the Content-Type header.\n\n        The header will be re-written in place without the parameter or its\n        value. All values will be quoted as necessary unless requote is\n        False.  Optional header specifies an alternative to the Content-Type\n        header.\n        "
        if header not in self:
            return
        new_ctype = ""
        for (p, v) in self.get_params(header=header, unquote=requote):
            if p.lower() != param.lower():
                if not new_ctype:
                    new_ctype = _formatparam(p, v, requote)
                else:
                    new_ctype = SEMISPACE.join([new_ctype, _formatparam(p, v, requote)])
        if new_ctype != self.get(header):
            del self[header]
            self[header] = new_ctype

    def set_type(self, type, header="Content-Type", requote=True):
        "Set the main type and subtype for the Content-Type header.\n\n        type must be a string in the form \"maintype/subtype\", otherwise a\n        ValueError is raised.\n\n        This method replaces the Content-Type header, keeping all the\n        parameters in place.  If requote is False, this leaves the existing\n        header's quoting as is.  Otherwise, the parameters will be quoted (the\n        default).\n\n        An alternative header can be specified in the header argument.  When\n        the Content-Type header is set, we'll always also add a MIME-Version\n        header.\n        "
        if not (type.count("/") == 1):
            raise ValueError
        if header.lower() == "content-type":
            del self["mime-version"]
            self["MIME-Version"] = "1.0"
        if header not in self:
            self[header] = type
            return
        params = self.get_params(header=header, unquote=requote)
        del self[header]
        self[header] = type
        for (p, v) in params[1:]:
            self.set_param(p, v, header, requote)

    def get_filename(self, failobj=None):
        "Return the filename associated with the payload if present.\n\n        The filename is extracted from the Content-Disposition header's\n        `filename' parameter, and it is unquoted.  If that header is missing\n        the `filename' parameter, this method falls back to looking for the\n        `name' parameter.\n        "
        missing = object()
        filename = self.get_param("filename", missing, "content-disposition")
        if filename is missing:
            filename = self.get_param("name", missing, "content-type")
        if filename is missing:
            return failobj
        return utils.collapse_rfc2231_value(filename).strip()

    def get_boundary(self, failobj=None):
        "Return the boundary associated with the payload if present.\n\n        The boundary is extracted from the Content-Type header's `boundary'\n        parameter, and it is unquoted.\n        "
        missing = object()
        boundary = self.get_param("boundary", missing)
        if boundary is missing:
            return failobj
        return utils.collapse_rfc2231_value(boundary).rstrip()

    def set_boundary(self, boundary):
        "Set the boundary parameter in Content-Type to 'boundary'.\n\n        This is subtly different than deleting the Content-Type header and\n        adding a new one with a new boundary parameter via add_header().  The\n        main difference is that using the set_boundary() method preserves the\n        order of the Content-Type header in the original message.\n\n        HeaderParseError is raised if the message has no Content-Type header.\n        "
        missing = object()
        params = self._get_params_preserve(missing, "content-type")
        if params is missing:
            raise errors.HeaderParseError("No Content-Type header found")
        newparams = []
        foundp = False
        for (pk, pv) in params:
            if pk.lower() == "boundary":
                newparams.append(("boundary", ('"%s"' % boundary)))
                foundp = True
            else:
                newparams.append((pk, pv))
        if not foundp:
            newparams.append(("boundary", ('"%s"' % boundary)))
        newheaders = []
        for (h, v) in self._headers:
            if h.lower() == "content-type":
                parts = []
                for (k, v) in newparams:
                    if v == "":
                        parts.append(k)
                    else:
                        parts.append(("%s=%s" % (k, v)))
                val = SEMISPACE.join(parts)
                newheaders.append(self.policy.header_store_parse(h, val))
            else:
                newheaders.append((h, v))
        self._headers = newheaders

    def get_content_charset(self, failobj=None):
        "Return the charset parameter of the Content-Type header.\n\n        The returned string is always coerced to lower case.  If there is no\n        Content-Type header, or if that header has no charset parameter,\n        failobj is returned.\n        "
        missing = object()
        charset = self.get_param("charset", missing)
        if charset is missing:
            return failobj
        if isinstance(charset, tuple):
            pcharset = charset[0] or "us-ascii"
            try:
                as_bytes = charset[2].encode("raw-unicode-escape")
                charset = str(as_bytes, pcharset)
            except (LookupError, UnicodeError):
                charset = charset[2]
        try:
            charset.encode("us-ascii")
        except UnicodeError:
            return failobj
        return charset.lower()

    def get_charsets(self, failobj=None):
        "Return a list containing the charset(s) used in this message.\n\n        The returned list of items describes the Content-Type headers'\n        charset parameter for this message and all the subparts in its\n        payload.\n\n        Each item will either be a string (the value of the charset parameter\n        in the Content-Type header of that part) or the value of the\n        'failobj' parameter (defaults to None), if the part does not have a\n        main MIME type of \"text\", or the charset is not defined.\n\n        The list will contain one string for each part of the message, plus\n        one for the container message (i.e. self), so that a non-multipart\n        message will still return a list of length 1.\n        "
        return [part.get_content_charset(failobj) for part in self.walk()]

    def get_content_disposition(self):
        "Return the message's content-disposition if it exists, or None.\n\n        The return values can be either 'inline', 'attachment' or None\n        according to the rfc2183.\n        "
        value = self.get("content-disposition")
        if value is None:
            return None
        c_d = _splitparam(value)[0].lower()
        return c_d

    from email.iterators import walk


class MIMEPart(Message):
    def __init__(self, policy=None):
        if policy is None:
            from email.policy import default

            policy = default
        Message.__init__(self, policy)

    def as_string(self, unixfrom=False, maxheaderlen=None, policy=None):
        "Return the entire formatted message as a string.\n\n        Optional 'unixfrom', when true, means include the Unix From_ envelope\n        header.  maxheaderlen is retained for backward compatibility with the\n        base Message class, but defaults to None, meaning that the policy value\n        for max_line_length controls the header maximum length.  'policy' is\n        passed to the Generator instance used to serialize the message; if it\n        is not specified the policy associated with the message instance is\n        used.\n        "
        policy = self.policy if (policy is None) else policy
        if maxheaderlen is None:
            maxheaderlen = policy.max_line_length
        return super().as_string(maxheaderlen=maxheaderlen, policy=policy)

    def __str__(self):
        return self.as_string(policy=self.policy.clone(utf8=True))

    def is_attachment(self):
        c_d = self.get("content-disposition")
        return False if (c_d is None) else (c_d.content_disposition == "attachment")

    def _find_body(self, part, preferencelist):
        if part.is_attachment():
            return
        (maintype, subtype) = part.get_content_type().split("/")
        if maintype == "text":
            if subtype in preferencelist:
                (yield (preferencelist.index(subtype), part))
            return
        if maintype != "multipart":
            return
        if subtype != "related":
            for subpart in part.iter_parts():
                (yield from self._find_body(subpart, preferencelist))
            return
        if "related" in preferencelist:
            (yield (preferencelist.index("related"), part))
        candidate = None
        start = part.get_param("start")
        if start:
            for subpart in part.iter_parts():
                if subpart["content-id"] == start:
                    candidate = subpart
                    break
        if candidate is None:
            subparts = part.get_payload()
            candidate = subparts[0] if subparts else None
        if candidate is not None:
            (yield from self._find_body(candidate, preferencelist))

    def get_body(self, preferencelist=("related", "html", "plain")):
        "Return best candidate mime part for display as 'body' of message.\n\n        Do a depth first search, starting with self, looking for the first part\n        matching each of the items in preferencelist, and return the part\n        corresponding to the first item that has a match, or None if no items\n        have a match.  If 'related' is not included in preferencelist, consider\n        the root part of any multipart/related encountered as a candidate\n        match.  Ignore parts with 'Content-Disposition: attachment'.\n        "
        best_prio = len(preferencelist)
        body = None
        for (prio, part) in self._find_body(self, preferencelist):
            if prio < best_prio:
                best_prio = prio
                body = part
                if prio == 0:
                    break
        return body

    _body_types = {
        ("text", "plain"),
        ("text", "html"),
        ("multipart", "related"),
        ("multipart", "alternative"),
    }

    def iter_attachments(self):
        "Return an iterator over the non-main parts of a multipart.\n\n        Skip the first of each occurrence of text/plain, text/html,\n        multipart/related, or multipart/alternative in the multipart (unless\n        they have a 'Content-Disposition: attachment' header) and include all\n        remaining subparts in the returned iterator.  When applied to a\n        multipart/related, return all parts except the root part.  Return an\n        empty iterator when applied to a multipart/alternative or a\n        non-multipart.\n        "
        (maintype, subtype) = self.get_content_type().split("/")
        if (maintype != "multipart") or (subtype == "alternative"):
            return
        payload = self.get_payload()
        try:
            parts = payload.copy()
        except AttributeError:
            return
        if (maintype == "multipart") and (subtype == "related"):
            start = self.get_param("start")
            if start:
                found = False
                attachments = []
                for part in parts:
                    if part.get("content-id") == start:
                        found = True
                    else:
                        attachments.append(part)
                if found:
                    (yield from attachments)
                    return
            parts.pop(0)
            (yield from parts)
            return
        seen = []
        for part in parts:
            (maintype, subtype) = part.get_content_type().split("/")
            if (
                ((maintype, subtype) in self._body_types)
                and (not part.is_attachment())
                and (subtype not in seen)
            ):
                seen.append(subtype)
                continue
            (yield part)

    def iter_parts(self):
        "Return an iterator over all immediate subparts of a multipart.\n\n        Return an empty iterator for a non-multipart.\n        "
        if self.get_content_maintype() == "multipart":
            (yield from self.get_payload())

    def get_content(self, *args, content_manager=None, **kw):
        if content_manager is None:
            content_manager = self.policy.content_manager
        return content_manager.get_content(self, *args, **kw)

    def set_content(self, *args, content_manager=None, **kw):
        if content_manager is None:
            content_manager = self.policy.content_manager
        content_manager.set_content(self, *args, **kw)

    def _make_multipart(self, subtype, disallowed_subtypes, boundary):
        if self.get_content_maintype() == "multipart":
            existing_subtype = self.get_content_subtype()
            disallowed_subtypes = disallowed_subtypes + (subtype,)
            if existing_subtype in disallowed_subtypes:
                raise ValueError(
                    "Cannot convert {} to {}".format(existing_subtype, subtype)
                )
        keep_headers = []
        part_headers = []
        for (name, value) in self._headers:
            if name.lower().startswith("content-"):
                part_headers.append((name, value))
            else:
                keep_headers.append((name, value))
        if part_headers:
            part = type(self)(policy=self.policy)
            part._headers = part_headers
            part._payload = self._payload
            self._payload = [part]
        else:
            self._payload = []
        self._headers = keep_headers
        self["Content-Type"] = "multipart/" + subtype
        if boundary is not None:
            self.set_param("boundary", boundary)

    def make_related(self, boundary=None):
        self._make_multipart("related", ("alternative", "mixed"), boundary)

    def make_alternative(self, boundary=None):
        self._make_multipart("alternative", ("mixed",), boundary)

    def make_mixed(self, boundary=None):
        self._make_multipart("mixed", (), boundary)

    def _add_multipart(self, _subtype, *args, _disp=None, **kw):
        if (self.get_content_maintype() != "multipart") or (
            self.get_content_subtype() != _subtype
        ):
            getattr(self, ("make_" + _subtype))()
        part = type(self)(policy=self.policy)
        part.set_content(*args, **kw)
        if _disp and ("content-disposition" not in part):
            part["Content-Disposition"] = _disp
        self.attach(part)

    def add_related(self, *args, **kw):
        self._add_multipart("related", *args, _disp="inline", **kw)

    def add_alternative(self, *args, **kw):
        self._add_multipart("alternative", *args, **kw)

    def add_attachment(self, *args, **kw):
        self._add_multipart("mixed", *args, _disp="attachment", **kw)

    def clear(self):
        self._headers = []
        self._payload = None

    def clear_content(self):
        self._headers = [
            (n, v) for (n, v) in self._headers if (not n.lower().startswith("content-"))
        ]
        self._payload = None


class EmailMessage(MIMEPart):
    def set_content(self, *args, **kw):
        super().set_content(*args, **kw)
        if "MIME-Version" not in self:
            self["MIME-Version"] = "1.0"
