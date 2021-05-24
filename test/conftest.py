import pytest
import os

@pytest.hookimpl
def pytest_runtest_setup(item):
    # called for running each test in 'a' directory
    #print("setting up", item)
    pass

@pytest.hookimpl
def pytest_collection_modifyitems(session, config, items):
    #print('colletion modify items', session, config, items)
    os.environ['BBOX_TESTING'] = 'yes'
    os.environ['BBOX_PATH'] = 'test/bbox'
