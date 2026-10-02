"""
errors.py — Exception hierarchy for the Pompom Meta publishing layer.

Every exception raised by this package inherits from PublishError.
"""


class PublishError(Exception):
    """Base class for every publishing failure."""


class MetaConfigurationError(PublishError):
    """Required environment variables are missing or inconsistent."""


class MetaApiError(PublishError):
    """The Graph API answered with an error payload.

    The message never contains an access token; the HTTP layer scrubs
    known secrets before the body reaches this exception.
    """

    def __init__(self, message: str, *, status: int | None = None,
                 code: int | None = None, subcode: int | None = None,
                 error_type: str | None = None, fbtrace_id: str | None = None,
                 body: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.subcode = subcode
        self.error_type = error_type
        self.fbtrace_id = fbtrace_id
        self.body = body

    def __str__(self) -> str:
        parts = [super().__str__()]
        details = []
        if self.status is not None:
            details.append(f"http={self.status}")
        if self.code is not None:
            details.append(f"code={self.code}")
        if self.subcode is not None:
            details.append(f"subcode={self.subcode}")
        if self.error_type:
            details.append(f"type={self.error_type}")
        if self.fbtrace_id:
            details.append(f"fbtrace_id={self.fbtrace_id}")
        if details:
            parts.append(f"({', '.join(details)})")
        return " ".join(parts)


class MetaAuthenticationError(MetaApiError):
    """The token is missing, expired, or lacks the required permission."""


class MetaRateLimitError(MetaApiError):
    """Throttled by Meta; retried with exponential backoff before raising."""


class MetaUploadError(PublishError):
    """The video bytes or the hosted URL could not be ingested."""


class MetaProcessingTimeout(PublishError):
    """Media did not reach a ready state inside the polling window."""


class MetaStorageError(PublishError):
    """The video could not be published to a publicly reachable URL."""
