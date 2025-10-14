from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from clusterblade.core.paths import get_runtime_dir

def render_es_config(
    cluster_name,
    node,
    master_nodes,
    enable_ssl=True,
    enable_http=False,
    http_groups=None
):
    """
    Render elasticsearch.yml for a given node.
    Template is inside project (clusterblade/templates).
    Output YAML is outside in runtime/generated_configs.
    """

    # Template directory inside the package
    template_dir = Path(__file__).resolve().parent.parent / "templates"
    template_dir_str = str(template_dir.as_posix())

    env = Environment(
        loader=FileSystemLoader(template_dir_str),
        autoescape=select_autoescape()
    )

    try:
        template = env.get_template("elasticsearch.yml.j2")
    except Exception as e:
        raise FileNotFoundError(
            f"❌ Could not find elasticsearch.yml.j2 inside {template_dir_str}\n{e}"
        )

    # Prepare render context
    master_ips = [m["ip"] for m in master_nodes]
    master_names = [m["name"] for m in master_nodes]

    # Infer node group from name
    node_name_lower = node["name"].lower()
    if "master" in node_name_lower:
        node_group = "master"
    elif "data" in node_name_lower:
        node_group = "data"
    elif "ingest" in node_name_lower:
        node_group = "ingest"
    else:
        node_group = "coordinator"

    # Should this node get HTTP SSL?
    http_enabled_for_node = enable_http and node_group in (http_groups or [])

    # Prepare Jinja context
    context = {
        "cluster_name": cluster_name,
        "node": node,
        "master_ips": master_ips,
        "master_names": master_names,
        "enable_ssl": enable_ssl,
        "enable_http": http_enabled_for_node,
    }

    # Render the template
    content = template.render(**context)

    # Output directory (outside project)
    output_dir = get_runtime_dir() / "generated_configs"
    output_dir.mkdir(parents=True, exist_ok=True)

    out_file = output_dir / f"elasticsearch.yml"
    out_file.write_text(content, encoding="utf-8")

    print(f"✅ Rendered config for {node['name']} ({node_group}) at: {out_file}")
    return str(out_file)
