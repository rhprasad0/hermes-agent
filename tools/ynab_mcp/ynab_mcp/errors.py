class YnabError(Exception):
    """Base class for YNAB integration errors."""


class YnabConfigError(YnabError):
    """Raised when required YNAB configuration is missing or invalid."""


class YnabApiError(YnabError):
    """Raised when the YNAB API returns an unexpected error."""


class YnabAuthError(YnabApiError):
    """Raised when the configured YNAB access token is invalid or missing."""


class YnabRateLimitError(YnabApiError):
    """Raised when the YNAB API rate limit is exceeded."""
