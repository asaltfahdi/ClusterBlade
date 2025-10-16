from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from clusterblade.core.paths import get_runtime_dir


def render_es_config(
    cluster_name,
    node,
    master_nodes,
    enable_security=True,
    enable_ssl=True,
    enable_http=False,
    http_groups=None,
    enable_logging=False,
    memory_lock=False
):
    """
    Render elasticsearch.yml for a given node.
    Uses Jinja2 template (clusterblade/templates/elasticsearch.yml.j2)
    and writes to runtime/generated_configs/{node_name}/elasticsearch.yml
    """

    template_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=select_autoescape())

    try:
        template = env.get_template("elasticsearch.yml.j2")
    except Exception as e:
        raise FileNotFoundError(f"❌ Missing elasticsearch.yml.j2 in {template_dir}\n{e}")

    # Identify master group
    master_ips = [m["ip"] for m in master_nodes]
    master_names = [m["name"] for m in master_nodes]

    node_name = node.get("name", "unknown")
    node_ip = node.get("ip", "127.0.0.1")
    node_rack = node.get("rack", "r1")

    # Infer group
    lower = node_name.lower()
    if "master" in lower:
        node_group = "master"
    elif "data" in lower:
        node_group = "data"
    elif "ingest" in lower:
        node_group = "ingest"
    else:
        node_group = "coordinator"

    # HTTP enable flag
    http_enabled = enable_http and node_group in (http_groups or [])

    # Template context
    context = {
        "cluster_name": cluster_name,
        "node": {"name": node_name, "ip": node_ip, "rack": node_rack},
        "master_ips": master_ips,
        "master_names": master_names,
        "enable_security": enable_security,
        "enable_ssl": enable_ssl,
        "enable_http": http_enabled,
        "enable_logging": enable_logging,
        "memory_lock": memory_lock,
    }

    # Render YAML
    rendered = template.render(**context)

    # Output path
    output_dir = get_runtime_dir() / "generated_configs" / node_name
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "elasticsearch.yml"
    out_file.write_text(rendered, encoding="utf-8")

    print(f"✅ Config rendered for {node_name} ({node_group}) -> {out_file}")
    return str(out_file)
