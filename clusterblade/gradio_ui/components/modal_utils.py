import gradio as gr

class ModalManager:
    """
    A reusable modal utility for Gradio apps.
    Handles opening, closing, and dynamic title/message updates.
    """

    def __init__(self):
        # 🔹 Internal state (shared across uses)
        self.confirm_state = gr.State(False)

        # 🔹 Build modal UI
        with gr.Group(visible=False, elem_id="modal-overlay") as self.modal:
            gr.HTML("""
                <style>
                #modal-overlay {
                    position: fixed;
                    top: 0; left: 0;
                    width: 100%; height: 100%;
                    background: rgba(0, 0, 0, 0.6);
                    display: flex; justify-content: center; align-items: center;
                    z-index: 9999;
                }
                .modal-content {
                    background: #1e1e1e;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
                    width: 350px;
                }
                </style>
            """)
            with gr.Column(elem_classes=["modal-content"]):
                self.modal_title = gr.Markdown("### Confirm Action")
                self.modal_message = gr.Markdown("Are you sure you want to continue?")
                with gr.Row():
                    self.confirm_btn = gr.Button("✅ Confirm", variant="primary")
                    self.cancel_btn = gr.Button("❌ Cancel", variant="secondary")

    # ===============================
    # 🧩 CONTROL METHODS
    # ===============================
    def open_modal(self, title: str, message: str):
        """Returns UI updates to open modal with dynamic content."""
        return (
            gr.update(visible=True),
            gr.update(value=f"### {title}"),
            gr.update(value=message),
            False,  # Reset confirm_state
        )

    def close_modal(self, confirmed: bool = False):
        """Returns UI updates to close modal."""
        return (
            gr.update(visible=False),
            gr.update(),
            gr.update(),
            confirmed,
        )

    def confirm_and_close(self):
        """Closes the modal immediately and sets confirm_state=True."""
        return (
            gr.update(visible=False),
            gr.update(),
            gr.update(),
            True,
        )
    # ===============================
    # 🔗 LINKAGE
    # ===============================
    def bind_buttons(self):
        """Connects confirm/cancel buttons to close the modal."""
        self.confirm_btn.click(
            lambda: self.close_modal(True),
            outputs=[self.modal, self.modal_title, self.modal_message, self.confirm_state],
        )

        self.cancel_btn.click(
            lambda: self.close_modal(False),
            outputs=[self.modal, self.modal_title, self.modal_message, self.confirm_state],
        )

        self.confirm_btn.click(
            lambda: self.confirm_and_close(),
            outputs=[self.modal, self.modal_title, self.modal_message, self.confirm_state],
         )   
