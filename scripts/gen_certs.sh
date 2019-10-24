#!/usr/bin/env bash
# Derived from https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/prog/configuration/1612/b_1612_programmability_cg/grpc_network_management_interface.html#id_89031

CERT_BASE="certs"

if [ -z $1 ]; then
    echo "Usage: gen_certs.sh <hostname> [<password>]"
    exit 1
fi

mkdir -p $CERT_BASE

# Setting up a CA
openssl genrsa -out $CERT_BASE/rootCA.key 2048
openssl req -subj /C=/ST=/L=/O=/CN=rootCA -x509 -new -nodes -key $CERT_BASE/rootCA.key -sha256 -out $CERT_BASE/rootCA.pem

# Setting up device cert and key
openssl genrsa -out $CERT_BASE/device.key 2048
openssl req -subj /C=/ST=/L=/O=/CN=$1 -new -key $CERT_BASE/device.key -out $CERT_BASE/device.csr
openssl x509 -req -in $CERT_BASE/device.csr -CA $CERT_BASE/rootCA.pem -CAkey $CERT_BASE/rootCA.key -CAcreateserial -out $CERT_BASE/device.crt -sha256

# Encrypt device key - needed for input to IOS
if [ ! -z $2 ]; then
    openssl rsa -des3 -in $CERT_BASE/device.key -out $CERT_BASE/device.des3.key -passout pass:$2
else
    echo "Skipping device key encryption."
fi

# Setting up client cert and key
openssl genrsa -out $CERT_BASE/client.key 2048
openssl req -subj /C=/ST=/L=/O=/CN=gnmi_client -new -key $CERT_BASE/client.key -out $CERT_BASE/client.csr
openssl x509 -req -in $CERT_BASE/client.csr -CA $CERT_BASE/rootCA.pem -CAkey $CERT_BASE/rootCA.key -CAcreateserial -out $CERT_BASE/client.crt -sha256