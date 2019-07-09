"""Copyright 2019 Cisco Systems All rights reserved.

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

"""Python gNMI wrapper to ease usage."""

import grpc
from .proto import gnmi_pb2_grpc
from .proto import gnmi_pb2
from . import json_format

from grpc.beta import implementations

class GNMIClient(object):
    """This class creates grpc calls using python.
    """
    def __init__(self, host, port, timeout, user, password, creds=None, options=None):
        """:param user: Username for device login
            :param password: Password for device login
            :param host: The ip address for the device
            :param port: The port for the device
            :param timeout: how long before the rpc call timesout
            :param creds: Input of the pem file
            :param options: TLS server name
            :type password: str
            :type user: str
            :type host: str
            :type port: int
            :type timeout:int
            :type creds: str
            :type options: str
        """
        if creds != None:
            self._target = '%s:%d' % (host, port)
            self._creds = implementations.ssl_channel_credentials(creds)
            self._options = options
            channel = grpc.secure_channel(
                self._target, self._creds, (('grpc.ssl_target_name_override', self._options,),))
            self._channel = implementations.Channel(channel)
        else:
            self._host = host
            self._port = port
            self._channel = implementations.insecure_channel(self._host, self._port)
        self._stub = gnmi_pb2_grpc.gNMIStub(self._channel)
        self._timeout = float(timeout)
        self._metadata = [('username', user), ('password', password)]

    def __repr__(self):
        return '%s(Host = %s, Port = %s, User = %s, Password = %s, Timeout = %s)' % (
            self.__class__.__name__,
            self._host,
            self._port,
            self._metadata[0][1],
            self._metadata[1][1],
            self._timeout
        )

    def capabilities(self):
        """Capabilities allows the client to retrieve the set of capabilities that
        is supported by the target. This allows the target to validate the
        service version that is implemented and retrieve the set of models that
        the target supports. The models can then be specified in subsequent RPCs
        to restrict the set of data that is utilized.
        Reference: gNMI Specification Section 3.2
        """
        message = gnmi_pb2.CapabilityRequest()
        responses = self._stub.Capabilities(message, metadata=self._metadata)
        return responses
    
    def get(self, path, prefix=None, gnmi_type=None,
            encoding=0, user_models=None, extension=None):
        """
        A snapshot of the state that exists on the target
        :param path: A set of paths to request data snapshot
        :param prefix: a path that is applied to all paths
        :param gnmi_type: type of data requested [CONFIG, STATE, OPERATIONAL]
        :param encoding: Data format data comes out in 2=Proto, 0=JSON
        :param user_models: ModelData messages indicating the schema definition
        :param extension: a repeated field to carry gNMI extensions
        :type path:
        :type prefix:
        :type gnmi_type: string
        :type encoding: int
        :type user_models:
        :type extension:
        :return: Return the response object
        :rtype:
        """
        request = gnmi_pb2.GetRequest(
            path=path,
            prefix=prefix,
            type=gnmi_type,
            encoding=encoding,
            user_models=user_models,
            extension=extension)
        response = self._stub.Get(request, metadata=self._metadata)
        return response
    
    def set(self, prefix=None, update=None, replace=None, delete=None, extension=None):
        """
        Modifications to the state of the target are made through the Set RPC.
        A client sends a SetRequest message to the target indicating the modifications
        it desires.
        :param prefix: The prefix specified is applied to all paths defined within other fields of the message.
        :param update: A set of messages indicating elements of the data tree whose content is to be updated
        :param replace: A set of messages indicating elements of the data tree whose contents is to be replaced
        :param delete: A set of paths which are to be removed from the data tree.
        :param extension: Repeated field used to carry gNMI extensions
        :type prefix:
        :type update:
        :type replace:
        :type delete:
        :return: SetResonse with the following fields: prefix, response, extension
        """
        request = gnmi_pb2.SetRequest(
            prefix=prefix,
            update=update,
            replace=replace,
            delete=delete)
        response = self._stub.Set(request, metadata=self._metadata)
        return response
    
    def subscribe(self, subs, interval_seconds, encoding=2):
        """
        Subscription to receive updates relating to the state of data instances on a target
        :param subs: Subscription paths to subscribe to
        :param interval_seconds: Time of subscription path
        :param encoding: Defaults to Proto, 1, JSON
        :type subs: list
        :type interval_seconds: int
        :type encoding: int
        :return: Telemetry stream
        """
        subscriptions = []
        interval = interval_seconds * 1000000000 # convert to ns
        for sub in subs:
            pathelems = []
            for pathlevel in sub.split("/"):
                pathelems.append(gnmi_pb2.PathElem(name=pathlevel))
            path = gnmi_pb2.Path(elem=pathelems)
            subscriptions.append(gnmi_pb2.Subscription(path=path, sample_interval=interval, mode="SAMPLE"))
        sublist = gnmi_pb2.SubscriptionList(subscriptions=subscriptions,encoding=encoding)
        subreq = [gnmi_pb2.SubscribeRequest(subscribe=sublist)]
        stream = self._stub.Subscribe(subreq, metadata=self._metadata)
        for unit in stream:
            yield unit

    def connectivityhandler(self, callback):
        """Passing of a callback to monitor connectivety state updates.
        :param callback: A callback for monitoring
        :type: function
        """
        self._channel.subscribe(callback, True)