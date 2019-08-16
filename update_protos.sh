#!/usr/bin/env bash
echo "Updating proto sources..."
git submodule update --remote
echo "Compiling protos..."
python -m grpc_tools.protoc --proto_path=. --python_out=gnmi/proto --grpc_python_out=gnmi/proto github.com/openconfig/gnmi/proto/gnmi/gnmi.proto github.com/openconfig/gnmi/proto/gnmi_ext/gnmi_ext.proto
echo "Copying compiled protos..."
cp gnmi/proto/github/com/openconfig/gnmi/proto/gnmi/*.py gnmi/proto/
cp gnmi/proto/github/com/openconfig/gnmi/proto/gnmi_ext/*.py gnmi/proto/
echo "Copying compiled gRPC stubs..."
cp gnmi/proto/github.com/openconfig/gnmi/proto/gnmi_ext/*.py gnmi/proto/
cp gnmi/proto/github.com/openconfig/gnmi/proto/gnmi/*.py gnmi/proto/
echo "Fixing imports..."
python -c "
with open('gnmi/proto/gnmi_pb2_grpc.py', 'r') as gnmi_fd:
  file_content = gnmi_fd.read()
file_content = file_content.replace('from github.com.openconfig.gnmi.proto.gnmi import', 'from . import', 1)
with open('gnmi/proto/gnmi_pb2_grpc.py', 'w') as gnmi_fd:
  gnmi_fd.write(file_content)
with open('gnmi/proto/gnmi_pb2.py', 'r') as gnmi_pb_fd:
  file_content = gnmi_pb_fd.read()
file_content = file_content.replace('from github.com.openconfig.gnmi.proto.gnmi_ext import', 'from . import', 1)
with open('gnmi/proto/gnmi_pb2.py', 'w') as gnmi_pb_fd:
  gnmi_pb_fd.write(file_content)
"
echo "Cleaning up..."
rm -rf gnmi/proto/github
rm -rf gnmi/proto/github.com
