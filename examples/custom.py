#!/usr/bin/env python
"""Copyright 2020 Cisco Systems
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

"""Custom usage, no wrapper.
Because we're not using a wrapper, we are going to need to build our own protos.
"""

from cisco_gnmi import ClientBuilder, proto

"""First let's build a Client. We are not going to specify an OS
name here resulting in just the base Client returned without any OS
convenience methods. Client does have some level of "convenience" built-in
insofar as it doesn't take direct <RPC>Requests (SubscribeRequest) etc.
To directly use the gNMI RPCs access via client.service.<RPC>().
So - either:
  * Pass args to the client.<RPC>() methods.
  * Pass full <RPC>Request protos to client.service.<RPC>()
This code passes args to the client.<RPC>() methods.
"""
client = (
    ClientBuilder("127.0.0.1:9339")
    .set_secure_from_target()
    .set_ssl_target_override()
    .set_authentication("admin", "its_a_secret")
    .construct()
)
"""Capabilities is an easy RPC to test."""
capabilities = client.capabilities()
print(capabilities)
"""Let's build a Get!
client.get() expects a list of Paths as the primary method of interaction.
client.parse_xpath_to_gnmi_path is a convenience method to..parse an XPath to a Path.
Generally OS wrappers will override this function to specialize on origins, etc.
But we are not using a wrapper, and if using OpenConfig pathing we don't need an origin.
"""
get_path = client.parse_xpath_to_gnmi_path("/interfaces/interface/state/counters")
get_response = client.get([get_path], data_type="STATE", encoding="JSON_IETF")
print(get_response)
"""Let's build a sampled Subscribe!
client.subscribe() accepts an iterable of SubscriptionLists
"""
subscription_list = proto.gnmi_pb2.SubscriptionList()
subscription_list.mode = proto.gnmi_pb2.SubscriptionList.Mode.Value("STREAM")
subscription_list.encoding = proto.gnmi_pb2.Encoding.Value("PROTO")
sampled_subscription = proto.gnmi_pb2.Subscription()
sampled_subscription.path.CopyFrom(
    client.parse_xpath_to_gnmi_path("/interfaces/interface/state/counters")
)
sampled_subscription.mode = proto.gnmi_pb2.SubscriptionMode.Value("SAMPLE")
sampled_subscription.sample_interval = 10 * int(1e9)
subscription_list.subscription.append(sampled_subscription)
# Only print 2 responses
for msg_idx, subscribe_response in enumerate(client.subscribe([subscription_list])):
    print(subscribe_response)
    if msg_idx + 1 == 2:
        break
"""Now let's do ON_CHANGE. Just have to put SubscriptionMode to ON_CHANGE."""
subscription_list = proto.gnmi_pb2.SubscriptionList()
subscription_list.mode = proto.gnmi_pb2.SubscriptionList.Mode.Value("STREAM")
subscription_list.encoding = proto.gnmi_pb2.Encoding.Value("PROTO")
onchange_subscription = proto.gnmi_pb2.Subscription()
onchange_subscription.path.CopyFrom(
    client.parse_xpath_to_gnmi_path(
        "/syslog/messages/message", origin="Cisco-IOS-XR-infra-syslog-oper"
    )
)
onchange_subscription.mode = proto.gnmi_pb2.SubscriptionMode.Value("ON_CHANGE")
subscription_list.subscription.append(onchange_subscription)
# Only print 2 responses
for msg_idx, subscribe_response in enumerate(client.subscribe([subscription_list])):
    print(subscribe_response)
    if msg_idx + 1 == 2:
        break
"""Let's build a Set!
client.set() expects updates, replaces, and/or deletes to be provided.
updates is a list of Updates
replaces is a list of Updates
deletes is a list of Paths
Let's do an update, and then a delete.
"""
set_update = proto.gnmi_pb2.Update()
set_json = """
{
    "config": {
        "login-banner": "Hello, gNMI!"
    }
}
"""
