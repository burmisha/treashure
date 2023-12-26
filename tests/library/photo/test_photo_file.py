import pytest
import datetime

from library.photo.photo_file import get_dt_from_exif, cut_large_hour, get_timedelta


@pytest.mark.parametrize(
    'exif, suffix, dt',
    [
        (
            {'DateTime': '2022:04:17 15:13:50', 'SubsecTime': '00'},
            '',
            datetime.datetime(2022, 4, 17, 15, 13, 50),
        ),
        (
            {
                'DateTimeOriginal': '2022:07:09 11:39:04',
                'OffsetTimeOriginal': '+05:00',
                'SubsecTimeOriginal': '005',
            },
            'Original',
            datetime.datetime(2022, 7, 9, 11, 39, 4, 5000, tzinfo=datetime.timezone(datetime.timedelta(seconds=18000)))
        ),
        (
            {'DateTimeDigitized': '2019:09:22 24:40:46'},
            'Digitized',
            datetime.datetime(2019, 9, 23, 0, 40, 46)
        ),
        (
            {'DateTimeDigitized': '2019:09:22 14:40:46', 'SubsecTimeDigitized': '919503\x00'},
            'Digitized',
            datetime.datetime(2019, 9, 22, 14, 40, 46, 919503)
        ),
    ],
)
def test_get_dt_from_exif(exif, suffix, dt):
    result = get_dt_from_exif(exif, suffix=suffix)
    assert result == dt


@pytest.mark.parametrize(
    'dt, expected_dt, expected_days',
    [
        ('2010-11-22 24:40:20', '2010-11-22 0:40:20', 1),
        ('2010-11-22 23:41:21', '2010-11-22 23:41:21', 0),
    ],
)
def test_cut_large_hour(dt, expected_dt, expected_days):
    result_dt, result_days = cut_large_hour(dt)
    assert result_dt == expected_dt
    assert result_days == expected_days




@pytest.mark.parametrize(
    'line, expected',
    [
        ('+04:00\x00', datetime.timedelta(seconds=14400)),
        ('+04:00', datetime.timedelta(seconds=14400)),
    ],
)
def test_get_timedelta(line, expected):
    assert get_timedelta(line) == expected
