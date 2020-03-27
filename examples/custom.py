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

"""Custom usage, no wrapper."""

from cisco_gnmi import ClientBuilder, proto

client = ClientBuilder(
    '127.0.0.1:9339'
).set_secure_from_target().set_ssl_target_override().set_authentication(
    'admin',
    'its_a_secret'
).construct()
capabilities = client.capabilities()
print(capabilities)
subscription_list = proto.gnmi_pb2.SubscriptionList()
subscription_list.mode = proto.gnmi_pb2.SubscriptionList.Mode.Value("STREAM")
subscription_list.encoding = proto.gnmi_pb2.Encoding.Value("PROTO")
subscription = proto.gnmi_pb2.Subscription()
subscription.path.CopyFrom(client.parse_xpath_to_gnmi_path("/interfaces/interface/state/counters"))
subscription.mode = proto.gnmi_pb2.SubscriptionMode.Value("ON_CHANGE")
subscription_list.subscription.append(subscription)
for message in client.subscribe([subscription_list]):
    print(message)