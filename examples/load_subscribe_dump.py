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

"""This is effectively just demo code to load the output of subscribe_dump.py
"""
import argparse
import os
import logging
import json
import cisco_gnmi
from google.protobuf import json_format, text_format


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Demo of loading protobufs from files.")
    args = setup_args()
    src_proto_array = load_proto_file(args.protos_file)
    parsed_proto_array = []
    for proto_msg in src_proto_array:
        parsed_proto = None
        if args.text_format is True:
            parsed_proto = text_format.Parse(
                proto_msg, cisco_gnmi.proto.gnmi_pb2.SubscribeResponse()
            )
        else:
            if args.raw_json:
                parsed_proto = json_format.Parse(
                    proto_msg, cisco_gnmi.proto.gnmi_pb2.SubscribeResponse()
                )
            else:
                parsed_proto = json_format.ParseDict(
                    proto_msg, cisco_gnmi.proto.gnmi_pb2.SubscribeResponse()
                )
        parsed_proto_array.append(parsed_proto)
    logging.info("Parsed %i formatted messages into objects!", len(parsed_proto_array))


def load_proto_file(filename):
    if not filename.endswith(".json"):
        raise Exception("Expected JSON file (array of messages) from proto_dump.py")
    proto_array = None
    with open(filename, "r") as protos_fd:
        proto_array = json.load(protos_fd)
    if not isinstance(proto_array, (list)):
        raise Exception("Expected array of messages from file!")
    return proto_array


def setup_args():
    parser = argparse.ArgumentParser(description="Proto Load Example")
    parser.add_argument("protos_file", help="File containing protos.", type=str)
    parser.add_argument(
        "-text_format",
        help="Protos are in text format instead of JSON.",
        action="store_true",
    )
    parser.add_argument(
        "-raw_json",
        help="Do not serialize to dict, but directly to JSON.",
        action="store_true",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
