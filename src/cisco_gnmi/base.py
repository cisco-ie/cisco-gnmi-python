import ssl
import logging
import json

import grpc
import cryptography
from .util import gen_target_netloc


class Base(object):

    """Defining property due to gRPC timeout being based on a C long type.
    Should really define this based on architecture.
    32-bit C long max value. "Infinity".
    """

    _C_MAX_LONG = 2147483647

    _NS_IN_S = int(1e9)

    def __init__(self, target, timeout=_C_MAX_LONG):
        self.target_netloc = gen_target_netloc(target)
        self.timeout = timeout
        self.username = None
        self.password = None
        self.channel_creds = None
        self.channel_options = None
        self.channel = None
        self.service_class = None
        self.service = None

    def with_authentication(self, username, password):
        self.username = username
        self.password = password
        return self

    def apply_service(self, service_class):
        if not self.channel:
            raise Exception("Must initialize channel before service!")
        self.service_class = service_class
        self.service = service_class(self.channel)
        return self

    def as_secure(
        self,
        root_certificates=None,
        private_key=None,
        certificate_chain=None,
        root_from_target=False,
        target_name_from_root=False,
        channel_options=None,
        from_file=False,
    ):
        """Creates a secure channel for gRPC with the specified options.
        This is effectively just a wrapper around grpc.ssl_channel_credentials and grpc.secure_channel.
        Does not assume certs should be loaded from file by default.
        Includes functionality to automatically acquire server root certificate akin to Go.
        https://docs.python.org/2/library/ssl.html#ssl.get_server_certificate
        """
        if self.channel:
            self.channel.close()
        self.channel_options = channel_options

        def get_cert_content(filepath):
            cert_content = None
            with open(filepath, "rb") as cert_fd:
                cert_content = cert_fd.read()
            return cert_content

        def get_cert_from_target(target):
            return ssl.get_server_certificate(
                (self.target_netloc.hostname, self.target_netloc.port)
            ).encode("utf-8")

        def get_cn_from_cert(cert_pem):
            cert_cn = None
            cert_parsed = cryptography.x509.load_pem_x509_certificate(
                cert_pem, cryptography.hazmat.backends.default_backend()
            )
            cert_cns = cert_parsed.subject.get_attributes_for_oid(
                cryptography.x509.oid.NameOID.COMMON_NAME
            )
            if len(cert_cns):
                if len(cert_cns) > 1:
                    logging.warning(
                        "Multiple CNs found for certificate, defaulting to the first one."
                    )
                cert_cn = cert_cns[0].value
                logging.debug("Using %s as certificate CN.", cert_cn)
            else:
                logging.warning("No CN found for certificate.")
            return cert_cn

        private_key = get_cert_content(private_key) if from_file else private_key
        certificate_chain = (
            get_cert_content(certificate_chain) if from_file else certificate_chain
        )
        if root_certificates and root_from_target:
            logging.warning(
                "Root certificates specified, not discovering root from target."
            )
            root_certificates = (
                get_cert_content(root_certificates) if from_file else root_certificates
            )
        elif root_from_target:
            root_certificates = get_cert_from_target(self.target_netloc)
            if target_name_from_root:
                logging.warning(
                    "Overriding SSL target name, this is effectively insecure."
                )
                cert_cn = get_cn_from_cert(root_certificates)
                server_option = ("grpc.ssl_target_name_override", cert_cn)
                if not cert_cn:
                    logging.warning("No CN found, not altering channel options.")
                if self.channel_options:
                    logging.warning(
                        "Modifying passed channel options to override server name from root certificate."
                    )
                    found_index = None
                    for index, option in enumerate(self.channel_options):
                        if option[0] == "grpc.ssl_target_name_override":
                            found_index = index
                            break
                    if found_index is not None:
                        self.channel_options[found_index] = server_option
                    else:
                        self.channel_options.append(server_option)
                else:
                    self.channel_options = [server_option]
        self.channel_creds = grpc.ssl_channel_credentials(
            root_certificates, private_key, certificate_chain
        )
        self.channel = grpc.secure_channel(
            self.target_netloc.netloc, self.channel_creds, self.channel_options
        )
        if self.service_class:
            self.apply_service(self.service_class)
        return self

    def as_insecure(self, channel_options=None, compression=None):
        logging.warning(
            "TLS MUST be enabled per gNMI specification. If utilizing the gNMI implementation without TLS, it is non-compliant."
        )
        if self.channel:
            self.channel.close()
        if self.channel_creds:
            self.channel_creds = None
        self.channel_options = channel_options
        self.channel = grpc.insecure_channel(
            self.target_netloc.netloc, self.channel_options, compression
        )
        if self.service_class:
            self.apply_service(self.service_class)
        return self

    def _gen_metadata(self):
        """Generates expected gRPC call metadata."""
        return [("username", self.username), ("password", self.password)]

    def __str__(self):
        """JSON dump a dict of basic attributes."""
        return json.dumps(
            {
                "class": str(self.__class__),
                "target": self.target_netloc.netloc,
                "is_authenticated": bool(self.username),
                "is_secure": bool(self.channel_creds),
            }
        )
