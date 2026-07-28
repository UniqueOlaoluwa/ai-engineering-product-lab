"""Custom exceptions used by the AI Engineering Product Lab."""


class PromptTemplateError(Exception):
    """Base exception for prompt-template configuration problems."""


class TemplateFileNotFoundError(PromptTemplateError):
    """Raised when the prompt-template file cannot be found."""


class InvalidTemplateJSONError(PromptTemplateError):
    """Raised when the prompt-template file contains invalid JSON."""


class InvalidTemplateStructureError(PromptTemplateError):
    """Raised when the prompt-template configuration has an invalid structure."""