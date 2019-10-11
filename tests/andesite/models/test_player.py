from datetime import datetime

from andesite import Equalizer, FilterMap, Karaoke, Player, PlayerFrameStats, PlayerUpdate, Timescale, Tremolo, Vibrato, VolumeFilter
from andesite.transform import build_from_raw


def test_player_update_build():
    raw_data = {"guildId": "549904277108424715", "userId": "549905730099216384",
                "state": {"time": "1552516847143", "position": 2173780, "paused": False, "volume": 100,
                          "filters": {"vibrato": {"frequency": 2.0, "depth": 0.5, "enabled": False},
                                      "volume": {"volume": 1.0, "enabled": False},
                                      "tremolo": {"frequency": 2.0, "depth": 0.5, "enabled": False},
                                      "equalizer": {"bands": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                                                    "enabled": False},
                                      "karaoke": {"level": 1.0, "monoLevel": 1.0, "filterBand": 220.0,
                                                  "filterWidth": 100.0, "enabled": False},
                                      "timescale": {"speed": 1.0, "pitch": 1.0, "rate": 1.0, "enabled": False}},
                          "mixer": {},
                          "mixerEnabled": False,
                          "frame": {"loss": 0, "success": 3016, "usable": True}}}

    # noinspection PyArgumentList
    expected = PlayerUpdate(
        549905730099216384,
        549904277108424715,
        Player(
            datetime(2019, 3, 13, 22, 40, 47, 143000),
            2173.78,
            False,
            1.0,
            FilterMap(dict(
                vibrato=Vibrato(enabled=False),
                volume=VolumeFilter(enabled=False),
                tremolo=Tremolo(enabled=False),
                equalizer=Equalizer(enabled=False),
                karaoke=Karaoke(enabled=False),
                timescale=Timescale(enabled=False),
            )),
            PlayerFrameStats(0, 3016, True),
            {},
            False
        )
    )

    player_update = build_from_raw(PlayerUpdate, raw_data)

    assert player_update == expected
