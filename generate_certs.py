#!/usr/bin/env python3
"""
Generate self-signed certificate for local HTTPS testing.
"""
import subprocess
import os

cert_dir = os.path.join(os.path.dirname(__file__), 'certs')
os.makedirs(cert_dir, exist_ok=True)

cert_file = os.path.join(cert_dir, 'localhost.crt')
key_file = os.path.join(cert_dir, 'localhost.key')

if not os.path.exists(cert_file) or not os.path.exists(key_file):
    try:
        # Try using openssl command line
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
            '-keyout', key_file,
            '-out', cert_file,
            '-days', '365',
            '-nodes',
            '-subj', '/C=US/ST=Local/L=Local/O=Local/CN=localhost'
        ], check=True)
        print(f"✅ Certificate generated: {cert_file}")
    except FileNotFoundError:
        # Fallback: use cryptography library
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            import datetime
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Generate certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Local"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, u"Local"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Local"),
                x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365)
            ).add_extension(
                x509.SubjectAlternativeName([x509.DNSName(u"localhost"), x509.DNSName(u"*.localhost")]),
                critical=False,
            ).sign(private_key, hashes.SHA256(), default_backend())
            
            # Write certificate
            with open(cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            # Write private key
            with open(key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            print(f"✅ Certificate generated using cryptography library: {cert_file}")
        except ImportError:
            print("❌ cryptography library not found. Install with: pip install cryptography")
else:
    print(f"✅ Certificate already exists: {cert_file}")
