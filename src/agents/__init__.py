"""Agent system for ReACT-based QA with Haystack orchestration."""

from .contracts import (
    AgentRole,
    ActionType,
    AgentMemory,
    ExecutionContext,
    ReasonerContract,
    ActorContract,
    OrchestratorContract,
    QualityAssuranceContract,
    ReActStep,
    ReActTrace,
    QualityMetrics,
    StateTransfer,
    StateCacheContract,
)

from .orchestrator import (
    InMemoryStateCache,
    PersistentStateCache,
    ReActOrchestrator,
    HaystackPipelineState,
    PipelineOrchestrator,
)

from .qa_agent import (
    QAReasonerAgent,
    QAActorAgent,
    QAAssessmentAgent,
)

__all__ = [
    # Contracts
    "AgentRole",
    "ActionType",
    "AgentMemory",
    "ExecutionContext",
    "ReasonerContract",
    "ActorContract",
    "OrchestratorContract",
    "QualityAssuranceContract",
    "ReActStep",
    "ReActTrace",
    "QualityMetrics",
    "StateTransfer",
    "StateCacheContract",
    # Orchestration
    "InMemoryStateCache",
    "PersistentStateCache",
    "ReActOrchestrator",
    "HaystackPipelineState",
    "PipelineOrchestrator",
    # QA Agents
    "QAReasonerAgent",
    "QAActorAgent",
    "QAAssessmentAgent",
]
