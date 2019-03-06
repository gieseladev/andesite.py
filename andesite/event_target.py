import asyncio
import inspect
import logging
from asyncio import CancelledError, Future
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List, MutableMapping, Optional, TypeVar, Union

__all__ = ["Event", "EventHandler", "EventErrorEvent", "EventFilter", "OneTimeEventListener", "EventListener", "EventTarget"]

log = logging.getLogger(__name__)


class Event:
    """Base type of all events."""
    name: str

    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self.__dict__.update(kwargs)


EventHandler = Callable[[Event], Any]


class EventErrorEvent(Event):
    """Event type passed to `EventTarget.on_event_error`."""
    handler: EventHandler
    exception: Exception
    original_event: Event

    def __init__(self, handler: EventHandler, exception: Exception, original_event: Event) -> None:
        super().__init__("event_error", handler=handler, exception=exception, original_event=original_event)


EventFilter = Callable[[Event], bool]


@dataclass()
class OneTimeEventListener:
    """One-time event listener.

    Special event listener which waits for the first event matching the conditions and then removes itself.
    """
    future: Future
    condition: Optional[EventFilter] = None


@dataclass()
class EventListener:
    """Persistent event listener"""
    handler: EventHandler


T = TypeVar("T")


def _push_map_list(mapping: MutableMapping[str, List[T]], key: str, item: T) -> None:
    try:
        items = mapping[key]
    except KeyError:
        mapping[key] = [item]
    else:
        items.append(item)


class EventTarget:
    """An object that can dispatch `Event`s."""
    _one_time_listeners: Dict[str, List[OneTimeEventListener]]
    _listeners: Dict[str, List[EventListener]]

    def __init__(self) -> None:
        self._one_time_listeners = {}
        self._listeners = {}

    def wait_for(self, event: str, *, check: EventFilter, timeout: float = None) -> Future[Optional[Event]]:
        """Return a future which resolves when an `Event` meeting the given conditions is dispatched."""
        future = Future()
        listener = OneTimeEventListener(future, check)

        _push_map_list(self._one_time_listeners, event, listener)

        return asyncio.wait_for(future, timeout=timeout)

    def add_listener(self, event: str, listener: Union[EventHandler, EventListener]) -> EventListener:
        """Add a listener for an `Event` which is called whenever said event is dispatched."""
        if not isinstance(listener, EventListener):
            listener = EventListener(listener)

        _push_map_list(self._listeners, event, listener)
        return listener

    def remove_listener(self, event: str, target: Union[EventHandler, EventListener]) -> bool:
        """Remove a previously added event listener.

        When a `EventHandler` is passed, all event listeners with the given handler are removed.

        Returns:
            bool: Whether the listener was successfully removed.
        """
        try:
            listeners = self._listeners[event]
        except KeyError:
            return False

        if isinstance(target, EventListener):
            try:
                listeners.remove(target)
                return True
            except ValueError:
                return False

        removed_some: bool = False
        for i, listener in reversed(listeners):
            if listener.handler == target:
                del listeners[i]
                removed_some = True

        return removed_some

    def dispatch(self, event: Event) -> Optional[Future]:
        """Dispatch an event.

        Returns:
            Optional[Future]: Future aggregating all asynchronous dispatches.
                Can be awaited to make sure all handlers have been executed.
        """
        log.debug("dispatching", event)

        futures: List[Union[Coroutine, Future]] = []
        event_name = event.name

        one_time_listeners = self._one_time_listeners.get(event_name)
        if one_time_listeners:
            to_remove: List[int] = []

            for i, listener in enumerate(one_time_listeners):
                future = listener.future
                if future.cancelled():
                    to_remove.append(i)
                    continue

                condition = listener.condition
                if condition:
                    try:
                        res = condition(event)
                    except Exception as e:
                        res = False
                        future.set_exception(e)
                        to_remove.append(i)
                else:
                    res = True

                if res:
                    future.set_result(event)
                    to_remove.append(i)

            if len(to_remove) == len(one_time_listeners):
                one_time_listeners.clear()
            else:
                for i in reversed(to_remove):
                    del one_time_listeners[i]

        try:
            method = getattr(self, f"on_{event_name}")
        except AttributeError:
            pass
        else:
            futures.append(self._run_event(method, event))

        listeners = self._listeners.get(event_name)
        if listeners:
            for listener in listeners:
                futures.append(self._run_event(listener.handler, event))

        if futures:
            return asyncio.gather(*futures)
        else:
            return None

    async def _run_event(self, method: EventHandler, event: Event):
        try:
            if inspect.iscoroutine(method):
                await method(event)
            else:
                method(event)
        except CancelledError:
            pass
        except Exception as e:
            error_event = EventErrorEvent(method, e, event)

            with suppress(CancelledError):
                await self.on_event_error(error_event)

    # noinspection PyMethodMayBeStatic
    async def on_event_error(self, event: EventErrorEvent) -> None:
        """Called when an error occurs during event dispatching."""
        log.exception(f"There was an error when {event.handler} handled {event.original_event}: {event.exception}")
