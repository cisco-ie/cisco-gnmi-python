#!/usr/bin/env python
"""
Command parsing sourced from this wonderful blog by Chase Seibert
https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html
"""
import json
import logging
import argparse
from getpass import getpass
from google.protobuf import json_format, text_format
from . import ClientBuilder
import sys


def main():
    # Using a map so we don't have function overlap e.g. set()
    rpc_map = {
        "capabilities": gnmi_capabilities,
        "subscribe": gnmi_subscribe,
        "get": gnmi_get,
        "set": gnmi_set
    }
    parser = argparse.ArgumentParser(description="gNMI CLI demonstrating library usage.", usage="""
    gnmcli <rpc> [<args>]

    Supported RPCs:
    %s

    See --help for RPC options.
    """.format('\n'.join(rpc_map.keys())))
    parser.add_argument("rpc", help="gNMI RPC to perform against network element.")
    if len(sys.argv) < 2:
        logging.error("Must at minimum provide RPC and required arguments!")
        parser.print_help()
        exit(1)
    args = parser.parse_args(sys.argv[1:2])
    if args.rpc not in rpc_map.keys():
        logging.error("%s not in supported RPCs: %s!", args.rpc, ', '.join(rpc_map.keys()))
        parser.print_help()
        exit(1)
    rpc_map[args.rpc]()

def gnmi_capabilities():
    parser = argparse.ArgumentParser(
        description="Performs Capabilities RPC against network element."
    )
    args = __common_args_handler(parser)

def gnmi_subscribe():
    parser = argparse.ArgumentParser(
        description="Performs Subscribe RPC against network element."
    )
    args = __common_args_handler(parser)
    pass

def gnmi_get():
    parser = argparse.ArgumentParser(
        description="Performs Get RPC against network element."
    )
    args = __common_args_handler(parser)

def gnmi_set():
    parser = argparse.ArgumentParser(
        description="Performs Set RPC against network element."
    )
    args = __common_args_handler(parser)

def __gen_client(netloc, os_name, username, password, root_certificates=None, private_key=None, certificate_chain=None, ssl_target_override=None, auto_ssl_target_override=False):
    builder = ClientBuilder(netloc)
    builder.set_os(os_name)
    builder.set_call_authentication(username, password)
    if not any([root_certificates, private_key, certificate_chain]):
        builder.set_secure_from_target()
    else:
        builder.set_secure_from_file(root_certificates, private_key, certificate_chain)
    if ssl_target_override:
        builder.set_ssl_target_override(ssl_target_override)
    elif auto_ssl_target_override:
        builder.set_ssl_target_override()
    return builder.construct()

def __common_args_handler(parser):
    """Ideally would be a decorator."""
    parser.add_argument("netloc", help="<host>:<port>", type=str)
    parser.add_argument(
        "-os",
        help="OS to use.",
        type=str,
        default="IOS XR",
        choices=list(ClientBuilder.os_class_map.keys()),
    )
    parser.add_argument("-root_certificates", description="Root certificates for secure connection.")
    parser.add_argument("-private_key", description="Private key for secure connection.")
    parser.add_argument("-certificate_chain", description="Certificate chain for secure connection.")
    parser.add_argument("-ssl_target_override", description="gRPC SSL target override option.")
    parser.add_argument("-auto_ssl_target_override", description="Root certificates for secure connection.", action="store_true")
    parser.add_argument("-debug", help="Print debug messages", action="store_true")
    args = parser.parse_args(sys.argv[2:])
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    args.username = input("Username: ")
    args.password = getpass()
    return args


if __name__ == "__main__":
    main()