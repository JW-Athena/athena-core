from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict
from uuid import uuid4

from event_bus import event_bus


@dataclass
class MissionExecutionContext:
    mission_id: str = field(default_factory=lambda: str(uuid4()))
    objective_results: Dict[str, Any] = field(default_factory=dict)
    shared_outputs: Dict[str, Any] = field(default_factory=dict)
    capability_cache: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)
    execution_statistics: Dict[str, int] = field(
        default_factory=lambda: {
            "capabilities_requested": 0,
            "capabilities_executed": 0,
            "capabilities_reused": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "execution_time_saved_ms": 0,
        }
    )

    def cache_hit(self, capability: str, objective_id: str = "") -> Dict[str, Any]:
        with self.lock:
            self.execution_statistics["capabilities_requested"] += 1
            if capability not in self.capability_cache:
                self.execution_statistics["cache_misses"] += 1
                event_bus.publish(
                    "MissionCacheMiss",
                    "executive_mission_context",
                    {
                        "mission_id": self.mission_id,
                        "capability": capability,
                        "objective_id": objective_id,
                    },
                )
                return {}

            self.execution_statistics["capabilities_reused"] += 1
            self.execution_statistics["cache_hits"] += 1
            self.execution_statistics["execution_time_saved_ms"] += self._estimated_saved_ms(capability)
            cached = dict(self.capability_cache[capability])

        event_bus.publish(
            "MissionCacheHit",
            "executive_mission_context",
            {
                "mission_id": self.mission_id,
                "capability": capability,
                "objective_id": objective_id,
            },
        )
        return cached

    def store_capability_result(
        self,
        capability: str,
        result: Dict[str, Any],
        objective_id: str = "",
    ) -> None:
        with self.lock:
            self.capability_cache[capability] = dict(result)
            self.execution_statistics["capabilities_executed"] += 1
            if objective_id:
                self.metadata["last_objective_id"] = objective_id

    def store_objective_result(self, objective_id: str, result: Dict[str, Any]) -> None:
        with self.lock:
            self.objective_results[objective_id] = result

    def statistics(self) -> Dict[str, int]:
        with self.lock:
            stats = dict(self.execution_statistics)
        return {
            "capabilities_requested": stats.get("capabilities_requested", 0),
            "executed": stats.get("capabilities_executed", 0),
            "reused": stats.get("capabilities_reused", 0),
            "cache_hits": stats.get("cache_hits", 0),
            "cache_misses": stats.get("cache_misses", 0),
            "execution_time_saved_ms": stats.get("execution_time_saved_ms", 0),
        }

    def _estimated_saved_ms(self, capability: str) -> int:
        estimates = {
            "file_understanding_with_memory": 100,
            "executive_extraction": 150,
            "obligation_extraction": 150,
            "risk_register": 250,
            "executive_decision_brief": 250,
            "executive_action_plan": 300,
            "file_intelligence_loop": 300,
        }
        return estimates.get(capability, 100)
