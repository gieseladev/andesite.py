"""State handler for Andesite clients.

If you want to store your state externally for example in a database, there
are two approaches you can use. You can either implement the
`AbstractState` and use the default `AndesitePlayerState` (which can be
easily converted to and from JSON), or you can use the default `State`
with a custom `AbstractPlayerState` implementation.
Both approaches have their advantages, but you should always consider that while
the get operations are often performed together (especially during state
migration), the set operations are not.

Attributes:
    StateArgumentType (Union[AbstractState, bool, None]): (Type alias)
        types which can be passed as a state handler to a client.
"""

import abc
import functools
import logging
from typing import Any, Awaitable, Callable, Coroutine, Dict, Generic, Optional, TypeVar, Union

import andesite
from .transform import build_from_raw, convert_to_raw

__all__ = ["AbstractPlayerState", "PlayerState",
           "AbstractState", "State",
           "player_to_raw", "player_from_raw",
           "voice_server_update_to_raw", "voice_server_update_from_raw",
           "StateArgumentType", "_get_state"]

log = logging.getLogger(__name__)


def player_to_raw(player: andesite.Player) -> Dict[str, Any]:
    """Convert the given player to a JSON-serialisable dict.

    Args:
        player: Player to convert.

    Returns:
        A JSON-Serialisable dict containing all the data of the player.
        This data can be passed to `player_from_raw` which creates a `Player`
        instance again.
    """
    return convert_to_raw(player)


def player_from_raw(data: Dict[str, Any]) -> andesite.Player:
    """Recreate a player from the converted dict.

    Args:
        data: Data returned by `player_to_raw` to convert to a Player.

    Raises:
          Exception: If the data can't be used to create a Player.

    Returns:
        Created `Player` instance.
    """
    return build_from_raw(andesite.Player, data)


def voice_server_update_to_raw(update: andesite.VoiceServerUpdate) -> Dict[str, Any]:
    """Convert the given voice server update to a JSON-serialisable dict.

    Args:
        update: Voice server update to convert.

    Returns:
        A JSON-Serialisable dict containing all the data of the voice server
        update. This data can be passed to `voice_server_update_from_raw` which
        creates a `VoiceServerUpdate` instance again.
    """
    return convert_to_raw(update)


def voice_server_update_from_raw(data: Dict[str, Any]) -> andesite.VoiceServerUpdate:
    """Recreate a voice server update from the converted dict.

    Args:
        data: Data returned by `voice_server_update_to_raw` to convert.

    Raises:
          Exception: If the data can't be used to create a voice server update.

    Returns:
        Created `VoiceServerUpdate` instance.
    """
    return build_from_raw(andesite.VoiceServerUpdate, data)


class AbstractPlayerState(abc.ABC):
    """State of a single Andesite player.

    Notes:
        Unless you're doing something weird you don't need to call the setter
        functions. If the player state is managed by an `AbstractState`
        which is connected to a client then everything is done for you.

    See Also:
        `AndesitePlayerState` for an in-memory implementation.
    """
    __slots__ = ()

    def __str__(self) -> str:
        return f"PlayerState(guild_id={self.guild_id})"

    @property
    @abc.abstractmethod
    def guild_id(self) -> int:
        """ID of the guild the player is for."""
        ...

    @abc.abstractmethod
    async def get_player(self) -> Optional[andesite.Player]:
        """Get the player information.

        Returns:
            `Player` information or `None` if no player information
            is present.
        """
        ...

    @abc.abstractmethod
    async def set_player(self, player: Optional[andesite.Player]) -> None:
        """Set the current player.

        Args:
            player: Player data to set. May be `None` to remove the player
                information.
        """
        ...

    @abc.abstractmethod
    async def get_voice_server_update(self) -> Optional[andesite.VoiceServerUpdate]:
        """Get the last voice server update that was sent to the player.

        Returns:
            The last voice server update or `None` if none exists.
        """
        ...

    @abc.abstractmethod
    async def set_voice_server_update(self, update: Optional[andesite.VoiceServerUpdate]) -> None:
        """Set the last voice server update.

        Args:
            update: Voice server update to set.
        """
        ...

    @abc.abstractmethod
    async def get_track(self) -> Optional[str]:
        """Get the currently playing track."""
        ...

    @abc.abstractmethod
    async def set_track(self, track: Optional[str]) -> None:
        """Set the currently playing track."""
        ...


