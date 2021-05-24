import pytest
from aiobbox.server import has_service
from aiobbox.cluster.ticket import get_ticket
from aiobbox.testing import test_mode

def test_basic_conf():
    assert not has_service('aaa')
    assert test_mode()

def test_ticket():
    ticket = get_ticket()
    assert ticket.loaded
    assert ticket.name == 'bboxtest'
    assert ticket.bind_ip == '127.0.0.1'
