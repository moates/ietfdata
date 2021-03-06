from typing import Any

IMAPClientError: Any
IMAPClientAbortError: Any
IMAPClientReadOnlyError: Any

class CapabilityError(IMAPClientError): ...
class LoginError(IMAPClientError): ...
class IllegalStateError(IMAPClientError): ...
class InvalidCriteriaError(IMAPClientError): ...
class ProtocolError(IMAPClientError): ...
