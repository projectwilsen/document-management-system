import queue
import threading
import tkinter.messagebox as mb
from tkinter import filedialog

import customtkinter as ctk

from core.rename_faktur import rename_faktur


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rename Faktur Pajak Coretax")
        self.geometry("720x520")
        self.minsize(600, 420)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._log_queue: queue.Queue = queue.Queue()
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Title
        ctk.CTkLabel(
            self,
            text="Rename Faktur Pajak Coretax",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Folder pickers
        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_frame, text="Folder Sumber", width=110, anchor="w").grid(
            row=0, column=0, padx=(12, 4), pady=10
        )
        self._source_entry = ctk.CTkEntry(folder_frame)
        self._source_entry.configure(state="disabled")
        self._source_entry.grid(row=0, column=1, padx=4, pady=10, sticky="ew")
        ctk.CTkButton(folder_frame, text="Browse", width=80, command=self._browse_source).grid(
            row=0, column=2, padx=(4, 12), pady=10
        )

        ctk.CTkLabel(folder_frame, text="Folder Tujuan", width=110, anchor="w").grid(
            row=1, column=0, padx=(12, 4), pady=(0, 10)
        )
        self._output_entry = ctk.CTkEntry(folder_frame)
        self._output_entry.configure(state="disabled")
        self._output_entry.grid(row=1, column=1, padx=4, pady=(0, 10), sticky="ew")
        ctk.CTkButton(folder_frame, text="Browse", width=80, command=self._browse_output).grid(
            row=1, column=2, padx=(4, 12), pady=(0, 10)
        )

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=20, pady=6, sticky="e")

        self._preview_btn = ctk.CTkButton(
            btn_frame, text="Preview", width=110, fg_color="gray50",
            hover_color="gray40", command=self._run_preview
        )
        self._preview_btn.grid(row=0, column=0, padx=(0, 8))

        self._sync_btn = ctk.CTkButton(
            btn_frame, text="Sync", width=110, command=self._run_sync
        )
        self._sync_btn.grid(row=0, column=1)

        # Log panel
        self._log_box = ctk.CTkTextbox(
            self,
            state="disabled",
            font=ctk.CTkFont(family="Courier New", size=12),
            wrap="none",
        )
        self._log_box.grid(row=3, column=0, padx=20, pady=6, sticky="nsew")

        # Summary bar
        self._summary_label = ctk.CTkLabel(self, text="", anchor="w")
        self._summary_label.grid(row=4, column=0, padx=20, pady=(2, 16), sticky="w")

    # --- folder pickers ---

    def _browse_source(self):
        path = filedialog.askdirectory(title="Pilih Folder Sumber")
        if path:
            self._set_entry(self._source_entry, path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="Pilih Folder Tujuan")
        if path:
            self._set_entry(self._output_entry, path)

    def _set_entry(self, entry: ctk.CTkEntry, value: str):
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)
        entry.configure(state="disabled")

    # --- actions ---

    def _run_preview(self):
        self._start_process(preview=True)

    def _run_sync(self):
        self._start_process(preview=False)

    def _start_process(self, preview: bool):
        source = self._source_entry.get()
        output = self._output_entry.get()

        if not source:
            mb.showerror("Error", "Pilih folder sumber terlebih dahulu.")
            return
        if not output:
            mb.showerror("Error", "Pilih folder tujuan terlebih dahulu.")
            return

        self._clear_log()
        self._set_buttons(enabled=False)
        mode = "PREVIEW (tidak ada file yang dipindah)" if preview else "SYNC (file akan dipindah)"
        self._append_log(f"Mode : {mode}")
        self._append_log("-" * 70)

        def worker():
            result = rename_faktur(
                folder=source,
                output_folder=output,
                preview=preview,
                log_callback=lambda msg: self._log_queue.put(("log", msg)),
            )
            self._log_queue.put(("done", result))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_queue()

    # --- UI helpers ---

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        self._summary_label.configure(text="")

    def _append_log(self, text: str):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", text + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _set_buttons(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self._preview_btn.configure(state=state)
        self._sync_btn.configure(state=state)

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self._log_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "done":
                    r = payload
                    self._summary_label.configure(
                        text=f"✅ Berhasil: {r['berhasil']}    ❌ Gagal: {r['gagal']}    ⏭  Dilewati: {r['skip']}"
                    )
                    self._set_buttons(enabled=True)
                    return
        except Exception:
            pass
        self.after(100, self._poll_queue)
