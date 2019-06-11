from andesite import LoadType, LoadedTrack, PlaylistInfo, TrackInfo, TrackMetadata
from andesite.transform import build_from_raw


def test_loaded_track_load():
    raw_data = {"loadType": "SEARCH_RESULT",
                "tracks": [
                    {
                        "track": "QAAAlQIAMFdoYXQgSXMgWW91ciBTb3VsIEVsZW1lbnQ/IENvb2wgUGVyc29uYWxpdHkgVGVzdAALQlJJR0hUIFNJREUAAAAAAApE6AALRmlzcjRZWV8yTDgAAQAraHR0cHM6Ly93d3cueW91dHViZS5jb20vd2F0Y2g/dj1GaXNyNFlZXzJMOAAHeW91dHViZQAAAAAAAAAA",
                        "info": {"class": "com.sedmelluq.discord.lavaplayer.source.youtube.YoutubeAudioTrack",
                                 "title": "What Is Your Soul Element? Cool Personality Test",
                                 "author": "BRIGHT SIDE", "length": 673000, "identifier": "Fisr4YY_2L8",
                                 "uri": "https://www.youtube.com/watch?v=Fisr4YY_2L8", "isStream": False,
                                 "isSeekable": True, "position": 0}
                    }, {
                        "track": "QAAAmQIANFdobyBJcyBTZWNyZXRseSBJbiBMb3ZlIFdpdGggWW91PyAoUGVyc29uYWxpdHkgVGVzdCkAC0JSSUdIVCBTSURFAAAAAAAHgeAAC2NIWHRuTkNzR280AAEAK2h0dHBzOi8vd3d3LnlvdXR1YmUuY29tL3dhdGNoP3Y9Y0hYdG5OQ3NHbzQAB3lvdXR1YmUAAAAAAAAAAA==",
                        "info": {"class": "com.sedmelluq.discord.lavaplayer.source.youtube.YoutubeAudioTrack",
                                 "title": "Who Is Secretly In Love With You? (Personality Test)",
                                 "author": "BRIGHT SIDE", "length": 492000, "identifier": "cHXtnNCsGo4",
                                 "uri": "https://www.youtube.com/watch?v=cHXtnNCsGo4", "isStream": False,
                                 "isSeekable": True, "position": 0}
                    }, {
                        "track": "QAAAkAIAJjEzIFNVUlZJVkFMIFJJRERMRVMgVE8gVEVTVCBZT1VSIExPR0lDABA3LVNlY29uZCBSaWRkbGVzAAAAAAANB/AAC01QeHBEdGFQSHZBAAEAK2h0dHBzOi8vd3d3LnlvdXR1YmUuY29tL3dhdGNoP3Y9TVB4cER0YVBIdkEAB3lvdXR1YmUAAAAAAAAAAA==",
                        "info": {"class": "com.sedmelluq.discord.lavaplayer.source.youtube.YoutubeAudioTrack",
                                 "title": "13 SURVIVAL RIDDLES TO TEST YOUR LOGIC", "author": "7-Second Riddles",
                                 "length": 854000, "identifier": "MPxpDtaPHvA",
                                 "uri": "https://www.youtube.com/watch?v=MPxpDtaPHvA", "isStream": False,
                                 "isSeekable": True, "position": 0}
                    }],
                "playlistInfo": {"name": "Search results for: test", "selectedTrack": None}}

    track = build_from_raw(LoadedTrack, raw_data)

    assert track == LoadedTrack(LoadType.SEARCH_RESULT,
                                [TrackInfo(
                                    "QAAAlQIAMFdoYXQgSXMgWW91ciBTb3VsIEVsZW1lbnQ/IENvb2wgUGVyc29uYWxpdHkgVGVzdAALQlJJR0hUIFNJREUAAAAAAApE6AALRmlzcjRZWV8yTDgAAQAraHR0cHM6Ly93d3cueW91dHViZS5jb20vd2F0Y2g/dj1GaXNyNFlZXzJMOAAHeW91dHViZQAAAAAAAAAA",
                                    TrackMetadata("com.sedmelluq.discord.lavaplayer.source.youtube.YoutubeAudioTrack",
                                                  "What Is Your Soul Element? Cool Personality Test", "BRIGHT SIDE", 673, "Fisr4YY_2L8",
                                                  "https://www.youtube.com/watch?v=Fisr4YY_2L8", False, True, 0)
                                ), TrackInfo(
                                    "QAAAmQIANFdobyBJcyBTZWNyZXRseSBJbiBMb3ZlIFdpdGggWW91PyAoUGVyc29uYWxpdHkgVGVzdCkAC0JSSUdIVCBTSURFAAAAAAAHgeAAC2NIWHRuTkNzR280AAEAK2h0dHBzOi8vd3d3LnlvdXR1YmUuY29tL3dhdGNoP3Y9Y0hYdG5OQ3NHbzQAB3lvdXR1YmUAAAAAAAAAAA==",
                                    TrackMetadata("com.sedmelluq.discord.lavaplayer.source.youtube.YoutubeAudioTrack",
                                                  "Who Is Secretly In Love With You? (Personality Test)", "BRIGHT SIDE", 492, "cHXtnNCsGo4",
                                                  "https://www.youtube.com/watch?v=cHXtnNCsGo4", False, True, 0)
                                ), TrackInfo(
                                    "QAAAkAIAJjEzIFNVUlZJVkFMIFJJRERMRVMgVE8gVEVTVCBZT1VSIExPR0lDABA3LVNlY29uZCBSaWRkbGVzAAAAAAANB/AAC01QeHBEdGFQSHZBAAEAK2h0dHBzOi8vd3d3LnlvdXR1YmUuY29tL3dhdGNoP3Y9TVB4cER0YVBIdkEAB3lvdXR1YmUAAAAAAAAAAA==",
                                    TrackMetadata("com.sedmelluq.discord.lavaplayer.source.youtube.YoutubeAudioTrack",
                                                  "13 SURVIVAL RIDDLES TO TEST YOUR LOGIC", "7-Second Riddles", 854, "MPxpDtaPHvA",
                                                  "https://www.youtube.com/watch?v=MPxpDtaPHvA", False, True, 0)
                                )],
                                PlaylistInfo("Search results for: test", None))
