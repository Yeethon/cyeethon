"Different kinds of SAX Exceptions"
import sys

if sys.platform[:4] == "java":
    from java.lang import Exception
del sys


class SAXException(Exception):
    "Encapsulate an XML error or warning. This class can contain\n    basic error or warning information from either the XML parser or\n    the application: you can subclass it to provide additional\n    functionality, or to add localization. Note that although you will\n    receive a SAXException as the argument to the handlers in the\n    ErrorHandler interface, you are not actually required to raise\n    the exception; instead, you can simply read the information in\n    it."

    def __init__(self, msg, exception=None):
        "Creates an exception. The message is required, but the exception\n        is optional."
        self._msg = msg
        self._exception = exception
        Exception.__init__(self, msg)

    def getMessage(self):
        "Return a message for this exception."
        return self._msg

    def getException(self):
        "Return the embedded exception, or None if there was none."
        return self._exception

    def __str__(self):
        "Create a string representation of the exception."
        return self._msg

    def __getitem__(self, ix):
        "Avoids weird error messages if someone does exception[ix] by\n        mistake, since Exception has __getitem__ defined."
        raise AttributeError("__getitem__")


class SAXParseException(SAXException):
    "Encapsulate an XML parse error or warning.\n\n    This exception will include information for locating the error in\n    the original XML document. Note that although the application will\n    receive a SAXParseException as the argument to the handlers in the\n    ErrorHandler interface, the application is not actually required\n    to raise the exception; instead, it can simply read the\n    information in it and take a different action.\n\n    Since this exception is a subclass of SAXException, it inherits\n    the ability to wrap another exception."

    def __init__(self, msg, exception, locator):
        "Creates the exception. The exception parameter is allowed to be None."
        SAXException.__init__(self, msg, exception)
        self._locator = locator
        self._systemId = self._locator.getSystemId()
        self._colnum = self._locator.getColumnNumber()
        self._linenum = self._locator.getLineNumber()

    def getColumnNumber(self):
        "The column number of the end of the text where the exception\n        occurred."
        return self._colnum

    def getLineNumber(self):
        "The line number of the end of the text where the exception occurred."
        return self._linenum

    def getPublicId(self):
        "Get the public identifier of the entity where the exception occurred."
        return self._locator.getPublicId()

    def getSystemId(self):
        "Get the system identifier of the entity where the exception occurred."
        return self._systemId

    def __str__(self):
        "Create a string representation of the exception."
        sysid = self.getSystemId()
        if sysid is None:
            sysid = "<unknown>"
        linenum = self.getLineNumber()
        if linenum is None:
            linenum = "?"
        colnum = self.getColumnNumber()
        if colnum is None:
            colnum = "?"
        return "%s:%s:%s: %s" % (sysid, linenum, colnum, self._msg)


class SAXNotRecognizedException(SAXException):
    "Exception class for an unrecognized identifier.\n\n    An XMLReader will raise this exception when it is confronted with an\n    unrecognized feature or property. SAX applications and extensions may\n    use this class for similar purposes."


class SAXNotSupportedException(SAXException):
    "Exception class for an unsupported operation.\n\n    An XMLReader will raise this exception when a service it cannot\n    perform is requested (specifically setting a state or value). SAX\n    applications and extensions may use this class for similar\n    purposes."


class SAXReaderNotAvailable(SAXNotSupportedException):
    "Exception class for a missing driver.\n\n    An XMLReader module (driver) should raise this exception when it\n    is first imported, e.g. when a support module cannot be imported.\n    It also may be raised during parsing, e.g. if executing an external\n    program is not permitted."
