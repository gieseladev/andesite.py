from andesite.discord import compare_regions


def test_compare_regions():
    assert compare_regions("london", "london") == 3
    assert compare_regions("us-west", "us-east") == 2
    assert compare_regions("vip-us-west", "us") == 2
    assert compare_regions("us-west", "vip-us") == 2
    assert compare_regions("london", "japan") == 0
