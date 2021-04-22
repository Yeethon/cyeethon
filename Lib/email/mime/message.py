"Class representing message/* MIME documents."
__all__ = ["MIMEMessage"]
from email import message
from email.mime.nonmultipart import MIMENonMultipart


class MIMEMessage(MIMENonMultipart):
    "Class representing message/* MIME documents."

    def __init__(self, _msg, _subtype="rfc822", *, policy=None):
        'Create a message/* type MIME document.\n\n        _msg is a message object and must be an instance of Message, or a\n        derived class of Message, otherwise a TypeError is raised.\n\n        Optional _subtype defines the subtype of the contained message.  The\n        default is "rfc822" (this is defined by the MIME standard, even though\n        the term "rfc822" is technically outdated by RFC 2822).\n        '
        MIMENonMultipart.__init__(self, "message", _subtype, policy=policy)
        if not isinstance(_msg, message.Message):
            raise TypeError("Argument is not an instance of Message")
        message.Message.attach(self, _msg)
        self.set_default_type("message/rfc822")
