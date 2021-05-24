import pytest
from decimal import Decimal
import json
import pytz
from datetime import datetime, timedelta

from aiobbox.utils import guess_json, json_to_str

def test_guess_json():
    assert guess_json('688') == 688
    with pytest.raises(json.decoder.JSONDecodeError):
        assert guess_json('{dfa') == 8

    assert guess_json('"hello"') == 'hello'

def test_json():
    assert json_to_str(datetime(2021, 5, 24, 3, 1, 16, tzinfo=pytz.UTC)) == '"2021-05-24T03:01:16+00:00"'
    assert json_to_str(Decimal('1.234')) == '"1.234"'
