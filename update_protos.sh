#!/usr/bin/env bash
echo "Updating proto sources..."
git submodule update --remote
cp github.com/openconfig/gnmi/proto/gnmi/*.proto gnmi/proto/
cp github.com/openconfig/gnmi/proto/gnmi_ext/*.proto gnmi/proto/
echo "Fixing proto imports..."
python -c "
with open('gnmi/proto/gnmi.proto', 'r') as gnmi_fd:
  file_content = gnmi_fd.read()
file_content = file_content.replace('github.com/openconfig/gnmi/proto/gnmi_ext/', '', 1)
with open('gnmi/proto/gnmi.proto', 'w') as gnmi_fd:
  gnmi_fd.write(file_content)
"
echo "Compiling protos..."
python -m grpc_tools.protoc --proto_path=gnmi/proto --python_out=gnmi/proto --grpc_python_out=gnmi/proto gnmi.proto gnmi_ext.proto
echo "Fixing compiled Python imports..."
python -c "
with open('gnmi/proto/gnmi_pb2_grpc.py', 'r') as gnmi_fd:
  file_content = gnmi_fd.read()
file_content = file_content.replace('import gnmi_pb2', 'from . import gnmi_pb2', 1)
with open('gnmi/proto/gnmi_pb2_grpc.py', 'w') as gnmi_fd:
  gnmi_fd.write(file_content)
with open('gnmi/proto/gnmi_pb2.py', 'r') as gnmi_fd:
  file_content = gnmi_fd.read()
file_content = file_content.replace('import gnmi_ext_pb2', 'from . import gnmi_ext_pb2', 1)
with open('gnmi/proto/gnmi_pb2.py', 'w') as gnmi_fd:
  gnmi_fd.write(file_content)
"
echo "Cleaning up..."
rm gnmi/proto/*.proto
