"""Event dispatching and listening."""

import asyncio
import inspect
import logging
from asyncio import AbstractEventLoop, CancelledError, Future
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Coroutine, Dict, List, MutableMapping, Optional, TypeVar, Union, overload

__all__ = ["Event", "EventHandler", "EventErrorEvent", "EventFilter", "OneTimeEventListener", "EventListener", "EventTarget"]

log = logging.getLogger(__name__)


class Event:
    """Base type of all events.

    Attributes:
        name (str): Name of the event.
    """
    name: str

    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self.__dict__.update(kwargs)


EventHandler = Callable[[Event], Any]


class EventErrorEvent(Event):
    """Event type passed to `EventTarget.on_event_error`.

    Attributes:
        handler (EventHandler): Callback that received the event.
        exception (Exception): Error that was raised by the handler.
        original_event (Event): Event that was to be dispatched but caused an error.
    """
    handler: EventHandler
    exception: Exception
    original_event: Event

    def __init__(self, handler: EventHandler, exception: Exception, original_event: Event) -> None:
        super().__init__("event_error", handler=handler, exception=exception, original_event=original_event)


EventFilter = Callable[[Event], bool]


# noinspection PyUnresolvedReferences
@dataclass()
class OneTimeEventListener:
    """One-time event listener.

    Special event listener which waits for the first event matching the conditions and then removes itself.

    Attributes:
        future (Future): Future that was returned to the callee and is used
            to communicate.
            When an event occurs which meets the conditions it is set
            as the result of this future. If an error occurs, it is
            set as the exception.
        condition (Optional[EventFilter): Callback which takes an `Event` and returns `True`
            to accept the event and `False` otherwise.
            If not provided, all events are accepted.
    """
    future: Future
    condition: Optional[EventFilter] = None


# noinspection PyUnresolvedReferences
@dataclass()
class EventListener:
    """Persistent event listener.

    Attributes:
        handler (EventHandler): Callback which will be called whenever an event occurs.
    """
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
    """An object that can dispatch `Event` instances to listeners.

    Args:
        loop: You can specify the loop which will be used for various asynchronous actions.
            If you don't specify a loop, it will be dynamically retrieved when needed.
    """
    _one_time_listeners: Dict[str, List[OneTimeEventListener]]
    _listeners: Dict[str, List[EventListener]]

    _loop: Optional[AbstractEventLoop]

    def __init__(self, *, loop: AbstractEventLoop = None) -> None:
        self._loop = loop
        self._one_time_listeners = {}
        self._listeners = {}

    @overload
    def wait_for(self, event: str, *, check: EventFilter) -> Awaitable[Event]:
        ...

    @overload
    def wait_for(self, event: str, *, check: EventFilter, timeout: float) -> Awaitable[Optional[Event]]:
        ...

    def wait_for(self, event: str, *, check: EventFilter, timeout: float = None) -> Awaitable[Optional[Event]]:
        """Wait for an event to be dispatched.

        This is similar to adding a listener, but it only listens once and
        returns the event that was dispatched instead of calling a callback.

        Args:
            event: Name of the event to listen to
            check: Callback which takes an `Event` and returns `True`
                to accept the event and `False` otherwise.
                If not provided, all events are accepted.
            timeout: Amount of seconds to wait before aborting.
                If not provided it will wait forever.

        Returns:
            `Future` which when awaited yields the event.
            If a timeout was given the result will be `None`
            if it timed-out.
        """
        # not using self._loop.create_future because loop may be None
        future = Future(loop=self._loop)
        listener = OneTimeEventListener(future, check)

        _push_map_list(self._one_time_listeners, event, listener)

        return asyncio.wait_for(future, timeout=timeout, loop=self._loop)

    def add_listener(self, event: str, listener: Union[EventHandler, EventListener]) -> EventListener:
        """Add a listener for an `Event` which is called whenever said event is dispatched.

        Args:
            event: Name of the event to listen to
            listener: Listener to add.

        Returns:
            The `EventListener` that was added.
            If the provided listener already is an `EventListener`,
            the return value is the same value.
        """
        if not isinstance(listener, EventListener):
            listener = EventListener(listener)

        _push_map_list(self._listeners, event, listener)
        return listener

    def remove_listener(self, event: str, target: Union[EventHandler, EventListener]) -> bool:
        """Remove a previously added event listener.

        When a `EventHandler` is passed, all event listeners with the given handler are removed.

        Args:
            event: Name of the event for which to remove a listener.
            target: Listener to remove.

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

        Events are first propagated to the "one-time listeners" (i.e. those added by `wait_for`),
        then the instances "on_<event>" methods are called and finally
        the listeners.

        If an error occurs while dispatching an event, `on_event_error` is called.

        Args:
            event: Event to be dispatched.

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
            return asyncio.gather(*futures, loop=self._loop)
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
        """Called when an error occurs during event dispatching.

        Args:
            event: Special event type which contains some meta information
                next to the original event.
        """
        log.exception(f"There was an error when {event.handler} handled {event.original_event}: {event.exception}")
