#!/usr/bin/env bash
echo "Updating proto sources..."
git submodule update --remote
echo "Compiling protos..."
python -m grpc_tools.protoc --proto_path=. --python_out=gnmi-python/proto --grpc_python_out=gnmi-python/proto github.com/openconfig/gnmi/proto/gnmi/gnmi.proto
echo "Copying compiled protos..."
cp gnmi-python/proto/github/com/openconfig/gnmi/proto/gnmi/*.py gnmi-python/proto/
echo "Copying compiled gRPC stubs..."
cp gnmi-python/proto/github.com/openconfig/gnmi/proto/gnmi/*.py gnmi-python/proto/
echo "Cleaning up..."
rm -rf gnmi-python/proto/github
rm -rf gnmi-python/proto/github.com
