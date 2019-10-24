import unittest
from unittest import mock
from src.cisco_gnmi.auth import CiscoAuthPlugin


def test_call():
    username = "grpc-username"
    password = "grpc-password"

    mock_call = mock.MagicMock(spec=CiscoAuthPlugin.__call__)

    instance = CiscoAuthPlugin(username, password)
    result = instance.__call__(
        [(username, "testUsr"), (password, "testPass")], CiscoAuthPlugin
    )
    mock_call.assert_not_called()
