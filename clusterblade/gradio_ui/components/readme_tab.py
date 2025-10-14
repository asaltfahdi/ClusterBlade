import os
import gradio as gr

def render_readme_tab():
    """
    Displays the project's README.md file inside a Gradio tab.
    """

    # ✅ Locate README.md in project root (same level as pyproject.toml)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    readme_path = os.path.join(base_dir, "README.md")
   
    if not os.path.exists(readme_path):
        readme_content = "# 📄 README file not found\nPlease ensure README.md exists in the project root."
    else:
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()

    # Build the tab layout
    with gr.Blocks() as readme_tab:
        gr.Markdown("## 📘 Project Documentation — ClusterBlade")
        gr.Markdown(readme_content, elem_classes=["readme-content"])

    return readme_tab
