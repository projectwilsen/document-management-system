import webbrowser
import customtkinter as ctk


class StatusBar(ctk.CTkFrame):
    def __init__(self, parent, dashboard_url: str = "http://localhost:3000"):
        super().__init__(parent, fg_color=("gray90", "gray20"), height=36)
        self._dashboard_url = dashboard_url
        self.grid_columnconfigure(0, weight=1)

        self._label = ctk.CTkLabel(self, text="Loading plan info...", anchor="w",
                                    font=ctk.CTkFont(size=12))
        self._label.grid(row=0, column=0, padx=12, sticky="w")

        self._upgrade_btn = ctk.CTkButton(
            self, text="Upgrade →", width=90, height=24,
            font=ctk.CTkFont(size=12),
            command=lambda: webbrowser.open(f"{self._dashboard_url}/billing"),
        )
        self._upgrade_btn.grid(row=0, column=1, padx=8)
        self._upgrade_btn.grid_remove()

    def update_quota(self, plan: str, used: int, limit: int | None):
        if limit is None:
            text = f"\U0001f4e6 {plan.capitalize()} Plan  •  {used} docs used (unlimited)"
            self._upgrade_btn.grid_remove()
        else:
            remaining = max(0, limit - used)
            text = f"\U0001f4e6 {plan.capitalize()} Plan  •  {used} / {limit} docs used"
            if remaining == 0:
                text += "  ⚠️ Limit reached"
                self._upgrade_btn.grid()
            else:
                self._upgrade_btn.grid_remove()
        self._label.configure(text=text)

    def set_error(self, msg: str):
        self._label.configure(text=f"⚠️ {msg}")
