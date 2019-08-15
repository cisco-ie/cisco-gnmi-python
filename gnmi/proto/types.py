from enum import Enum
from . import gnmi_pb2

class Encoding(Enum):
    JSON = gnmi_pb2.Encoding.JSON
    BYTES = gnmi_pb2.Encoding.BYTES
    PROTO = gnmi_pb2.Encoding.PROTO
    ASCII = gnmi_pb2.Encoding.ASCII
    JSON_IETF = gnmi_pb2.Encoding.JSON_IETF

class SubscriptionList_Mode(Enum):
    STREAM = gnmi_pb2.SubscriptionList.Mode.STREAM
    ONCE = gnmi_pb2.SubscriptionList.Mode.ONCE
    POLL = gnmi_pb2.SubscriptionList.Mode.POLL

class SubscriptionMode(Enum):
    TARGET_DEFINED = gnmi_pb2.SubscriptionMode.TARGET_DEFINED
    ON_CHANGE = gnmi_pb2.SubscriptionMode.ON_CHANGE
    SAMPLE = gnmi_pb2.SubscriptionMode.SAMPLE

class UpdateResult_Operation(Enum):
    INVALID = gnmi_pb2.UpdateResult.Operation.INVALID
    DELETE = gnmi_pb2.UpdateResult.Operation.DELETE
    REPLACE = gnmi_pb2.UpdateResult.Operation.REPLACE
    UPDATE = gnmi_pb2.UpdateResult.Operation.UPDATE

class GetRequest_DataType(Enum):
    ALL = gnmi_pb2.GetRequest.DataType.ALL
    CONFIG = gnmi_pb2.GetRequest.DataType.CONFIG
    STATE = gnmi_pb2.GetRequest.DataType.STATE
    OPERATIONAL = gnmi_pb2.GetRequest.DataType.OPERATIONAL