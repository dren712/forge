import asyncio
from typing import Any, Callable, List
from app.tracing.events import TraceEvent, EventType
from app.provenance.hasher import sign_event, GENESIS_HASH


class EventRecorder:
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.events: List[TraceEvent] = []
        self._last_hash: str = GENESIS_HASH
        self._listeners: List[Callable[[TraceEvent], Any]] = []

    def subscribe(self, callback: Callable[[TraceEvent], Any]) -> None:
        self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[TraceEvent], Any]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def emit(
        self,
        event_type: EventType,
        payload: dict[str, Any],
        generation_id: str | None = None,
        execution_id: str | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            experiment_id=self.experiment_id,
            generation_id=generation_id,
            execution_id=execution_id,
            type=event_type,
            payload=payload,
        )
        # Sign cryptographically
        sign_event(event, self._last_hash)
        self._last_hash = event.event_hash
        self.events.append(event)

        # Notify active streaming listeners
        for listener in list(self._listeners):
            try:
                res = listener(event)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception:
                pass

        return event

    def get_events(self) -> List[TraceEvent]:
        return list(self.events)
