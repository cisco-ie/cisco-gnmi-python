import pytest
from pytest_mock import mocker
from src.cisco_gnmi.proto import gnmi_pb2
from src.cisco_gnmi import util
from src.cisco_gnmi.util import urlparse, ssl, x509, default_backend


def test_gen_target_netloc_valueerror():
    with pytest.raises(ValueError):
        util.gen_target_netloc("http://www.test.com", "test_prefix://", 8000)

def test_gen_target_netloc_parsed_none():

    mock_netloc = '//www.testing.com:8080'
    mock_parsed_netloc = urlparse(mock_netloc)

    result = util.gen_target_netloc("www.testing.com", "http://", 8080)
    assert mock_parsed_netloc == result

def test_validate_proto_enum_exception_one():
    
    enum = gnmi_pb2.SubscriptionMode

    with pytest.raises(Exception):
        util.validate_proto_enum('test', 'INVALID_VALUE', 'test', enum)

def test_validate_proto_enum_exception_two():
    pass

def test_validate_proto_enum_exception_three():
    pass

def test_validate_proto_enum_value_return():
    
    enum = gnmi_pb2.SubscriptionMode

    result = util.validate_proto_enum('test', 'ON_CHANGE', 'test', enum)
    assert 1 == result


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

def test_get_cn_from_cert_retrun_value_one(mocker):
    pass

def test_get_cn_from_cert_retrun_value_two(mocker):
    pass

