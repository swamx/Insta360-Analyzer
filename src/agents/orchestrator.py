"""Haystack-based orchestration and state management."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import OrderedDict

from src.utils.logger import get_logger
from .contracts import (
    ExecutionContext,
    ReasonerContract,
    ActorContract,
    OrchestratorContract,
    ReActTrace,
    StateTransfer,
    StateCacheContract,
    ActionType,
)

logger = get_logger("agents.orchestrator")


# ============================================================================
# State Cache Implementation
# ============================================================================

class InMemoryStateCache(StateCacheContract):
    """In-memory state cache with LRU eviction."""

    def __init__(self, max_size: int = 100):
        """Initialize cache."""
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def cache_state(self, key: str, state: Dict[str, Any]) -> None:
        """Cache state."""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Evict oldest (least recently used)
                self.cache.popitem(last=False)

        self.cache[key] = {
            "timestamp": datetime.now().isoformat(),
            "data": state,
        }

        logger.debug(f"Cached state: {key}")

    def retrieve_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached state."""
        if key in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]["data"]

        self.misses += 1
        return None

    def clear_cache(self) -> None:
        """Clear cache."""
        self.cache.clear()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


class PersistentStateCache(StateCacheContract):
    """Persistent state cache using JSON files."""

    def __init__(self, cache_dir: Path):
        """Initialize persistent cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_cache: Dict[str, Dict[str, Any]] = {}

    def cache_state(self, key: str, state: Dict[str, Any]) -> None:
        """Cache state to disk and memory."""
        self.memory_cache[key] = state

        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "data": state,
                }, f, indent=2)
            logger.debug(f"Persisted state: {cache_file}")
        except Exception as e:
            logger.error(f"Failed to persist state: {str(e)}")

    def retrieve_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve from memory or disk."""
        if key in self.memory_cache:
            return self.memory_cache[key]

        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    self.memory_cache[key] = data["data"]
                    return data["data"]
            except Exception as e:
                logger.error(f"Failed to load state: {str(e)}")

        return None

    def clear_cache(self) -> None:
        """Clear cache."""
        self.memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.info("Cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_files = list(self.cache_dir.glob("*.json"))
        return {
            "memory_cache_size": len(self.memory_cache),
            "disk_cache_files": len(cache_files),
            "cache_dir": str(self.cache_dir),
        }


# ============================================================================
# ReACT Orchestrator
# ============================================================================

class ReActOrchestrator(OrchestratorContract):
    """ReACT orchestrator with Haystack integration."""

    def __init__(
        self,
        reasoner: ReasonerContract,
        actor: ActorContract,
        state_cache: Optional[StateCacheContract] = None,
        max_iterations: int = 5,
    ):
        """Initialize orchestrator."""
        self.reasoner = reasoner
        self.actor = actor
        self.state_cache = state_cache or InMemoryStateCache()
        self.max_iterations = max_iterations
        self.traces: List[ReActTrace] = []

    def orchestrate(
        self,
        context: ExecutionContext,
        reasoner: Optional[ReasonerContract] = None,
        actor: Optional[ActorContract] = None,
    ) -> Dict[str, Any]:
        """
        Execute ReACT loop.

        Thought → Action → Observation → (repeat until done or max iterations)
        """
        reasoner = reasoner or self.reasoner
        actor = actor or self.actor

        logger.info(f"Starting ReACT orchestration: {context.file_id}")

        trace = ReActTrace(agent_id=f"react_{context.file_id}")
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"ReACT iteration {iteration}/{self.max_iterations}")

            # Phase 1: Thought (Reasoning)
            trace.add_step("thought", f"Analyzing state at iteration {iteration}")
            context.reasoner_memory.add_thought(f"Iteration {iteration} starting")

            reasoning = reasoner.reason(context)
            trace.add_step("thought", json.dumps(reasoning, indent=2))

            # Check if diagnosis clear
            if reasoning.get("confidence", 0) < 0.5:
                trace.add_step("thought", "Low confidence in diagnosis, need more information")
                continue

            # Phase 2: Action
            trace.add_step("action", f"Executing: {reasoning.get('next_step')}")

            action_result = actor.act(context, reasoning)
            trace.add_step("observation", json.dumps(action_result, indent=2))

            # Cache state after action
            state_key = f"{context.file_id}_iteration_{iteration}"
            self.state_cache.cache_state(state_key, {
                "context": context.to_dict(),
                "reasoning": reasoning,
                "action_result": action_result,
            })

            # Phase 3: Observe & Evaluate
            quality_score = reasoner.evaluate(context, action_result)
            context.update_quality_score(quality_score)

            trace.add_step("observation", f"Quality score: {quality_score}/10")

            # Check if should continue
            if not self.should_iterate(context):
                logger.info(f"Stopping at iteration {iteration}: quality threshold met")
                break

            # Check if action successful
            if not action_result.get("success", False):
                logger.warning(f"Action failed at iteration {iteration}")
                trace.add_step("thought", "Previous action failed, trying different approach")
                continue

        # Final evaluation
        trace.final_answer = f"Completed {iteration} iterations, quality score: {context.quality_score:.1f}/10"
        trace.success = context.quality_score >= 7.0
        trace.score = context.quality_score

        self.traces.append(trace)

        logger.info(f"ReACT orchestration complete: {trace.final_answer}")

        return {
            "success": trace.success,
            "iterations": iteration,
            "quality_score": context.quality_score,
            "trace": trace.to_dict(),
            "context": context.to_dict(),
            "cache_stats": self.state_cache.get_cache_stats(),
        }

    def should_iterate(self, context: ExecutionContext) -> bool:
        """Decide if another iteration needed."""
        # Stop if quality is good
        if context.quality_score >= 8.0:
            return False

        # Stop if no improvements from feedback
        if len(context.feedback_collected) >= 5:
            avg_rating = sum(
                f.get("rating", 0) for f in context.feedback_collected
            ) / len(context.feedback_collected)
            if avg_rating >= 4.0:
                return False

        return True

    def get_execution_trace(self, iteration: int = -1) -> Optional[ReActTrace]:
        """Get execution trace."""
        if not self.traces:
            return None
        return self.traces[iteration]


# ============================================================================
# Haystack Pipeline Integration
# ============================================================================

class HaystackPipelineState:
    """Haystack pipeline state management."""

    def __init__(self, state_cache: StateCacheContract):
        """Initialize pipeline state."""
        self.state_cache = state_cache
        self.current_state: Dict[str, Any] = {}

    def update(self, **kwargs) -> None:
        """Update pipeline state."""
        self.current_state.update(kwargs)

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from state."""
        return self.current_state.get(key, default)

    def cache_checkpoint(self, checkpoint_id: str) -> None:
        """Cache current state as checkpoint."""
        self.state_cache.cache_state(checkpoint_id, self.current_state.copy())
        logger.info(f"Cached checkpoint: {checkpoint_id}")

    def load_checkpoint(self, checkpoint_id: str) -> bool:
        """Load state from checkpoint."""
        state = self.state_cache.retrieve_state(checkpoint_id)
        if state:
            self.current_state = state
            logger.info(f"Loaded checkpoint: {checkpoint_id}")
            return True
        logger.warning(f"Checkpoint not found: {checkpoint_id}")
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.current_state.copy()


class PipelineOrchestrator:
    """Orchestrate complete pipeline with state management."""

    def __init__(
        self,
        reasoner: ReasonerContract,
        actor: ActorContract,
        cache_dir: Optional[Path] = None,
    ):
        """Initialize pipeline orchestrator."""
        state_cache = (
            PersistentStateCache(cache_dir)
            if cache_dir
            else InMemoryStateCache()
        )

        self.react_orchestrator = ReActOrchestrator(
            reasoner,
            actor,
            state_cache,
            max_iterations=5,
        )

        self.pipeline_state = HaystackPipelineState(state_cache)
        self.state_cache = state_cache

    def run_pipeline(self, context: ExecutionContext) -> Dict[str, Any]:
        """Run complete pipeline."""
        logger.info(f"Starting pipeline: {context.file_id}")

        # Create checkpoint ID
        checkpoint_id = f"pipeline_{context.file_id}"

        # Check if resuming
        if self.pipeline_state.load_checkpoint(checkpoint_id):
            logger.info(f"Resuming from checkpoint: {checkpoint_id}")

        # Update pipeline state
        self.pipeline_state.update(
            file_id=context.file_id,
            video_path=context.video_path,
            started_at=datetime.now().isoformat(),
        )

        # Run ReACT orchestration
        react_result = self.react_orchestrator.orchestrate(context)

        # Update state with results
        self.pipeline_state.update(
            react_result=react_result,
            completed_at=datetime.now().isoformat(),
            final_score=context.quality_score,
        )

        # Cache final state
        self.pipeline_state.cache_checkpoint(checkpoint_id)

        logger.info(f"Pipeline complete: {context.file_id}")

        return {
            "pipeline_state": self.pipeline_state.to_dict(),
            "react_result": react_result,
            "cache_stats": self.state_cache.get_cache_stats(),
        }

    def get_state(self) -> Dict[str, Any]:
        """Get current pipeline state."""
        return self.pipeline_state.to_dict()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.state_cache.get_cache_stats()

    def clear_cache(self) -> None:
        """Clear cache."""
        self.state_cache.clear_cache()
        logger.info("Cache cleared")
