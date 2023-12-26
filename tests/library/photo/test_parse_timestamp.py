import pytest

from library.photo.parse_timestamp import parse_timestamp


@pytest.mark.parametrize(
	'line, expected',
	[
        ('2022-12-29 22:14:05', 1672337645),  # ARM
        ('2005-01-01 10:10:10', 1104559810),
        ('2033-01-01 10:10:10', 1988172610),
        ('Screenshot_20191231-190906.png', 1577804946),
        ('Screenshot_20191231-190907~2.png', 1577804947),
        ('PHOTO_20191231_190908_0.jpg', 1577804948),
        ('2021-11-06 16:18:21.jpg', 1636201101),
        ('2020-04-24 03.00.49 3.jpg', 1587682849),
        ('1305-burmisha-20130524232554.png', 1369423554),
        ('photo_2018-05-10_17-13-31.jpg', 1525958011),
        ('photo_2018_05-10_17-13-31.jpg', 1525958011),
        ('photo_2018.05-10_17-13-31.jpg', 1525958011),
        ('photo_2018:05-10_17-13-31.jpg', 1525958011),
        ('20180510171331.png', 1525958011),
        ('2018-05-10 17:13:31.png', 1525958011),
        ('2007_04_03-07_58_17.png', 1175569097),
        ('photo311519012136790160.png', None),
        ('11-49472976-784857-800-100.jpg', None),
        ('XX-49472976-784857-800-100.jpg', None),
        ('2007_04_26-16_37_11.jpg', 1177587431),
        ('P-00930-2007_04_26-16_37_11.jpg', 1177587431),
        ('IMG_20191028_081550_384.jpg', 1572236150),
        ('IMG_20191028_081550_384', 1572236150),
        ('20191028081550', 1572236150),
    ],
)
def test_parse_timestamp(line, expected):
	# TODO: check timezones
    timestamp = parse_timestamp(line)
    assert timestamp == expected