from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
from pathlib import Path
import ipaddress
import yaml
import shutil


def cleanup_old_certs(cert_dir: Path):
    """Delete all existing certificates and keys."""
    if cert_dir.exists():
        print(f"🧹 Cleaning old certificates in {cert_dir}...")
        for item in cert_dir.iterdir():
            if item.is_file():
                item.unlink()
        print("✅ Old certificates removed.")
    else:
        cert_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created new certificate directory: {cert_dir}")


def generate_ca(cert_dir: Path):
    """Generate a new CA certificate and private key."""
    print("🔧 Generating new Root CA...")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "OM"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ClusterBlade"),
        x509.NameAttribute(NameOID.COMMON_NAME, "ClusterBlade Root CA"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    ca_key_path = cert_dir / "ca.key"
    ca_cert_path = cert_dir / "ca.pem"

    with open(ca_key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )
    with open(ca_cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"✅ Created new CA certificate: {ca_cert_path}")
    return ca_cert_path, ca_key_path


def generate_node_cert(cert_dir: Path, node_name: str, node_ip: str, ca_cert_path: Path, ca_key_path: Path, password: bytes | None = None):
    """Generate per-node PEM cert and key signed by CA."""
    key_path = cert_dir / f"{node_name}.key"
    cert_path = cert_dir / f"{node_name}.crt"

    # Load CA
    with open(ca_cert_path, "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read())
    with open(ca_key_path, "rb") as f:
        ca_key = serialization.load_pem_private_key(f.read(), password=None)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ClusterBlade Node"),
        x509.NameAttribute(NameOID.COMMON_NAME, node_name),
    ])

    alt_names = [
        x509.DNSName(node_name),
        x509.IPAddress(ipaddress.ip_address(node_ip))
    ]

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.BestAvailableEncryption(password)
                if password else serialization.NoEncryption()
            )
        )
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"✅ Generated new certificate for {node_name} ({node_ip})")
    return cert_path, key_path


def generate_all_from_yaml(yaml_path: Path, cert_dir: Path, password: bytes | None = None):
    """Regenerate all certs fresh based on instances.yaml."""
    print("📖 Reading instances from YAML file...")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    instances = data.get("instances") or data.get("nodes")
    if not instances:
        print("❌ No instances found in YAML file.")
        return

    # Always wipe and start fresh
    cleanup_old_certs(cert_dir)

    # Create new CA
    ca_cert, ca_key = generate_ca(cert_dir)

    # Generate new certs for all nodes
    for node in instances:
        name = node.get("name")
        ip = node.get("ip")
        if not name or not ip:
            print(f"⚠️ Skipping node with incomplete data: {node}")
            continue

        generate_node_cert(cert_dir, name, ip, ca_cert, ca_key, password)

    print("\n🎉 All node certificates regenerated successfully!")

def generate_http_certs(cert_dir: Path, ca_cert_path: Path, ca_key_path: Path):
    """
    Generate HTTPS (HTTP layer) certificates signed by existing CA.

    Creates:
      - http.key
      - http.crt
      - ca.crt (copy of CA certificate)
    """

    cert_dir.mkdir(parents=True, exist_ok=True)

    # --- Load existing CA certificate and key ---
    with open(ca_cert_path, "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read())
    with open(ca_key_path, "rb") as f:
        ca_key = serialization.load_pem_private_key(f.read(), password=None)

    # --- Generate private key for HTTP layer ---
    http_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # --- Build certificate ---
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"OM"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"ClusterBlade"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"Elasticsearch HTTP Layer"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(http_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(u"localhost"),
                x509.DNSName(u"elasticsearch"),
            ]),
            critical=False,
        )
        .sign(private_key=ca_key, algorithm=hashes.SHA256())
    )

    # --- Save files ---
    http_key_path = cert_dir / "http.key"
    http_cert_path = cert_dir / "http.crt"
    http_ca_path = cert_dir / "ca.crt"

    with open(http_key_path, "wb") as f:
        f.write(
            http_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with open(http_cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Copy CA certificate for completeness
    with open(http_ca_path, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    return {
        "key": str(http_key_path),
        "cert": str(http_cert_path),
        "ca": str(http_ca_path),
    }

# Example CLI usage:
# python -m clusterblade.certificates.generator runtime/instances.yaml runtime/certificates
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m clusterblade.certificates.generator <instances.yaml> <output_dir>")
    else:
        yaml_file = Path(sys.argv[1])
        output_dir = Path(sys.argv[2])
        generate_all_from_yaml(yaml_file, output_dir)
