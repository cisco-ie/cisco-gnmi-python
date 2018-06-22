#!/usr/bin/env bash
protoc --proto_path=. --python_out=gnmi-python/proto github.com/openconfig/gnmi/proto/gnmi/gnmi.proto
cp gnmi-python/proto/github/com/openconfig/gnmi/proto/gnmi/*.py gnmi-python/proto/
rm -rf gnmi-python/proto/github
