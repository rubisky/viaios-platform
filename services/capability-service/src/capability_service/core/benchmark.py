"""Benchmark engine for AI model performance evaluation."""
from __future__ import annotations

import time
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""
    model_id: str = ""
    warmup_iterations: int = 10
    benchmark_iterations: int = 100
    batch_sizes: list[int] = field(default_factory=lambda: [1, 4, 8])
    input_shape: str = "auto"
    timeout_seconds: int = 300


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    benchmark_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    model_id: str = ""
    model_name: str = ""
    framework: str = ""
    task: str = ""

    # Timing
    avg_latency_ms: float = 0
    p50_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    min_latency_ms: float = 0
    max_latency_ms: float = 0

    # Throughput
    throughput_per_second: float = 0
    batch_size: int = 1

    # Memory
    gpu_memory_used_mb: int = 0
    cpu_memory_used_mb: int = 0

    # Status
    success: bool = True
    error_message: Optional[str] = None
    completed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "framework": self.framework,
            "task": self.task,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "throughput_per_second": self.throughput_per_second,
            "batch_size": self.batch_size,
            "gpu_memory_used_mb": self.gpu_memory_used_mb,
            "cpu_memory_used_mb": self.cpu_memory_used_mb,
            "success": self.success,
            "error_message": self.error_message,
            "completed_at": self.completed_at,
        }


class BenchmarkEngine:
    """Runs performance benchmarks on AI models.

    Measures latency (avg, P50, P95, P99), throughput, and memory usage.
    Supports configurable warmup and benchmark iterations.
    """

    def __init__(self):
        self._results: dict[str, list[BenchmarkResult]] = {}

    def run_benchmark(
        self,
        model_id: str,
        model_name: str,
        framework: str,
        task: str,
        inference_fn,
        config: Optional[BenchmarkConfig] = None,
    ) -> BenchmarkResult:
        """Run a benchmark on a model using the provided inference function.

        Args:
            model_id: Unique model identifier
            model_name: Human-readable model name
            framework: Model framework (ONNX, TensorRT, PyTorch, etc.)
            task: Task type (detection, classification, etc.)
            inference_fn: Callable that takes a batch and returns results
            config: Benchmark configuration

        Returns:
            BenchmarkResult with all performance metrics
        """
        if config is None:
            config = BenchmarkConfig(model_id=model_id)

        result = BenchmarkResult(
            model_id=model_id,
            model_name=model_name,
            framework=framework,
            task=task,
            batch_size=config.batch_sizes[0],
        )

        try:
            # Warmup phase
            for _ in range(config.warmup_iterations):
                inference_fn()

            # Benchmark phase
            latencies: list[float] = []
            start_time = time.perf_counter()

            for i in range(config.benchmark_iterations):
                t0 = time.perf_counter()
                inference_fn()
                latencies.append((time.perf_counter() - t0) * 1000)  # ms

            elapsed = time.perf_counter() - start_time

            # Calculate statistics
            sorted_latencies = sorted(latencies)
            result.avg_latency_ms = statistics.mean(latencies)
            result.p50_latency_ms = sorted_latencies[len(sorted_latencies) // 2]
            result.p95_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            result.p99_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.99)]
            result.min_latency_ms = sorted_latencies[0]
            result.max_latency_ms = sorted_latencies[-1]
            result.throughput_per_second = config.benchmark_iterations / elapsed
            result.success = True

        except Exception as e:
            result.success = False
            result.error_message = str(e)

        # Store result
        if model_id not in self._results:
            self._results[model_id] = []
        self._results[model_id].append(result)

        return result

    def quick_benchmark(self, model_id: str, model_name: str, framework: str,
                        task: str, inference_fn) -> BenchmarkResult:
        """Run a quick 20-iteration benchmark for rapid evaluation."""
        config = BenchmarkConfig(
            model_id=model_id,
            warmup_iterations=3,
            benchmark_iterations=20,
        )
        return self.run_benchmark(model_id, model_name, framework, task, inference_fn, config)

    def get_results(self, model_id: str) -> list[BenchmarkResult]:
        """Get all benchmark results for a model."""
        return self._results.get(model_id, [])

    def compare_models(self, model_ids: list[str]) -> dict[str, Any]:
        """Compare benchmark results across multiple models.

        Returns a comparison dict with each model's key metrics side by side.
        """
        comparison = {"models": [], "metrics": {}}

        for mid in model_ids:
            results = self._results.get(mid, [])
            if not results:
                continue
            latest = results[-1]
            comparison["models"].append({
                "model_id": latest.model_id,
                "model_name": latest.model_name,
                "framework": latest.framework,
                "task": latest.task,
                "avg_latency_ms": latest.avg_latency_ms,
                "p95_latency_ms": latest.p95_latency_ms,
                "throughput_per_second": latest.throughput_per_second,
            })

        # Find best in each category
        if comparison["models"]:
            best_latency = min(comparison["models"], key=lambda m: m["avg_latency_ms"])
            best_throughput = max(comparison["models"], key=lambda m: m["throughput_per_second"])
            comparison["best_latency"] = best_latency["model_name"]
            comparison["best_throughput"] = best_throughput["model_name"]

        return comparison

    def list_all_results(self) -> dict[str, list[dict]]:
        """Get all benchmark results for all models."""
        return {
            mid: [r.to_dict() for r in results]
            for mid, results in self._results.items()
        }


# Global singleton
benchmark_engine = BenchmarkEngine()
