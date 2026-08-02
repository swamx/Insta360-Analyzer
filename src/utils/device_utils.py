"""GPU/CPU device detection and management."""

import torch
from typing import Dict, Optional


def get_device_info() -> Dict[str, any]:
    """Get detailed device information."""
    info = {
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }

    if torch.cuda.is_available():
        info["current_device"] = torch.cuda.current_device()
        info["current_device_name"] = torch.cuda.get_device_name()
        info["total_memory_gb"] = torch.cuda.get_device_properties(0).total_memory / 1e9

    info["torch_version"] = torch.__version__
    return info


def get_device() -> torch.device:
    """Get the best available device (GPU or CPU)."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def get_available_memory_gb() -> float:
    """Get available GPU memory in GB."""
    if not torch.cuda.is_available():
        return 0.0
    return torch.cuda.get_device_properties(0).total_memory / 1e9 - (
        torch.cuda.memory_allocated() / 1e9
    )


def get_reserved_memory_gb() -> float:
    """Get reserved (but not used) GPU memory in GB."""
    if not torch.cuda.is_available():
        return 0.0
    return torch.cuda.memory_reserved() / 1e9


def clear_gpu_cache() -> None:
    """Clear GPU cache."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def estimate_batch_size(model_params: int, target_memory_gb: float = 4.0) -> int:
    """Estimate batch size based on available GPU memory and model size."""
    if not torch.cuda.is_available():
        return 1

    available_gb = get_available_memory_gb()
    if available_gb < 1.0:
        return 1

    # Heuristic: model size + overhead per sample
    estimated_batch = max(1, int((available_gb / target_memory_gb) * 16))
    return min(estimated_batch, 64)
