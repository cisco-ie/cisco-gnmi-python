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

"""This demoes a gNMI subscription and dumping messages to a file."""
import json
import logging
import argparse
from getpass import getpass
from google.protobuf import json_format, text_format
from cisco_gnmi import ClientBuilder


def main():
    logging.basicConfig(level=logging.INFO)
    args = setup_args()
    username = input("Username: ")
    password = getpass()
    logging.info("Connecting to %s as %s ...", args.netloc, args.os)
    client = (
        ClientBuilder(args.netloc)
        .set_os(args.os)
        .set_secure_from_target()
        .set_ssl_target_override()
        .set_call_authentication(username, password)
        .construct()
    )
    formatted_messages = []
    try:
        logging.info("Subscribing to %s ...", args.xpath)
        sub_args = {"xpath_subscriptions": args.xpath}
        if args.encoding:
            sub_args["encoding"] = args.encoding
        for message in client.subscribe_xpaths(**sub_args):
            if message.sync_response and not args.no_stop:
                logging.warning("Stopping on sync_response.")
                break
            formatted_message = None
            if args.text_format is True:
                formatted_message = text_format.MessageToString(message)
            else:
                if args.raw_json:
                    formatted_message = json_format.MessageToJson(message)
                else:
                    formatted_message = json_format.MessageToDict(message)
            logging.info(formatted_message)
            formatted_messages.append(formatted_message)
    except KeyboardInterrupt:
        logging.warning("Stopping on interrupt.")
    except Exception:
        logging.exception("Stopping due to exception!")
    finally:
        logging.info("Writing to %s ...", args.protos_file)
        with open(args.protos_file, "w") as protos_fd:
            json.dump(
                formatted_messages,
                protos_fd,
                sort_keys=True,
                indent=4,
                separators=(",", ": "),
            )


def setup_args():
    parser = argparse.ArgumentParser(description="gNMI Proto Dump Example")
    parser.add_argument("netloc", help="<host>:<port>", type=str)
    parser.add_argument(
        "-os",
        help="OS to use.",
        type=str,
        default="IOS XR",
        choices=list(ClientBuilder.os_class_map.keys()),
    )
    parser.add_argument(
        "-xpath",
        help="XPath to subscribe to.",
        type=str,
        default="/interfaces/interface/state/counters",
    )
    parser.add_argument(
        "-protos_file", help="File to write protos.", type=str, default="gnmi_sub.json"
    )
    parser.add_argument(
        "-no_stop", help="Do not stop on sync_response.", action="store_true"
    )
    parser.add_argument(
        "-encoding", help="gNMI subscription encoding.", type=str, nargs="?"
    )
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
