"\nThis module contains the core classes of version 2.0 of SAX for Python.\nThis file provides only default classes with absolutely minimum\nfunctionality, from which drivers and applications can be subclassed.\n\nMany of these classes are empty and are included only as documentation\nof the interfaces.\n\n$Id$\n"
version = "2.0beta"


class ErrorHandler:
    "Basic interface for SAX error handlers.\n\n    If you create an object that implements this interface, then\n    register the object with your XMLReader, the parser will call the\n    methods in your object to report all warnings and errors. There\n    are three levels of errors available: warnings, (possibly)\n    recoverable errors, and unrecoverable errors. All methods take a\n    SAXParseException as the only parameter."

    def error(self, exception):
        "Handle a recoverable error."
        raise exception

    def fatalError(self, exception):
        "Handle a non-recoverable error."
        raise exception

    def warning(self, exception):
        "Handle a warning."
        print(exception)


class ContentHandler:
    "Interface for receiving logical document content events.\n\n    This is the main callback interface in SAX, and the one most\n    important to applications. The order of events in this interface\n    mirrors the order of the information in the document."

    def __init__(self):
        self._locator = None

    def setDocumentLocator(self, locator):
        "Called by the parser to give the application a locator for\n        locating the origin of document events.\n\n        SAX parsers are strongly encouraged (though not absolutely\n        required) to supply a locator: if it does so, it must supply\n        the locator to the application by invoking this method before\n        invoking any of the other methods in the DocumentHandler\n        interface.\n\n        The locator allows the application to determine the end\n        position of any document-related event, even if the parser is\n        not reporting an error. Typically, the application will use\n        this information for reporting its own errors (such as\n        character content that does not match an application's\n        business rules). The information returned by the locator is\n        probably not sufficient for use with a search engine.\n\n        Note that the locator will return correct information only\n        during the invocation of the events in this interface. The\n        application should not attempt to use it at any other time."
        self._locator = locator

    def startDocument(self):
        "Receive notification of the beginning of a document.\n\n        The SAX parser will invoke this method only once, before any\n        other methods in this interface or in DTDHandler (except for\n        setDocumentLocator)."

    def endDocument(self):
        "Receive notification of the end of a document.\n\n        The SAX parser will invoke this method only once, and it will\n        be the last method invoked during the parse. The parser shall\n        not invoke this method until it has either abandoned parsing\n        (because of an unrecoverable error) or reached the end of\n        input."

    def startPrefixMapping(self, prefix, uri):
        "Begin the scope of a prefix-URI Namespace mapping.\n\n        The information from this event is not necessary for normal\n        Namespace processing: the SAX XML reader will automatically\n        replace prefixes for element and attribute names when the\n        http://xml.org/sax/features/namespaces feature is true (the\n        default).\n\n        There are cases, however, when applications need to use\n        prefixes in character data or in attribute values, where they\n        cannot safely be expanded automatically; the\n        start/endPrefixMapping event supplies the information to the\n        application to expand prefixes in those contexts itself, if\n        necessary.\n\n        Note that start/endPrefixMapping events are not guaranteed to\n        be properly nested relative to each-other: all\n        startPrefixMapping events will occur before the corresponding\n        startElement event, and all endPrefixMapping events will occur\n        after the corresponding endElement event, but their order is\n        not guaranteed."

    def endPrefixMapping(self, prefix):
        "End the scope of a prefix-URI mapping.\n\n        See startPrefixMapping for details. This event will always\n        occur after the corresponding endElement event, but the order\n        of endPrefixMapping events is not otherwise guaranteed."

    def startElement(self, name, attrs):
        "Signals the start of an element in non-namespace mode.\n\n        The name parameter contains the raw XML 1.0 name of the\n        element type as a string and the attrs parameter holds an\n        instance of the Attributes class containing the attributes of\n        the element."

    def endElement(self, name):
        "Signals the end of an element in non-namespace mode.\n\n        The name parameter contains the name of the element type, just\n        as with the startElement event."

    def startElementNS(self, name, qname, attrs):
        "Signals the start of an element in namespace mode.\n\n        The name parameter contains the name of the element type as a\n        (uri, localname) tuple, the qname parameter the raw XML 1.0\n        name used in the source document, and the attrs parameter\n        holds an instance of the Attributes class containing the\n        attributes of the element.\n\n        The uri part of the name tuple is None for elements which have\n        no namespace."

    def endElementNS(self, name, qname):
        "Signals the end of an element in namespace mode.\n\n        The name parameter contains the name of the element type, just\n        as with the startElementNS event."

    def characters(self, content):
        "Receive notification of character data.\n\n        The Parser will call this method to report each chunk of\n        character data. SAX parsers may return all contiguous\n        character data in a single chunk, or they may split it into\n        several chunks; however, all of the characters in any single\n        event must come from the same external entity so that the\n        Locator provides useful information."

    def ignorableWhitespace(self, whitespace):
        "Receive notification of ignorable whitespace in element content.\n\n        Validating Parsers must use this method to report each chunk\n        of ignorable whitespace (see the W3C XML 1.0 recommendation,\n        section 2.10): non-validating parsers may also use this method\n        if they are capable of parsing and using content models.\n\n        SAX parsers may return all contiguous whitespace in a single\n        chunk, or they may split it into several chunks; however, all\n        of the characters in any single event must come from the same\n        external entity, so that the Locator provides useful\n        information."

    def processingInstruction(self, target, data):
        "Receive notification of a processing instruction.\n\n        The Parser will invoke this method once for each processing\n        instruction found: note that processing instructions may occur\n        before or after the main document element.\n\n        A SAX parser should never report an XML declaration (XML 1.0,\n        section 2.8) or a text declaration (XML 1.0, section 4.3.1)\n        using this method."

    def skippedEntity(self, name):
        "Receive notification of a skipped entity.\n\n        The Parser will invoke this method once for each entity\n        skipped. Non-validating processors may skip entities if they\n        have not seen the declarations (because, for example, the\n        entity was declared in an external DTD subset). All processors\n        may skip external entities, depending on the values of the\n        http://xml.org/sax/features/external-general-entities and the\n        http://xml.org/sax/features/external-parameter-entities\n        properties."


