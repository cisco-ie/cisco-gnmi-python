#!/usr/bin/env bash
# Derived from https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/prog/configuration/1612/b_1612_programmability_cg/grpc_network_management_interface.html#id_89031

CERT_BASE="certs"

if [ -z $1 ] || [ -z $2 ]; then
    echo "Usage: gen_certs.sh <server_hostname> <ip> [<password>]"
    exit 1
fi

server_hostname=$1
ip=$2
password=$3

mkdir -p $CERT_BASE

function print_red () {
    printf "\033[0;31m$1 ...\033[0m\n"
}

# Setting up a CA
if [ -f "$CERT_BASE/rootCA.key" ] && [ -f "$CERT_BASE/rootCA.pem" ]; then
    print_red "SKIPPING rootCA generation, already exist"
else
    print_red "GENERATING rootCA"
    openssl genrsa -out $CERT_BASE/rootCA.key 2048
    openssl req -subj /C=/ST=/L=/O=/CN=rootCA -x509 -new -nodes -key $CERT_BASE/rootCA.key -sha256 -days 1095 -out $CERT_BASE/rootCA.pem
fi

# Setting up device cert and key
print_red "GENERATING device certificates with CN $server_hostname and IP $ip"
openssl genrsa -out $CERT_BASE/device.key 2048
openssl req -subj /C=/ST=/L=/O=/CN=$server_hostname -new -key $CERT_BASE/device.key -out $CERT_BASE/device.csr
openssl x509 -req -in $CERT_BASE/device.csr -CA $CERT_BASE/rootCA.pem -CAkey $CERT_BASE/rootCA.key -CAcreateserial -out $CERT_BASE/device.crt -days 1095 -sha256 -extfile <(printf "%s" "subjectAltName=DNS:$server_hostname,IP:$ip")

# Encrypt device key
if [ ! -z $password ]; then
    print_red "ENCRYPTING device certificates and bundling with password"
    # DES 3 for device, needed for input to IOS XE
    openssl rsa -des3 -in $CERT_BASE/device.key -out $CERT_BASE/device.des3.key -passout pass:$password
    # PKCS #12 for device, needed for NX-OS
    # Uncertain if this is correct
    openssl pkcs12 -export -out $CERT_BASE/device.pfx -inkey $CERT_BASE/device.key -in $CERT_BASE/device.crt -certfile $CERT_BASE/rootCA.pem -password pass:$password
else
    print_red "SKIPPING device key encryption"
fi

# Setting up client cert and key
if [ -f "$CERT_BASE/client.key" ] && [ -f "$CERT_BASE/client.crt" ]; then
    print_red "SKIPPING client certificates generation, already exist"
else
    hostname=$(hostname)
    print_red "GENERATING client certificates with CN $hostname"
    openssl genrsa -out $CERT_BASE/client.key 2048
    openssl req -subj /C=/ST=/L=/O=/CN=$hostname -new -key $CERT_BASE/client.key -out $CERT_BASE/client.csr
    openssl x509 -req -in $CERT_BASE/client.csr -CA $CERT_BASE/rootCA.pem -CAkey $CERT_BASE/rootCA.key -CAcreateserial -out $CERT_BASE/client.crt -days 1095 -sha256
fi
