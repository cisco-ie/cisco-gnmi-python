#!/usr/bin/env bash
echo "Updating proto sources..."
git submodule update --remote
cp github.com/openconfig/gnmi/proto/gnmi/*.proto cisco_gnmi/proto/
cp github.com/openconfig/gnmi/proto/gnmi_ext/*.proto cisco_gnmi/proto/
echo "Fixing proto imports..."
python -c "
with open('cisco_gnmi/proto/gnmi.proto', 'r') as gnmi_fd:
  file_content = gnmi_fd.read()
file_content = file_content.replace('github.com/openconfig/gnmi/proto/gnmi_ext/', '', 1)
with open('cisco_gnmi/proto/gnmi.proto', 'w') as gnmi_fd:
  gnmi_fd.write(file_content)
"
echo "Compiling protos..."
pipenv run python -m grpc_tools.protoc --proto_path=cisco_gnmi/proto --python_out=cisco_gnmi/proto --grpc_python_out=cisco_gnmi/proto gnmi.proto gnmi_ext.proto
echo "Fixing compiled Python imports..."
python -c "
with open('cisco_gnmi/proto/gnmi_pb2_grpc.py', 'r') as gnmi_fd:
  file_content = gnmi_fd.read()
file_content = file_content.replace('import gnmi_pb2', 'from . import gnmi_pb2', 1)
with open('cisco_gnmi/proto/gnmi_pb2_grpc.py', 'w') as gnmi_fd:
  gnmi_fd.write(file_content)
with open('cisco_gnmi/proto/gnmi_pb2.py', 'r') as gnmi_fd:
  file_content = gnmi_fd.read()
file_content = file_content.replace('import gnmi_ext_pb2', 'from . import gnmi_ext_pb2', 1)
with open('cisco_gnmi/proto/gnmi_pb2.py', 'w') as gnmi_fd:
  gnmi_fd.write(file_content)
"
echo "Cleaning up..."
rm cisco_gnmi/proto/*.proto