class DTDHandler:
    "Handle DTD events.\n\n    This interface specifies only those DTD events required for basic\n    parsing (unparsed entities and attributes)."

    def notationDecl(self, name, publicId, systemId):
        "Handle a notation declaration event."

    def unparsedEntityDecl(self, name, publicId, systemId, ndata):
        "Handle an unparsed entity declaration event."


class EntityResolver:
    "Basic interface for resolving entities. If you create an object\n    implementing this interface, then register the object with your\n    Parser, the parser will call the method in your object to\n    resolve all external entities. Note that DefaultHandler implements\n    this interface with the default behaviour."

    def resolveEntity(self, publicId, systemId):
        "Resolve the system identifier of an entity and return either\n        the system identifier to read from as a string, or an InputSource\n        to read from."
        return systemId


feature_namespaces = "http://xml.org/sax/features/namespaces"
feature_namespace_prefixes = "http://xml.org/sax/features/namespace-prefixes"
feature_string_interning = "http://xml.org/sax/features/string-interning"
feature_validation = "http://xml.org/sax/features/validation"
feature_external_ges = "http://xml.org/sax/features/external-general-entities"
feature_external_pes = "http://xml.org/sax/features/external-parameter-entities"
all_features = [
    feature_namespaces,
    feature_namespace_prefixes,
    feature_string_interning,
    feature_validation,
    feature_external_ges,
    feature_external_pes,
]
property_lexical_handler = "http://xml.org/sax/properties/lexical-handler"
property_declaration_handler = "http://xml.org/sax/properties/declaration-handler"
property_dom_node = "http://xml.org/sax/properties/dom-node"
property_xml_string = "http://xml.org/sax/properties/xml-string"
property_encoding = "http://www.python.org/sax/properties/encoding"
property_interning_dict = "http://www.python.org/sax/properties/interning-dict"
all_properties = [
    property_lexical_handler,
    property_dom_node,
    property_declaration_handler,
    property_xml_string,
    property_encoding,
    property_interning_dict,
]


class LexicalHandler:
    "Optional SAX2 handler for lexical events.\n\n    This handler is used to obtain lexical information about an XML\n    document, that is, information about how the document was encoded\n    (as opposed to what it contains, which is reported to the\n    ContentHandler), such as comments and CDATA marked section\n    boundaries.\n\n    To set the LexicalHandler of an XMLReader, use the setProperty\n    method with the property identifier\n    'http://xml.org/sax/properties/lexical-handler'."

    def comment(self, content):
        "Reports a comment anywhere in the document (including the\n        DTD and outside the document element).\n\n        content is a string that holds the contents of the comment."

    def startDTD(self, name, public_id, system_id):
        "Report the start of the DTD declarations, if the document\n        has an associated DTD.\n\n        A startEntity event will be reported before declaration events\n        from the external DTD subset are reported, and this can be\n        used to infer from which subset DTD declarations derive.\n\n        name is the name of the document element type, public_id the\n        public identifier of the DTD (or None if none were supplied)\n        and system_id the system identfier of the external subset (or\n        None if none were supplied)."

    def endDTD(self):
        "Signals the end of DTD declarations."

    def startCDATA(self):
        "Reports the beginning of a CDATA marked section.\n\n        The contents of the CDATA marked section will be reported\n        through the characters event."

    def endCDATA(self):
        "Reports the end of a CDATA marked section."
