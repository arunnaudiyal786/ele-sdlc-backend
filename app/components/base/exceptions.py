from typing import Optional, Dict, Any


class ComponentError(Exception):
    """Base exception for all component errors."""

    def __init__(
        self,
        message: str,
        component: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.component = component
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "component": self.component,
            "details": self.details,
        }


# Session Component Exceptions
class SessionNotFoundError(ComponentError):
    pass


class InvalidSessionStateError(ComponentError):
    pass


# Requirement Component Exceptions
class RequirementTooShortError(ComponentError):
    pass


class FileTypeNotAllowedError(ComponentError):
    pass


class FileTooLargeError(ComponentError):
    pass


# Search Component Exceptions
class SearchWeightsInvalidError(ComponentError):
    pass


class NoMatchesFoundError(ComponentError):
    pass


# Agent Component Exceptions
class AgentExecutionError(ComponentError):
    pass


class PromptFormattingError(ComponentError):
    pass


class ResponseParsingError(ComponentError):
    pass


# External Service Exceptions
class OllamaUnavailableError(ComponentError):
    pass


class OllamaTimeoutError(ComponentError):
    pass


class VectorDBError(ComponentError):
    pass
