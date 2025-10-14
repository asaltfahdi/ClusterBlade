from pathlib import Path

def get_base_dir() -> Path:
    """
    Returns the base directory of the project — the folder that contains
    the `clusterblade/` package.
    """
    # __file__ = clusterblade/core/paths.py
    return Path(__file__).resolve().parent.parent.parent


def get_runtime_dir() -> Path:
    """
    Runtime directory base (same as project root).
    """
    base = get_base_dir()
    runtime = base / "runtime"
    runtime.mkdir(exist_ok=True)
    return runtime


def get_templates_dir() -> Path:
    """
    Directory for Jinja2 templates (outside package source).
    """
    path = get_runtime_dir() / "templates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_certificates_dir() -> Path:
    """
    Directory for generated certificates (outside package source).
    """
    path = get_runtime_dir() / "certificates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    """
    Directory for generated logs.
    """
    path = get_runtime_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
