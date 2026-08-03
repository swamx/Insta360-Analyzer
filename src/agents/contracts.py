"""Agent contracts and protocols for ReACT reasoning."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ============================================================================
# Enums & Protocols
# ============================================================================

class AgentRole(str, Enum):
    """Agent roles in the system."""
    REASONER = "reasoner"      # Analyzes and reasons about quality
    ACTOR = "actor"            # Takes actions to improve quality
    ORCHESTRATOR = "orchestrator"  # Coordinates other agents
    VALIDATOR = "validator"    # Validates outcomes


class ActionType(str, Enum):
    """Types of actions agents can take."""
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    REGENERATE = "regenerate"
    FEEDBACK_COLLECT = "feedback_collect"
    LEARN = "learn"
    COMPARE = "compare"
    REPORT = "report"


# ============================================================================
# Agent State & Context
# ============================================================================

@dataclass
class AgentMemory:
    """Agent working memory."""

    thoughts: List[str] = field(default_factory=list)
    observations: Dict[str, Any] = field(default_factory=dict)
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    outcomes: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def add_thought(self, thought: str) -> None:
        """Add reasoning thought."""
        self.thoughts.append(thought)

    def add_observation(self, key: str, value: Any) -> None:
        """Record observation."""
        self.observations[key] = value

    def add_action(self, action: str, params: Dict[str, Any]) -> None:
        """Record action taken."""
        self.actions_taken.append({"action": action, "params": params})

    def add_error(self, error: str) -> None:
        """Record error."""
        self.errors.append(error)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "thoughts": self.thoughts,
            "observations": self.observations,
            "actions_taken": self.actions_taken,
            "outcomes": self.outcomes,
            "error_count": len(self.errors),
        }


@dataclass
class ExecutionContext:
    """Shared context between agents."""

    file_id: str
    video_path: str
    stage: str  # Current stage
    timestamp: datetime = field(default_factory=datetime.now)

    # Shared state
    reel_config: Dict[str, Any] = field(default_factory=dict)
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    feedback_collected: List[Dict[str, Any]] = field(default_factory=list)
    quality_score: float = 0.0

    # Agent memories
    reasoner_memory: AgentMemory = field(default_factory=AgentMemory)
    actor_memory: AgentMemory = field(default_factory=AgentMemory)

    def update_quality_score(self, score: float) -> None:
        """Update overall quality score."""
        self.quality_score = max(0.0, min(10.0, score))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_id": self.file_id,
            "video_path": self.video_path,
            "stage": self.stage,
            "quality_score": self.quality_score,
            "feedback_count": len(self.feedback_collected),
            "reasoner_memory": self.reasoner_memory.to_dict(),
            "actor_memory": self.actor_memory.to_dict(),
        }


# ============================================================================
# Agent Contracts
# ============================================================================

class ReasonerContract(ABC):
    """Contract for Reasoner agents."""

    @abstractmethod
    def reason(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Reason about current state.

        Returns:
            {
                "thoughts": [thoughts],
                "observations": {observations},
                "diagnosis": "issue description",
                "confidence": 0.0-1.0,
                "next_step": "recommended action"
            }
        """
        pass

    @abstractmethod
    def evaluate(self, context: ExecutionContext, results: Dict[str, Any]) -> float:
        """
        Evaluate quality of results.

        Args:
            context: Execution context
            results: Results to evaluate

        Returns:
            Quality score 0.0-10.0
        """
        pass


class ActorContract(ABC):
    """Contract for Actor agents."""

    @abstractmethod
    def act(self, context: ExecutionContext, reasoning: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take action based on reasoning.

        Args:
            context: Execution context
            reasoning: Output from reasoner

        Returns:
            {
                "action_type": ActionType,
                "action": "what was done",
                "result": "outcome",
                "success": bool,
                "feedback": "notes on action"
            }
        """
        pass

    @abstractmethod
    def can_act(self, action_type: ActionType) -> bool:
        """Check if agent can perform action."""
        pass


class OrchestratorContract(ABC):
    """Contract for Orchestrator agents."""

    @abstractmethod
    def orchestrate(
        self,
        context: ExecutionContext,
        reasoner: ReasonerContract,
        actor: ActorContract,
    ) -> Dict[str, Any]:
        """
        Orchestrate reasoning and acting cycle.

        Returns:
            Final results and recommendations
        """
        pass

    @abstractmethod
    def should_iterate(self, context: ExecutionContext) -> bool:
        """Decide if another cycle needed."""
        pass


# ============================================================================
# ReACT Agent Protocol
# ============================================================================

class ReActStep(BaseModel):
    """Single ReACT step."""

    step_num: int
    phase: str  # "thought", "action", "observation"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ReActTrace(BaseModel):
    """Complete ReACT execution trace."""

    agent_id: str
    steps: List[ReActStep] = Field(default_factory=list)
    final_answer: str = ""
    success: bool = False
    score: float = 0.0

    def add_step(self, phase: str, content: str) -> None:
        """Add step to trace."""
        step = ReActStep(
            step_num=len(self.steps) + 1,
            phase=phase,
            content=content,
        )
        self.steps.append(step)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "step_count": len(self.steps),
            "phases": [s.phase for s in self.steps],
            "final_answer": self.final_answer,
            "success": self.success,
            "score": self.score,
        }


# ============================================================================
# Quality Metrics Contract
# ============================================================================

class QualityMetrics(BaseModel):
    """Quality metrics for reel."""

    overall_score: float = Field(ge=0.0, le=10.0)
    criteria_scores: Dict[str, float] = Field(default_factory=dict)
    issues_found: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    def to_feedback(self) -> Dict[str, Any]:
        """Convert to feedback format."""
        return {
            "rating": int(self.overall_score),
            "criteria": self.criteria_scores,
            "issues": self.issues_found,
            "suggestions": self.recommendations,
            "confidence": self.confidence,
        }


class QualityAssuranceContract(ABC):
    """Contract for QA agents."""

    @abstractmethod
    def assess_quality(self, context: ExecutionContext) -> QualityMetrics:
        """Assess reel quality."""
        pass

    @abstractmethod
    def identify_issues(self, context: ExecutionContext) -> List[str]:
        """Identify quality issues."""
        pass

    @abstractmethod
    def recommend_improvements(self, context: ExecutionContext) -> List[str]:
        """Recommend improvements."""
        pass


# ============================================================================
# State Transfer Contract
# ============================================================================

class StateTransfer(BaseModel):
    """Transfer state between agents/cycles."""

    source_agent: str
    target_agent: str
    timestamp: datetime = Field(default_factory=datetime.now)
    state: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def merge(self, other: "StateTransfer") -> "StateTransfer":
        """Merge with another state transfer."""
        merged_state = {**self.state, **other.state}
        return StateTransfer(
            source_agent=self.source_agent,
            target_agent=other.target_agent,
            state=merged_state,
            metadata={**self.metadata, **other.metadata},
        )


class StateCacheContract(ABC):
    """Contract for state caching."""

    @abstractmethod
    def cache_state(self, key: str, state: Dict[str, Any]) -> None:
        """Cache state."""
        pass

    @abstractmethod
    def retrieve_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached state."""
        pass

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear cache."""
        pass

    @abstractmethod
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass
