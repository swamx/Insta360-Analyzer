"""Analytics flow orchestration and execution engine."""

import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from src.utils.logger import get_logger
from .core import (
    AnalyticsFlow,
    AnalysisInput,
    AnalysisOutput,
    AnalyticsComponent,
    FlowExecutor,
    AnalyticsConfig,
    PerformanceMetrics,
    ExecutionStats,
)

logger = get_logger("analytics.flow")


class FlowExecutorImpl(FlowExecutor):
    """Concrete implementation of flow executor."""

    def __init__(self, flow: AnalyticsFlow):
        """Initialize flow executor."""
        super().__init__(flow)
        self.metrics: List[PerformanceMetrics] = []

    def register_component(self, name: str, component: AnalyticsComponent) -> None:
        """Register component for execution."""
        if not isinstance(component, AnalyticsComponent):
            raise TypeError(f"Component {name} must be AnalyticsComponent subclass")

        self.components[name] = component
        logger.info(f"Registered component: {name} ({component.__class__.__name__})")

    def execute(self, input_data: AnalysisInput) -> Dict[str, AnalysisOutput]:
        """
        Execute flow with given input.

        Args:
            input_data: Input for flow

        Returns:
            Results from all nodes
        """
        start_time = datetime.now()
        logger.info(f"Starting flow: {self.flow.name}")

        # Validate flow
        if not self.validate_flow():
            raise ValueError("Flow validation failed")

        # Get execution order
        execution_order = self.flow.get_execution_order()
        logger.info(f"Execution order: {execution_order}")

        # Execute nodes
        node_inputs = {None: input_data}  # Start with original input
        results = {}

        for node_name in execution_order:
            node = self.flow.get_node(node_name)
            if not node or not node.enabled:
                continue

            logger.info(f"Executing node: {node_name}")

            # Get component
            if node_name not in self.components:
                logger.error(f"Component not registered: {node_name}")
                continue

            component = self.components[node_name]

            # Get input for this node
            if node.input_from is None:
                node_input = input_data
            else:
                if node.input_from not in results:
                    logger.error(f"Input node not found: {node.input_from}")
                    continue
                # Use output from previous node as input
                node_input = self._convert_output_to_input(
                    results[node.input_from], input_data
                )

            # Execute node
            try:
                start = time.time()
                result = component.process(node_input)
                elapsed_ms = (time.time() - start) * 1000

                results[node_name] = result
                logger.info(f"Node {node_name} completed: {result.decision} (confidence: {result.confidence:.2f})")

                # Record metrics
                metrics = PerformanceMetrics(
                    component_name=node_name,
                    execution_time_ms=elapsed_ms,
                    success=True,
                )
                self.metrics.append(metrics)

            except Exception as e:
                logger.error(f"Node {node_name} failed: {str(e)}")

                if self.flow.flow_config.stop_on_error:
                    raise

                # Record error metrics
                metrics = PerformanceMetrics(
                    component_name=node_name,
                    execution_time_ms=0.0,
                    success=False,
                    error_message=str(e),
                )
                self.metrics.append(metrics)

        end_time = datetime.now()
        logger.info(f"Flow completed: {self.flow.name}")

        return results

    def validate_flow(self) -> bool:
        """Validate flow configuration."""
        logger.info("Validating flow...")

        # Check all nodes have components
        for node in self.flow.nodes:
            if node.enabled and node.name not in self.components:
                logger.warning(f"Component not registered for node: {node.name}")

        # Check dependency chain is valid
        for node in self.flow.nodes:
            if node.input_from:
                if not self.flow.get_node(node.input_from):
                    logger.error(f"Input node not found: {node.input_from}")
                    return False

        logger.info("Flow validation passed")
        return True

    @staticmethod
    def _convert_output_to_input(
        output: AnalysisOutput, original_input: AnalysisInput
    ) -> AnalysisInput:
        """Convert component output to input for next component."""
        # Create new input with output results as metadata
        new_input = AnalysisInput(
            file_id=original_input.file_id,
            file_path=original_input.file_path,
            scene_id=original_input.scene_id,
            metadata={
                "previous_decision": output.decision,
                "previous_confidence": output.confidence,
                "previous_results": output.results,
                **original_input.metadata,
            },
        )
        return new_input


class FlowBuilder:
    """Builder pattern for creating analytics flows."""

    def __init__(self, name: str):
        """Initialize flow builder."""
        self.name = name
        self.description = ""
        self.nodes: List[Dict[str, Any]] = []
        self.flow_config = AnalyticsConfig()
        self.current_node: Optional[str] = None

    def with_description(self, description: str) -> "FlowBuilder":
        """Add flow description."""
        self.description = description
        return self

    def add_node(
        self,
        name: str,
        component_type: str,
        input_from: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> "FlowBuilder":
        """Add node to flow."""
        self.nodes.append({
            "name": name,
            "component_type": component_type,
            "input_from": input_from,
            "config": config or {},
            "enabled": True,
        })
        self.current_node = name
        logger.info(f"Added node: {name} ({component_type})")
        return self

    def configure_analytics(self, config: AnalyticsConfig) -> "FlowBuilder":
        """Set analytics configuration."""
        self.flow_config = config
        return self

    def build(self) -> AnalyticsFlow:
        """Build flow configuration."""
        from .core import AnalyticsNode, FlowConfig

        nodes = [AnalyticsNode(**node_config) for node_config in self.nodes]

        flow = AnalyticsFlow(
            name=self.name,
            description=self.description,
            nodes=nodes,
            flow_config=FlowConfig(name=self.name),
        )

        logger.info(f"Built flow: {self.name} with {len(nodes)} nodes")
        return flow


class FlowRegistry:
    """Registry for managing multiple flows."""

    def __init__(self):
        """Initialize flow registry."""
        self.flows: Dict[str, AnalyticsFlow] = {}
        self.executors: Dict[str, FlowExecutorImpl] = {}

    def register_flow(self, flow: AnalyticsFlow) -> None:
        """Register flow."""
        self.flows[flow.name] = flow
        self.executors[flow.name] = FlowExecutorImpl(flow)
        logger.info(f"Registered flow: {flow.name}")

    def get_flow(self, name: str) -> Optional[AnalyticsFlow]:
        """Get flow by name."""
        return self.flows.get(name)

    def get_executor(self, name: str) -> Optional[FlowExecutorImpl]:
        """Get executor for flow."""
        return self.executors.get(name)

    def list_flows(self) -> List[str]:
        """List all registered flows."""
        return list(self.flows.keys())

    def execute_flow(self, flow_name: str, input_data: AnalysisInput) -> Dict[str, AnalysisOutput]:
        """Execute registered flow."""
        executor = self.get_executor(flow_name)
        if not executor:
            raise ValueError(f"Flow not found: {flow_name}")

        return executor.execute(input_data)


# ============================================================================
# Predefined Flows
# ============================================================================

def create_insta360_perspective_flow() -> AnalyticsFlow:
    """Create flow for 360° perspective selection."""
    builder = FlowBuilder("insta360_perspective_selection")
    builder.with_description("Detect Insta360 format and select best perspective")
    builder.add_node("format_detector", "detector")
    builder.add_node("frame_analyzer", "analyzer", input_from="format_detector")
    builder.add_node("perspective_selector", "selector", input_from="frame_analyzer")
    return builder.build()


def create_scene_analytics_flow() -> AnalyticsFlow:
    """Create flow for scene analytics."""
    builder = FlowBuilder("scene_analytics")
    builder.with_description("Analyze scene: subjects, scenery, composition")
    builder.add_node("subject_detector", "detector")
    builder.add_node("scenery_analyzer", "analyzer", input_from="subject_detector")
    builder.add_node("composition_scorer", "scorer", input_from="scenery_analyzer")
    return builder.build()


def create_full_analytics_flow() -> AnalyticsFlow:
    """Create comprehensive flow combining all analytics."""
    builder = FlowBuilder("full_analytics")
    builder.with_description("Complete analytics pipeline")

    # Stage 0.5: Insta360 handling
    builder.add_node("format_detector", "detector")
    builder.add_node("perspective_selector", "selector", input_from="format_detector")

    # Stage 3: Scene analytics
    builder.add_node("subject_detector", "detector", input_from="perspective_selector")
    builder.add_node("scenery_analyzer", "analyzer", input_from="subject_detector")
    builder.add_node("composition_scorer", "scorer", input_from="scenery_analyzer")

    return builder.build()