class PlayerState(AbstractPlayerState):
    """Default player state storing the state in memory.

    The player state can be converted to a JSON-serialisable dict using
    `to_raw`. A state can also be created from said dict using the classmethod
    `from_raw`. These methods exist to make it easy to implement a custom
    `AbstractState` which loads and stores serialised player states.
    """
    __slots__ = ("__guild_id",
                 "_player", "_track", "_voice_server_update")

    __guild_id: int

    _player: Optional[andesite.Player]
    _track: Optional[str]
    _voice_server_update: Optional[andesite.VoiceServerUpdate]

    def __init__(self, guild_id: int):
        self.__guild_id = guild_id

        self._player = None
        self._track = None
        self._voice_server_update = None

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    async def get_player(self) -> Optional[andesite.Player]:
        return self._player

    async def set_player(self, player: Optional[andesite.Player]) -> None:
        self._player = player

    async def get_track(self) -> Optional[str]:
        return self._track

    async def set_track(self, track: Optional[str]) -> None:
        self._track = track

    async def get_voice_server_update(self) -> Optional[andesite.VoiceServerUpdate]:
        return self._voice_server_update

    async def set_voice_server_update(self, update: Optional[andesite.VoiceServerUpdate]) -> None:
        self._voice_server_update = update

    @classmethod
    def from_raw(cls, data: Dict[str, Any]) -> AbstractPlayerState:
        """Create an `AbstractPlayerState` from the raw data.

        Args:
            data: Raw player state data as returned by `to_raw`

        Returns:
            A new instance of `PlayerState` describing the same state
            as the data.
        """
        inst = cls(data["guild_id"])

        inst._track = data.get("track")

        try:
            raw_player = data["player"]
        except KeyError:
            pass
        else:
            if raw_player is not None:
                inst._player = player_from_raw(raw_player)

        try:
            raw_voice_server_update = data["raw_voice_server_update"]
        except KeyError:
            pass
        else:
            if raw_voice_server_update is not None:
                inst._voice_server_update = voice_server_update_from_raw(raw_voice_server_update)

        return inst

    def to_raw(self) -> Dict[str, Any]:
        """Convert the player state into a JSON-serialisable dict.

        Use the classmethod `from_raw` to re-create a `PlayerState` using the
        returned data.
        """
        if self._player:
            raw_player = player_to_raw(self._player)
        else:
            raw_player = None

        if self._voice_server_update:
            raw_voice_server_update = voice_server_update_to_raw(self._voice_server_update)
        else:
            raw_voice_server_update = None

        return {
            "guild_id": self.__guild_id,
            "player": raw_player,
            "track": self._track,
            "voice_server_update": raw_voice_server_update,
        }


async def _run_with_error_callback(coro: Coroutine, err_cb: Callable[[Exception], Awaitable]) -> None:
    try:
        await coro
    except Exception as e:
        await err_cb(e)


