"""Custom exception classes for error handling and recovery."""


class AnalyzerError(Exception):
    """Base exception for analyzer."""

    def __init__(self, message: str, file_id: str = None, stage: str = None):
        self.message = message
        self.file_id = file_id
        self.stage = stage
        super().__init__(self.message)


class RecoverableError(AnalyzerError):
    """Error that can be recovered by resuming from checkpoint."""

    pass


class NonRecoverableError(AnalyzerError):
    """Error that requires manual intervention."""

    pass


class CheckpointError(NonRecoverableError):
    """Checkpoint corruption or integrity error."""

    pass


class ModelError(NonRecoverableError):
    """Vision model loading or inference error."""

    pass


class FrameExtractionError(RecoverableError):
    """Frame extraction failure (may be retryable)."""

    pass


class OutOfMemoryError(RecoverableError):
    """GPU or system out of memory."""

    pass


class InvalidInputError(NonRecoverableError):
    """Invalid input file or format."""

    pass
