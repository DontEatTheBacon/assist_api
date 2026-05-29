class AssistAPIError(Exception):
    """ """

# selenium related errors

class ElementNotFoundError(AssistAPIError):
    """ """

class WebDriverError(AssistAPIError):
    """ """

class PageLoadTimeoutError(AssistAPIError):
    """ """

# parsing errors

class ParseError(AssistAPIError):
    """ """

#

class HtmlParseError(ParseError):
    """ """

class AgreementParseError(ParseError):
    """ """