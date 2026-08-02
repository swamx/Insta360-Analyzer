"""Base Stage class that all pipeline stages inherit from."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.utils.logger import get_logger


logger = get_logger("stages.base")


@dataclass
class StageResult:
    """Result of running a stage."""

    success: bool
    stage_name: str
    file_id: str
    message: str
    data: Dict[str, Any] = None


@dataclass
class ProgressInfo:
    """Progress information for a stage."""

    stage_name: str
    file_id: str
    total_items: int
    completed_items: int
    current_item: int = 0
    error_message: Optional[str] = None

    @property
    def completion_percentage(self) -> float:
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100


class Stage(ABC):
    """Base class for all pipeline stages."""

    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.logger = get_logger(f"stages.{stage_name}")

    @abstractmethod
    def run(
        self,
        file_id: str,
        resume_from: Optional[int] = None,
    ) -> StageResult:
        """
        Execute this stage.

        Args:
            file_id: Unique identifier for the file being processed
            resume_from: If provided, resume from this frame/item index

        Returns:
            StageResult with success status and message
        """
        pass

    @abstractmethod
    def can_resume(self, file_id: str) -> bool:
        """
        Check if this stage has a resumable checkpoint for the file.

        Args:
            file_id: File identifier

        Returns:
            True if resumable checkpoint exists
        """
        pass

    @abstractmethod
    def get_progress(self, file_id: str) -> Optional[ProgressInfo]:
        """
        Get progress information for this stage on the given file.

        Args:
            file_id: File identifier

        Returns:
            ProgressInfo if stage has been run, None otherwise
        """
        pass

    def _log_stage_start(self, file_id: str, resume_from: Optional[int] = None) -> None:
        """Log stage start."""
        if resume_from is not None:
            self.logger.info(
                f"[{file_id}] Starting {self.stage_name} (resuming from item {resume_from})"
            )
        else:
            self.logger.info(f"[{file_id}] Starting {self.stage_name}")

    def _log_stage_complete(self, file_id: str) -> None:
        """Log stage completion."""
        self.logger.info(f"[{file_id}] Completed {self.stage_name}")

    def _log_progress(self, file_id: str, current: int, total: int) -> None:
        """Log progress update."""
        pct = (current / total * 100) if total > 0 else 0
        self.logger.debug(
            f"[{file_id}] {self.stage_name} progress: {current}/{total} ({pct:.1f}%)"
        )
