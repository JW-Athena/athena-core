from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
import builtins


class AthenaEventBus:
    """
    Simple in-memory ATHENA Event Bus.

    Publishes significant ATHENA activities for future agents to consume. This
    implementation does not execute actions or use external message queues.
    """

    def __init__(self, max_events: int = 250):
        self.max_events = max_events
        if not hasattr(builtins, "_ATHENA_EVENT_BUS_EVENTS"):
            builtins._ATHENA_EVENT_BUS_EVENTS = []
        self._events: List[Dict[str, Any]] = builtins._ATHENA_EVENT_BUS_EVENTS

    def publish(
        self,
        event_type: str,
        source: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        event = {
            "id": str(uuid4()),
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "payload": payload or {},
        }
        self._events.append(event)
        if len(self._events) > self.max_events:
            del self._events[:-self.max_events]
        return dict(event)

    def latest(self, limit: int = 100) -> List[Dict[str, Any]]:
        safe_limit = max(1, min(int(limit or 100), self.max_events))
        return [dict(event) for event in self._events[-safe_limit:]]


event_bus = AthenaEventBus()
