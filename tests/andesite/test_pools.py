import andesite


def test_create_andesite_pool():
    andesite.create_pool(
        [("http://localhost:5555", None)],
        [("ws://localhost:5555", None), ("wss://example.com", "example")],
        user_id=1234,
    )
