"""Copyright 2019 Cisco Systems
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

 * Redistributions of source code must retain the above copyright
 notice, this list of conditions and the following disclaimer.

The contents of this file are licensed under the Apache License, Version 2.0
(the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
"""

"""Builder to ease constructing cisco_gnmi.Client derived classes."""

import logging

import grpc
from . import Client, XRClient, NXClient, XEClient
from .auth import CiscoAuthPlugin
from .util import gen_target_netloc, get_cert_from_target, get_cn_from_cert


LOGGER = logging.getLogger(__name__)
logger = LOGGER


class ClientBuilder(object):
    """Builder for the creation of a gNMI client.
    Supports construction of base Client and XRClient.
    Returns itself after each build stage to support chained initialization.

    Methods
    -------
    set_target(...)
        Specifies the network element to build a client for.
    set_os(...)
        Specifies which OS wrapper to deliver.
    set_secure(...)
        Specifies that a secure gRPC channel should be used.
    set_secure_from_file(...)
        Loads certificates from file system for secure gRPC channel.
    set_secure_from_target(...)
        Attempts to utilize available certificate from target for secure gRPC channel.
    set_call_authentication(...)
        Specifies username/password to utilize for authentication.
    set_ssl_target_override(...)
        Sets the gRPC option to override the SSL target name.
    set_channel_option(...)
        Sets a gRPC channel option. Implies knowledge of channel options.
    construct()
        Constructs and returns the built Client.
    _reset()
        Resets builder to baseline state.
    
    Examples
    --------
    >>> from cisco_gnmi import ClientBuilder
    >>> client = ClientBuilder(
    ...     '127.0.0.1:9339'
    ... ).set_os(
    ...     'IOS XR'
    ... ).set_secure_from_target().set_ssl_target_override().set_authentication(
    ...     'admin',
    ...     'its_a_secret'
    ... ).construct()
    >>> capabilities = client.capabilities()
    >>> print(capabilities)
    """

    os_class_map = {
        None: Client,
        "None": Client,
        "IOS XR": XRClient,
        "XR": XRClient,
        "NX-OS": NXClient,
        "NX": NXClient,
        "IOS XE": XEClient,
        "XE": XEClient,
    }

    def __init__(self, target):
        """Initializes the builder, most initialization is done via set_* methods.
        A target is always required, thus a member of the constructor.

        Parameters
        ----------
        target : str
            The target address of the network element to interact with.
            Expects a URL-like form, e.g. 127.0.0.1:9339
        """
        self.set_target(target)
        self._reset()

    def set_target(self, target):
        """Specifies the network element to build a client for.

        Parameters
        ----------
        target : str
            The target address of the network element to interact with.
            Expects a URL-like form, e.g. 127.0.0.1:9339
        
        Returns
        -------
        self
        """
        self.__target = target
        self.__target_netloc = gen_target_netloc(self.__target)
        return self

    def set_os(self, name=None):
        """Sets which OS to target which maps to an OS wrapper class.

        Parameters
        ----------
        name : str
            "IOS XR" maps to the XRClient class.
            "NX-OS" maps to the NXClient class.
            "IOS XE" maps to the XEClient class.
            None maps to the base Client class which simply wraps the gNMI stub.
            ["IOS XR", "NX-OS", "IOS XE", None]
        
        Returns
        -------
        self
        """
        if name not in self.os_class_map.keys():
            raise Exception("OS not supported!")
        else:
            LOGGER.debug("Using %s wrapper.", name or "Client")
            self.__client_class = self.os_class_map[name]
        return self

    def set_secure(
        self, root_certificates=None, private_key=None, certificate_chain=None
    ):
        """Simply sets the fields to be expected by grpc.ssl_channel_credentials(...).
        Setting this method disallows following set_secure(...) or _set_insecure() calls.

        Parameters
        ----------
        root_certificates : str or None
        private_key : str or None
        certificate_chain : str or None

        Returns
        -------
        self
        """
        self.__secure = True
        self.__root_certificates = root_certificates
        self.__private_key = private_key
        self.__certificate_chain = certificate_chain
        return self

    def _set_insecure(self):
        """Sets the flag to use an insecure channel.
        THIS IS AGAINST SPECIFICATION and should not
        be used unless necessary and secure transport
        is already well understood. 

        Returns
        -------
        self
        """
        self.__secure = False
        return self

    def set_secure_from_file(
        self, root_certificates=None, private_key=None, certificate_chain=None
    ):
        """Wraps set_secure(...) but treats arguments as file paths.

        Parameters
        ----------
        root_certicates : str or None
        private_key : str or None
        certificate_chain : str or None
        
        Returns
        -------
        self
        """

        def load_cert(file_path):
            cert_content = None
            if file_path is not None:
                with open(file_path, "rb") as cert_fd:
                    cert_content = cert_fd.read()
            return cert_content

        if root_certificates:
            root_certificates = load_cert(root_certificates)
        if private_key:
            private_key = load_cert(private_key)
        if certificate_chain:
            certificate_chain = load_cert(certificate_chain)
        self.set_secure(root_certificates, private_key, certificate_chain)
        return self

    def set_secure_from_target(self):
        """Wraps set_secure(...) but loads root certificates from target.
        In effect, simply uses the target's certificate to create an encrypted channel.

        TODO: This may not work with IOS XE and NX-OS, uncertain.

        Returns
        -------
        self
        """
        root_certificates = get_cert_from_target(self.__target_netloc)
        self.set_secure(root_certificates)
        return self

    def set_call_authentication(self, username, password):
        """Sets the username and password to utilize for authentication."""
        self.__username = username
        self.__password = password
        return self

    def set_ssl_target_override(self, ssl_target_name_override=None):
        """Sets the gRPC option to override the SSL target name with the specified value.
        
        If None supplied then the option will be derived from the CN of the root certificate.
        set_secure_from_target().set_ssl_target_override() effectively creates an encrypted
        but insecure channel.
        The above behavior attempts to replicate the Go gNMI reference -insecure parameter.
        This is not recommended other than for testing purposes.

        Parameters
        ----------
        ssl_target_name_override : str or None
            Value for grpc.ssl_target_name_override
        
        Returns
        -------
        self
        """
        self.__ssl_target_name_override = ssl_target_name_override
        return self

    def set_channel_option(self, name, value):
        """Sets a gRPC channel option. This method implies understanding of gRPC channels.
        If the option is found, the value is overwritten.

        Parameters
        ----------
        name : str
            The gRPC channel option name.
        value : ?
            The value of the named option.

        Returns
        -------
        self
        """
        new_option = (name, value)
        if not self.__channel_options:
            self.__channel_options = [new_option]
        else:
            found_index = None
            for index, option in enumerate(self.__channel_options):
                if option[0] == name:
                    found_index = index
                    break
            if found_index is not None:
                LOGGER.warning("Found existing channel option %s, overwriting!", name)
                self.__channel_options[found_index] = new_option
            else:
                self.__channel_options.append(new_option)
        return self

    def construct(self, return_channel=False):
        """Constructs and returns the desired Client object.
        The instance of this class will reset to default values for further building.

        Returns
        -------
        Client or NXClient or XEClient or XRClient
        """
        channel = None
        if self.__secure:
            LOGGER.debug("Using secure channel.")
            channel_metadata_creds = None
            if self.__username and self.__password:
                LOGGER.debug("Using username/password call authentication.")
                channel_metadata_creds = grpc.metadata_call_credentials(
                    CiscoAuthPlugin(self.__username, self.__password)
                )
            channel_ssl_creds = grpc.ssl_channel_credentials(
                self.__root_certificates, self.__private_key, self.__certificate_chain
            )
            channel_creds = None
            if channel_ssl_creds and channel_metadata_creds:
                LOGGER.debug("Using SSL/metadata authentication composite credentials.")
                channel_creds = grpc.composite_channel_credentials(
                    channel_ssl_creds, channel_metadata_creds
                )
            else:
                LOGGER.debug(
                    "Using SSL credentials, no channel metadata authentication."
                )
                channel_creds = channel_ssl_creds
            if self.__ssl_target_name_override is not False:
                if self.__ssl_target_name_override is None:
                    if not self.__root_certificates:
                        raise Exception("Deriving override requires root certificate!")
                    self.__ssl_target_name_override = get_cn_from_cert(
                        self.__root_certificates
                    )
                    LOGGER.warning(
                        "Overriding SSL option from certificate could increase MITM susceptibility!"
                    )
                self.set_channel_option(
                    "grpc.ssl_target_name_override", self.__ssl_target_name_override
                )
            channel = grpc.secure_channel(
                self.__target_netloc.netloc, channel_creds, self.__channel_options
            )
        else:
            LOGGER.warning(
                "Insecure gRPC channel is against gNMI specification, personal data may be compromised."
            )
            channel = grpc.insecure_channel(self.__target_netloc.netloc)
        if self.__client_class is None:
            self.set_os()
        client = None
        if self.__secure:
            client = self.__client_class(channel)
        else:
            client = self.__client_class(
                channel,
                default_call_metadata=[
                    ("username", self.__username),
                    ("password", self.__password),
                ],
            )
        self._reset()
        if return_channel:
            return client, channel
        else:
            return client

    def _reset(self):
        """Resets the builder.
        
        Returns
        -------
        self
        """
        self.set_target(self.__target)
        self.__client_class = None
        self.__root_certificates = None
        self.__private_key = None
        self.__certificate_chain = None
        self.__username = None
        self.__password = None
        self.__channel_options = None
        self.__ssl_target_name_override = False
        self.__secure = True
        return self
