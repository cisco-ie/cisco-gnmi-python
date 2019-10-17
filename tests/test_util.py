import pytest
from pytest_mock import mocker
from src.cisco_gnmi import util
from src.cisco_gnmi.util import urlparse, ssl, x509, default_backend


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

def test_get_cn_from_cert_retrun_value_one(mocker):

    mock_cert_parsed = mocker.patch.object(x509, 'load_pem_x509_certificate')
    result = util.get_cn_from_cert([])

    assert None == result

def test_get_cn_from_cert_retrun_value_two(mocker):
    pass

