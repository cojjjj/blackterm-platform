import pytest
from blackterm_recon.exceptions import PortSpecificationError
from blackterm_recon.ports import parse_ports


def test_parse_ports():
    assert parse_ports("22,80,8000-8002") == [22, 80, 8000, 8001, 8002]


def test_bad_range():
    with pytest.raises(PortSpecificationError):
        parse_ports("100-10")
