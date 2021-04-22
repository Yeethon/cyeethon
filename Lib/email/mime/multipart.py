"Base class for MIME multipart/* type messages."
__all__ = ["MIMEMultipart"]
from email.mime.base import MIMEBase


class MIMEMultipart(MIMEBase):
    "Base class for MIME multipart/* type messages."

    def __init__(
        self, _subtype="mixed", boundary=None, _subparts=None, *, policy=None, **_params
    ):
        "Creates a multipart/* type message.\n\n        By default, creates a multipart/mixed message, with proper\n        Content-Type and MIME-Version headers.\n\n        _subtype is the subtype of the multipart content type, defaulting to\n        `mixed'.\n\n        boundary is the multipart boundary string.  By default it is\n        calculated as needed.\n\n        _subparts is a sequence of initial subparts for the payload.  It\n        must be an iterable object, such as a list.  You can always\n        attach new subparts to the message by using the attach() method.\n\n        Additional parameters for the Content-Type header are taken from the\n        keyword arguments (or passed into the _params argument).\n        "
        MIMEBase.__init__(self, "multipart", _subtype, policy=policy, **_params)
        self._payload = []
        if _subparts:
            for p in _subparts:
                self.attach(p)
        if boundary:
            self.set_boundary(boundary)
