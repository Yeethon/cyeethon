"Class representing text/* type MIME documents."
__all__ = ["MIMEText"]
from email.charset import Charset
from email.mime.nonmultipart import MIMENonMultipart


class MIMEText(MIMENonMultipart):
    "Class for generating text/* type MIME documents."

    def __init__(self, _text, _subtype="plain", _charset=None, *, policy=None):
        'Create a text/* type MIME document.\n\n        _text is the string for this message object.\n\n        _subtype is the MIME sub content type, defaulting to "plain".\n\n        _charset is the character set parameter added to the Content-Type\n        header.  This defaults to "us-ascii".  Note that as a side-effect, the\n        Content-Transfer-Encoding header will also be set.\n        '
        if _charset is None:
            try:
                _text.encode("us-ascii")
                _charset = "us-ascii"
            except UnicodeEncodeError:
                _charset = "utf-8"
        MIMENonMultipart.__init__(
            self, "text", _subtype, policy=policy, **{"charset": str(_charset)}
        )
        self.set_payload(_text, _charset)
