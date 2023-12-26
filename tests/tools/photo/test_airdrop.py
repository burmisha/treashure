import pytest

from tools.photo.airdrop import rename


@pytest.mark.parametrize(
    'filename, expected',
    [
        ('/any_prefix/IMG_5666/IMG_E5666.mov', 'IMG_5666_edited.MOV'),
        ('/any_prefix/IMG_5666/IMG_5666.mov', 'IMG_5666.mov'),
        ('/any_prefix/IMG_7404/IMG_7404.AAE', 'IMG_7404.AAE'),
        ('/any_prefix/IMG_7404/IMG_7404.JPG', 'IMG_7404.JPG'),
        ('/any_prefix/IMG_7404/IMG_E7404.jpg', 'IMG_7404_edited.JPG'),
        ('/any_prefix/IMG_7404/IMG_O7404.AAE', 'IMG_7404_edited.AAE'),
        ('/any_prefix/FEAC8BBA-7A25-409F-8E6F-715FE57ADA8B/IMG_0967.JPG', 'IMG_0967.JPG'),
        ('/any_prefix/RPReplay_Final1627725283/IMG_1234.MP4', 'IMG_1234.MP4'),
        ('/any_prefix/RPReplay_Final1627725283 2/IMG_1234.MP4', 'IMG_1234.MP4'),
        ('/any_prefix/IMG_0123 2/IMG_E0123.jpg', 'IMG_0123_edited.JPG'),
        ('/any_prefix/FullSizeRender/IMG_0123.jpg', 'IMG_0123.jpg'),
        ('/any_prefix/FullSizeRender/IMG_E0123.jpg', 'IMG_0123_edited.JPG'),
        ('/any_prefix/FullSizeRender 2/IMG_0123.jpg', 'IMG_0123.jpg'),
        ('/any_prefix/FullSizeRender 22/IMG_0123.jpg', 'IMG_0123.jpg'),
    ],
)
def test_rename(filename, expected):
    assert rename(filename) == expected
