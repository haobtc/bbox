import os

def test_mode():
    return os.getenv('BBOX_TESTING', '').lower() in ('1', 'true', 'yes')