class AbstractState(abc.ABC):
    """Andesite state handler.

    Keeps track of the state of an Andesite node.
    """
    __slots__ = ()

    def __str__(self) -> str:
        return f"{type(self).__name__}"

    async def _handle_andesite_message(self, message: andesite.ReceiveOperation) -> None:
        """Handles the event of an andesite message being received.

        Args:
            message: Message that was sent.
        """
        if isinstance(message, andesite.PlayerUpdate):
            coro = self.handle_player_update(message)
        elif isinstance(message, andesite.AndesiteEvent):
            coro = self.handle_andesite_event(message)
        else:
            return

        err_cb: Callable = functools.partial(self.on_handle_message_error, message)
        await _run_with_error_callback(coro, err_cb)

    async def _handle_sent_message(self, guild_id: int, op: str, payload: Dict[str, Any]) -> None:
        """Handles the event of a message being sent.

        Args:
            guild_id: Guild id the message was sent for.
            op: Operation code.
            payload: Raw payload of the message.
        """
        if op == "voice-server-update":
            update = andesite.VoiceServerUpdate(payload["sessionId"], payload["event"])
            coro = self.handle_voice_server_update(guild_id, update)
        else:
            return

        err_cb: Callable = functools.partial(self.on_handle_sent_message_error, guild_id, op, payload)
        await _run_with_error_callback(coro, err_cb)

    @abc.abstractmethod
    async def handle_player_update(self, update: andesite.PlayerUpdate) -> None:
        """Handle a player update.

        Args:
            update: Update that was received.
        """
        ...

    @abc.abstractmethod
    async def handle_andesite_event(self, event: andesite.AndesiteEvent) -> None:
        """Handle an Andesite event.

        Args:
            event: Andesite event that was received.
        """
        ...

    @abc.abstractmethod
    async def handle_voice_server_update(self, guild_id: int, update: andesite.VoiceServerUpdate) -> None:
        """Handle a voice server update.

        Args:
            guild_id: Guild the update applies to.
            update: Voice server update.
        """
        ...

    async def on_handle_message_error(self, message: andesite.ReceiveOperation, exc: Exception) -> None:
        """Called when an error occurs during message handling.

        Args:
            message: Message that caused the error
            exc: Exception that was raised.
        """
        log.error(f"uncaught error {exc} in {self} when handling message {message}")

    async def on_handle_sent_message_error(self, guild_id: int, op: str, payload: Dict[str, Any],
                                           exc: Exception) -> None:
        """Called when an error occurs during sent message handling.

        Args:
            guild_id: Guild the message was sent for.
            op: Operation code.
            payload: Raw payload which was sent.
            exc: Exception that was raised.
        """
        log.error(f"uncaught error {exc} in {self} when handling sent message {op} for guild {guild_id}: {exc}\n\n"
                  f"Payload: {payload}")

    @abc.abstractmethod
    async def get(self, guild_id: int) -> AbstractPlayerState:
        """Get the player state of a guild.

        Args:
            guild_id: Guild to get player state for.

        Returns:
            Player state for the given guild.
        """
        ...


PST = TypeVar("PST", bound=AbstractPlayerState)


class State(AbstractState, Generic[PST]):
    """Default implementation of `AbstractState`.

    Stores the player states in memory.

    Args:
        state_factory: Callable which when called with a guild id, creates an
            `AbstractPlayerState`. The default is `PlayerState`.

    Attributes:
        player_states (Dict[int, AbstractPlayerState]): Mapping from guild id
            to the corresponding player state.
    """
    __slots__ = ("player_states", "_state_factory")

    player_states: Dict[int, PST]
    _state_factory: Callable[[int], PST]

    def __init__(self, *, state_factory: Callable[[int], PST] = PlayerState) -> None:
        self.player_states = {}

        self._state_factory = state_factory

    def __repr__(self) -> str:
        return f"{type(self).__name__}(state_factory={self._state_factory!r})"

    def _get_or_create_player_state(self, guild_id: int) -> PST:
        try:
            player_state = self.player_states[guild_id]
        except KeyError:
            player_state = self.player_states[guild_id] = self._state_factory(guild_id)

        return player_state

    async def handle_player_update(self, update: andesite.PlayerUpdate) -> None:
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"handling player update for {self}: {update}")

        state = self._get_or_create_player_state(update.guild_id)
        await state.set_player(update.state)

    async def handle_andesite_event(self, event: andesite.AndesiteEvent) -> None:
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"handling andesite event for {self}: {event}")

        if isinstance(event, (andesite.TrackEndEvent, andesite.TrackExceptionEvent, andesite.TrackStuckEvent)):
            track = None
        elif isinstance(event, andesite.TrackStartEvent):
            track = event.track
        else:
            return

        state = self._get_or_create_player_state(event.guild_id)
        await state.set_track(track)

    async def handle_voice_server_update(self, guild_id: int, update: andesite.VoiceServerUpdate) -> None:
        player_state = self._get_or_create_player_state(guild_id)
        await player_state.set_voice_server_update(update)

    async def get(self, guild_id: int) -> PST:
        return self._get_or_create_player_state(guild_id)


StateArgumentType = Union[AbstractState, bool, None]


def _get_state(state: StateArgumentType) -> Optional[AbstractState]:
    """Handle state creation/suppression.

    Args:
        state: State which was passed to the function.

    Raises:
        TypeError: If an invalid state argument was passed.

    Returns:
        An instance of `State` if state is `None` or `True`,
        `None` if state is `False`, and `state` itself if it's a state.
    """
    if state is None or state is True:
        return State()
    elif state is False:
        return None
    elif isinstance(state, AbstractState):
        return state
    else:
        raise TypeError("State must implement AbstractState. "
                        "You can also use False to disable state handling or"
                        "None to use the default state handler.")
