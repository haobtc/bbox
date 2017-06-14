import os

test_mode = (os.getenv('BBOX_TESTING', '').lower()
             in ('1', 'true', 'yes'))
