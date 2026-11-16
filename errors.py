"""Єдині типи помилок застосунку (коди збігаються зі spec 6.21)."""


class AppError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code, self.message, self.retryable = code, message, retryable


class LLMError(AppError):
    def __init__(self, message: str, code: str = "LLM_ERROR", retryable: bool = True):
        super().__init__(code, message, retryable)
