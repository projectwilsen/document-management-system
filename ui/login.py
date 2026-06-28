import webbrowser
import customtkinter as ctk
import tkinter.messagebox as mb
from core.api_client import ApiClient


class LoginWindow(ctk.CTkToplevel):
    def __init__(self, api: ApiClient, on_success: callable):
        super().__init__()
        self.title("Login — Rename Faktur Pajak")
        self.geometry("400x300")
        self.resizable(False, False)
        self.grab_set()  # modal

        self._api = api
        self._on_success = on_success
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Rename Faktur Pajak Coretax", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, pady=(24, 16)
        )

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, padx=32, sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Email", anchor="w").grid(row=0, column=0, sticky="w")
        self._email = ctk.CTkEntry(form, placeholder_text="email@company.com")
        self._email.grid(row=1, column=0, sticky="ew", pady=(2, 10))

        ctk.CTkLabel(form, text="Password", anchor="w").grid(row=2, column=0, sticky="w")
        self._password = ctk.CTkEntry(form, show="*", placeholder_text="••••••••")
        self._password.grid(row=3, column=0, sticky="ew", pady=(2, 16))

        self._login_btn = ctk.CTkButton(form, text="Login", command=self._do_login)
        self._login_btn.grid(row=4, column=0, sticky="ew")

        link_frame = ctk.CTkFrame(self, fg_color="transparent")
        link_frame.grid(row=2, column=0, pady=(12, 0))
        ctk.CTkButton(link_frame, text="Don't have an account?", fg_color="transparent",
                      text_color=("blue", "lightblue"), hover=False,
                      command=lambda: webbrowser.open("http://localhost:3000/register")).pack(side="left")
        ctk.CTkButton(link_frame, text="Forgot password?", fg_color="transparent",
                      text_color=("blue", "lightblue"), hover=False,
                      command=lambda: webbrowser.open("http://localhost:3000/forgot-password")).pack(side="left")

    def _do_login(self):
        email = self._email.get().strip()
        password = self._password.get()
        if not email or not password:
            mb.showerror("Error", "Email and password are required.", parent=self)
            return
        self._login_btn.configure(state="disabled", text="Logging in...")
        try:
            self._api.login(email, password)
            self.destroy()
            self._on_success()
        except Exception as e:
            mb.showerror("Login Failed", str(e), parent=self)
            self._login_btn.configure(state="normal", text="Login")
