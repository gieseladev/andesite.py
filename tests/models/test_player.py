def test_player_update_build():
    data = {"op": "player-update", "guildId": "549904277108424715", "userId": "549905730099216384",
            "state": {"time": "1552516847143", "position": 2173780, "paused": False, "volume": 100,
                      "filters": {"vibrato": {"frequency": 2.0, "depth": 0.5, "enabled": False}, "volume": {"volume": 1.0, "enabled": False},
                                  "tremolo": {"frequency": 2.0, "depth": 0.5, "enabled": False},
                                  "equalizer": {"bands": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                                                "enabled": False},
                                  "karaoke": {"level": 1.0, "monoLevel": 1.0, "filterBand": 220.0, "filterWidth": 220.0, "enabled": False},
                                  "timescale": {"speed": 1.0, "pitch": 1.0, "rate": 1.0, "enabled": False}}, "mixer": {}, "mixerEnabled": False,
                      "frame": {"loss": 0, "success": 3016, "usable": True}}}
