import copy

import lettercase

from andesite import ConnectionUpdate, PlayerUpdate, StatsUpdate, TrackEndEvent, TrackEndReason, TrackExceptionEvent, \
    TrackStartEvent, \
    TrackStuckEvent, UnknownAndesiteEvent, get_event_model, get_update_model
from andesite.transform import build_from_raw, convert_to_raw


def test_track_start_event_build():
    raw_data = {"type": "TrackStartEvent", "guildId": "549904277108424715", "userId": "549905730099216384",
                "track": "QAAAiwIAJ0x1aXMg"}

    # noinspection PyArgumentList
    assert build_from_raw(TrackStartEvent, raw_data) == TrackStartEvent("TrackStartEvent", 549905730099216384,
                                                                        549904277108424715, "QAAAiwIAJ0x1aXMg")


def test_track_start_event_dump():
    # noinspection PyArgumentList
    data = TrackStartEvent("TrackStartEvent", 549905730099216384, 549904277108424715, "QAAAiwIAJ0x1aXMg")

    assert convert_to_raw(data) == {"type": "TrackStartEvent", "guildId": "549904277108424715",
                                    "userId": "549905730099216384",
                                    "track": "QAAAiwIAJ0x1aXMg"}


def test_track_end_event_build():
    raw_data = {"type": "TrackEndEvent", "guildId": "549904277108424715", "userId": "549905730099216384",
                "track": "QAAAmAIANUFudWVsIEFBIC0gRW",
                "reason": "FINISHED", "mayStartNext": True}

    # noinspection PyArgumentList
    assert build_from_raw(TrackEndEvent, raw_data) == TrackEndEvent("TrackEndEvent", 549905730099216384,
                                                                    549904277108424715,
                                                                    "QAAAmAIANUFudWVsIEFBIC0gRW",
                                                                    TrackEndReason.FINISHED, True)


def test_track_end_event_dump():
    # noinspection PyArgumentList
    data = TrackEndEvent("TrackEndEvent", 549905730099216384, 549904277108424715,
                         "QAAAmAIANUFudWVsIEFBIC0gRW", TrackEndReason.FINISHED, True)

    assert convert_to_raw(data) == {"type": "TrackEndEvent", "guildId": "549904277108424715",
                                    "userId": "549905730099216384",
                                    "track": "QAAAmAIANUFudWVsIEFBIC0gRW",
                                    "reason": "FINISHED", "mayStartNext": True}


def test_get_event_model():
    assert get_event_model("TrackStartEvent") is TrackStartEvent
    assert get_event_model("TrackEndEvent") is TrackEndEvent
    assert get_event_model("TrackExceptionEvent") is TrackExceptionEvent
    assert get_event_model("TrackStuckEvent") is TrackStuckEvent
    assert get_event_model("stupid event which shouldn't exist") is UnknownAndesiteEvent


def test_get_update_model():
    assert get_update_model("connection-id") is ConnectionUpdate
    assert get_update_model("stats") is StatsUpdate
    assert get_update_model("player-update") is PlayerUpdate

    assert get_update_model("event") is None
    # we don't need to check every event because it uses get_event_model
    # and test_get_event_model already tests that
    assert get_update_model("event", "TrackStartEvent") is TrackStartEvent
    assert get_update_model("event", "stupid event which shouldn't exist") is UnknownAndesiteEvent


def test_unknown_andesite_event():
    data = {
        "type": "SpecialEvent",
        "userId": "1231231231231",
        "guildId": "234234234234234",
        "a": 5,
        "b": 6,
    }
    data_copy = copy.deepcopy(data)
    data_copy_low = copy.deepcopy(data_copy)
    lettercase.mut_convert_keys(data_copy_low, None, "snake")

    evt = build_from_raw(UnknownAndesiteEvent, data)

    assert evt.body == data_copy_low

    new_data = convert_to_raw(evt)
    assert data_copy == new_data
