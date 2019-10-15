import pytest
from src.cisco_gnmi import util
from urllib.parse import urlparse
import ssl


def test_gen_target_netloc_valueerror():
    with pytest.raises(ValueError):
        util.gen_target_netloc("test_target", "test_netloc", 0000)

def test_gen_target_netloc_parsed_none():
    pass

def test_gen_target_netloc_parsed_not_none():
    pass

def test_validate_proto_enum_exception_one():
    pass

def test_validate_proto_enum_exception_two():
    pass

def test_validate_proto_enum_exception_three():
    pass

def test_validate_proto_enum_value_return():
    pass

def test_get_cert_from_target():

    target_netloc = {
        "hostname": "172.217.15.100",
        "port": 443
    }
    
    expected_ssl_cert = ssl.get_server_certificate((
        target_netloc.get("hostname"),
        target_netloc.get("port")
    ))
    
    expected_ssl_cert.encode('utf-8')
      
    target = util.gen_target_netloc("172.217.15.100:443")
    result = util.get_cert_from_target((target)).decode('utf-8')

    assert expected_ssl_cert == result
