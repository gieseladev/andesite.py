"""Event dispatching and listening.

This module provides a simple `EventTarget` which can be used
to dispatch events.
The easiest way to use it is to inherit from it.

Attributes:
    EventHandler ((Event) -> `Any`): (Type alias) Callable which takes an event. If the callable is a coroutine it is awaited.
    EventFilter ((Event) -> `bool`): (Type alias) Callable which takes an event and returns a `bool`.
        This is used to "filter" events.
    EventSpecifierType (Union[str, Type[NamedEvent]]): (Type alias) Type of an object which conveys the name of an `Event`.
        Usually this is just a string with the name of the event, however you can
        also use a `NamedEvent` class.
"""
import abc
import asyncio
import inspect
import logging
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Coroutine, Dict, Iterable, List, Mapping, MutableMapping, Optional, Set, \
    Tuple, Type, TypeVar, Union, \
    overload

import lettercase

__all__ = ["Event", "NamedEvent",
           "EventErrorEvent",
           "EventHandler", "EventFilter",
           "OneTimeEventListener", "EventListener",
           "EventSpecifierType", "resolve_event_specifier",
           "EventTarget"]

log = logging.getLogger(__name__)


class Event:
    """Base type of all events.

    Args:
        name: Name of the event
        arg: Acts like kwargs, but doesn't need to be unpacked, thus being more
            efficient. This argument is optional. kwargs values will override
            the values in this mapping.
        **kwargs: Attributes to set on the event.

    Attributes:
        name (str): Name of the event.

    Dynamic attributes (those passed to the constructor) can also be accessed
    using the `get` method.
    """
    name: str

    _keys: Set[str]

    @overload
    def __init__(self, name: str, arg: Mapping[str, Any], **kwargs: Any) -> None:
        ...

    @overload
    def __init__(self, name: str, arg: Iterable[Tuple[str, Any]], **kwargs: Any) -> None:
        ...

    @overload
    def __init__(self, name: str, **kwargs: Any) -> None:
        ...

    def __init__(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.name = name

        body = dict(*args, **kwargs)
        self.__dict__.update(body)

        try:
            keys = self._keys
        except AttributeError:
            keys = self._keys = set()

        keys.update(body.keys())

    def __repr__(self) -> str:
        type_name = type(self).__name__
        name = self.name

        attrs_str = ", ".join(self._keys)
        return f"{type_name} ({name}) {{{attrs_str}}}"

    def get(self, key: str, *, default: Any = None) -> Optional[Any]:
        """Get the value of a key.

        Unlike `getattr`, the key must have been passed to the event.
        If you need to get any attribute, use `getattr` instead.

        Args:
            key: Name of the key to retrieve
            default: Default value to return if the key doesn't exist.
                (Default is `None`)
        """
        if key in self._keys:
            return getattr(self, key, default=default)
        return default


def _trim_suffix(s: str, suffix: str) -> str:
    """Return the string without the given suffix.

    Args:
        s: String to remove suffix from
        suffix: Exact suffix to remove
    """
    if s.endswith(suffix):
        return s[:-len(suffix)]
    else:
        return s


class NamedEvent(Event, abc.ABC):
    """Event which automatically gets its name from its class.

    Args:
        **kwargs: Attributes to set on the event.
            (Passed to the `Event` constructor)

    This is useful for subclasses of `Event` whose name is used for the event name.
    You may also manually set the event name by setting `__event_name__` on the class.

    This is an abstract class, you cannot use it directly. You can either use an `Event`
    or subclass this class.
    """
    __event_name__: str

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(self.get_event_name(), *args, **kwargs)

    @classmethod
    def _create_name(cls) -> str:
        """Generate the name for the event representing this class.

        This uses the class name and converts it to snake_case. ("NamedEvent" -> "named_event")
        If the class name endswith "Event" it is stripped. So "NamedEvent" would become "named".

        Returns:
            Generated name
        """
        cls_name = _trim_suffix(cls.__name__, "Event")

        name = lettercase.convert_to(cls_name, lettercase.LetterCase.SNAKE)
        cls.__event_name__ = name
        return name

    @classmethod
    def get_event_name(cls) -> str:
        """Get the event name for the event representing this class."""
        try:
            return cls.__event_name__
        except AttributeError:
            return cls._create_name()


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
        condition (Optional[EventFilter]): Callback which takes an `Event` and returns `True`
            to accept the event and `False` otherwise.
            If not provided, all events are accepted.
    """
    future: asyncio.Future
    condition: Optional[EventFilter] = None


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


EventSpecifierType = Union[str, Type[NamedEvent]]


def resolve_event_specifier(event: EventSpecifierType) -> str:
    """Resolve an `EventSpecifierType` to the name of the event.

    Raises:
        TypeError: If something other than an `EventSpecifierType` is passed.
    """
    if isinstance(event, str):
        return event
    elif issubclass(event, NamedEvent):
        return event.get_event_name()
    else:
        raise TypeError(f"Unknown event specifier type {type(event).__name__!r}: {event}")


class EventTarget:
    """An object that can dispatch `Event` instances to listeners.

    Args:
        loop: You can specify the loop which will be used for various asynchronous actions.
            If you don't specify a loop, it will be dynamically retrieved when needed.
    """
    _one_time_listeners: Dict[str, List[OneTimeEventListener]]
    _listeners: Dict[str, List[EventListener]]
    _children: Set["EventTarget"]

    _loop: Optional[asyncio.AbstractEventLoop]

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None) -> None:
        self._loop = loop
        self._one_time_listeners = {}
        self._listeners = {}
        self._children = set()

    @overload
    def wait_for(self, event: EventSpecifierType, *, check: EventFilter) -> Awaitable[Event]:
        ...

    @overload
    def wait_for(self, event: EventSpecifierType, *, check: EventFilter, timeout: float) -> Awaitable[Optional[Event]]:
        ...

    def wait_for(self, event: EventSpecifierType, *,
                 check: EventFilter,
                 timeout: float = None) -> Awaitable[Optional[Event]]:
        """Wait for an event to be dispatched.

        This is similar to adding a listener, but it only listens once and
        returns the event that was dispatched instead of calling a callback.

        Args:
            event: Name of the event to listen to.
                Also accepts `NamedEvent` types.
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
        event = resolve_event_specifier(event)

        # not using self._loop.create_future because loop may be None
        future = asyncio.Future(loop=self._loop)
        listener = OneTimeEventListener(future, check)

        _push_map_list(self._one_time_listeners, event, listener)

        return asyncio.wait_for(future, timeout=timeout, loop=self._loop)

    def add_dispatcher(self, target: "EventTarget") -> None:
        """Add a child event target which will dispatch the same events.

        Args:
            target: Event target to add as a child.
        """
        self._children.add(target)

    def remove_dispatcher(self, target: "EventTarget") -> None:
        """Remove a child event target.

        Args:
            target: Event target to remove.
        """

        self._children.discard(target)

    def add_listener(self, event: EventSpecifierType, listener: Union[EventHandler, EventListener]) -> EventListener:
        """Add a listener for an `Event` which is called whenever said event is dispatched.

        Args:
            event: Name of the event to listen to.
                Also accepts `NamedEvent` types.
            listener: Listener to add.

        Returns:
            The `EventListener` that was added.
            If the provided listener already is an `EventListener`,
            the return value is the same value.
        """
        event = resolve_event_specifier(event)

        if not isinstance(listener, EventListener):
            listener = EventListener(listener)

        _push_map_list(self._listeners, event, listener)
        return listener

    def remove_listener(self, event: EventSpecifierType, target: Union[EventHandler, EventListener]) -> bool:
        """Remove a previously added event listener.

        When a `EventHandler` is passed, all event listeners with the given handler are removed.

        Args:
            event: Name of the event for which to remove a listener.
                Also accepts `NamedEvent` types.
            target: Listener to remove.

        Returns:
            bool: Whether the listener was successfully removed.
        """
        event = resolve_event_specifier(event)

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

    @overload
    def has_listener(self, event: EventSpecifierType) -> bool:
        ...

    @overload
    def has_listener(self, event: EventSpecifierType,
                     target: Union[EventHandler, EventListener, OneTimeEventListener]) -> bool:
        ...

    def has_listener(self, event: EventSpecifierType,
                     target: Union[EventHandler, EventListener, OneTimeEventListener] = None) -> bool:
        """Check whether an event has a listener.

        This includes one-time listeners, but does not check method
        listeners (on_<event> methods defined in the event target class).

        Args:
            event: Name of the event to check.
                Also accepts `NamedEvent` types.
            target: Listener to check whether it has been added.
                If this is `None` the method checks whether the
                event has **any** listeners.
        """
        event = resolve_event_specifier(event)

        if target is None:
            return bool(self._listeners.get(event)) or bool(self._one_time_listeners.get(event))
        elif isinstance(target, OneTimeEventListener):
            try:
                listeners = self._one_time_listeners[event]
            except KeyError:
                return False
            else:
                return target in listeners
        else:
            try:
                listeners = self._listeners[event]
            except KeyError:
                return False

            if isinstance(target, EventListener):
                return target in listeners
            else:
                for listener in listeners:
                    if listener.handler == target:
                        return True

                return False

    def dispatch(self, event: Event) -> Optional[asyncio.Future]:
        """Dispatch an event.

        Events are first propagated to the "one-time listeners" (i.e. those added by `wait_for`),
        then the instances "on_<event>" methods are called and finally
        the listeners.

        Events are also propagated to child event targets.

        If an error occurs while dispatching an event, `on_event_error` is called.

        Args:
            event: Event to be dispatched.

        Returns:
            Optional[Future]: Future aggregating all asynchronous dispatches.
                Can be awaited to make sure all handlers have been executed.
        """
        if log.isEnabledFor(logging.DEBUG):
            # converting event to string may be expensive, so only
            # do it if we want it logged
            log.debug(f"dispatching: {event}")

        futures: List[Union[Coroutine, asyncio.Future]] = []
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

        for child_target in self._children:
            futures.append(asyncio.ensure_future(child_target.dispatch(event), loop=self._loop))

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
        except asyncio.CancelledError:
            pass
        except Exception as e:
            error_event = EventErrorEvent(method, e, event)

            with suppress(asyncio.CancelledError):
                await self.on_event_error(error_event)

    # noinspection PyMethodMayBeStatic
    async def on_event_error(self, event: EventErrorEvent) -> None:
        """Called when an error occurs during event dispatching.

        Args:
            event: Special event type which contains some meta information
                next to the original event.
        """
        log.exception(f"There was an error when {event.handler} handled {event.original_event}: {event.exception}")
