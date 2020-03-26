#!/usr/bin/env python
"""
Wraps gNMI RPCs with a reasonably useful CLI for interacting with network elements.


Command parsing sourced from this wonderful blog by Chase Seibert
https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html
"""
import json
import logging
import argparse
from getpass import getpass
from google.protobuf import json_format, text_format
from . import ClientBuilder, proto
from google.protobuf.internal import enum_type_wrapper
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
    client = __gen_client(args)
    logging.info(client.capabilities())

def gnmi_subscribe():
    """Performs a sampled Subscribe against network element.
    TODO: ON_CHANGE
    """
    parser = argparse.ArgumentParser(
        description="Performs Subscribe RPC against network element."
    )
    parser.add_argument(
        "-xpath",
        help="XPath to subscribe to.",
        type=str,
        action="append"
    )
    parser.add_argument(
        "-interval",
        help="Sample interval in seconds for Subscription.",
        type=int,
        default=10*int(1e9)
    )
    parser.add_argument(
        "-dump_file",
        help="Filename to dump to. Defaults to stdout.",
        type=str,
        default="stdout"
    )
    parser.add_argument(
        "-dump_json",
        help="Dump as JSON instead of textual protos.",
        action="store_true"
    )
    parser.add_argument(
        "-sync_stop", help="Stop on sync_response.", action="store_true"
    )
    parser.add_argument(
        "-encoding", help="gNMI subscription encoding.", type=str, nargs="?", choices=list(proto.gnmi_pb2.Encoding.keys())
    )
    args = __common_args_handler(parser)
    # Set default XPath outside of argparse due to default being persistent in argparse.
    if not args.xpath:
        args.xpath = ["/interfaces/interface/state/counters"]
    client = __gen_client(args)
    # Take care not to override options unnecessarily.
    kwargs = {}
    if args.encoding:
        kwargs["encoding"] = args.encoding
    if args.sample_interval:
        kwargs["sample_interval"] = args.sample_interval
    try:
        logging.info("Dumping responses to %s as %s ...", args.dump_file, "JSON" if args.dump_json else "textual proto")
        logging.info("Subscribing to:\n%s", '\n'.join(args.xpath))
        for subscribe_response in client.subscribe_xpaths(args.xpath, **kwargs):
            if subscribe_response.sync_response:
                logging.debug("sync_response received.")
                if args.sync_stop:
                    logging.warning("Stopping on sync_response.")
                    break
            formatted_message = None
            if args.dump_json:
                formatted_message = json_format.MessageToJson(subscribe_response, sort_keys=True)
            else:
                formatted_message = text_format.MessageToString(subscribe_response)
            if args.dump_file == "stdout":
                logging.info(formatted_message)
            else:
                with open(args.dump_file, "a") as dump_fd:
                    dump_fd.write(formatted_message)
    except KeyboardInterrupt:
        logging.warning("Stopping on interrupt.")
    except Exception:
        logging.exception("Stopping due to exception!")

def gnmi_get():
    parser = argparse.ArgumentParser(
        description="Performs Get RPC against network element."
    )
    parser.add_argument(
        "-xpath",
        help="XPaths to Get.",
        type=str,
        action="append"
    )
    parser.add_argument(
        "-encoding", help="gNMI subscription encoding.", type=str, nargs="?", choices=list(proto.gnmi_pb2.Encoding.keys())
    )
    parser.add_argument(
        "-data_type", help="gNMI GetRequest DataType", type=str, nargs="?", choices=list(enum_type_wrapper.EnumTypeWrapper(proto.gnmi_pb2._GETREQUEST_DATATYPE).keys())
    )
    parser.add_argument(
        "-dump_json",
        help="Dump as JSON instead of textual protos.",
        action="store_true"
    )
    args = __common_args_handler(parser)
    # Set default XPath outside of argparse due to default being persistent in argparse.
    if not args.xpath:
        args.xpath = ["/interfaces/interface/state/counters"]
    client = __gen_client(args)
    kwargs = {}
    if args.encoding:
        kwargs["encoding"] = args.encoding
    if args.data_type:
        kwargs["data_type"] = args.data_type
    get_response = client.get_xpaths(args.xpath, **kwargs)
    formatted_message = None
    if args.dump_json:
        formatted_message = json_format.MessageToJson(get_response, sort_keys=True)
    else:
        formatted_message = text_format.MessageToString(get_response)
    logging.info(formatted_message)

def gnmi_set():
    parser = argparse.ArgumentParser(
        description="Performs Set RPC against network element."
    )
    args = __common_args_handler(parser)
    client = __gen_client(args)


def __gen_client(args):
    builder = ClientBuilder(args.netloc)
    builder.set_os(args.os)
    builder.set_call_authentication(args.username, args.password)
    if not any([args.root_certificates, args.private_key, args.certificate_chain]):
        builder.set_secure_from_target()
    else:
        builder.set_secure_from_file(args.root_certificates, args.private_key, args.certificate_chain)
    if args.ssl_target_override:
        builder.set_ssl_target_override(args.ssl_target_override)
    elif args.auto_ssl_target_override:
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