"""Windows desktop interface for the ESA E4407B trace exporter."""

import logging
import os
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from esa_export import DEFAULT_ADDRESS, check_connection, export_trace, output_path


BACKGROUND = "#edf2f7"
SURFACE = "#ffffff"
INK = "#172b42"
MUTED = "#455b72"
NAVY = "#122943"
BLUE = "#1260a8"
GREEN = "#166247"
RED = "#a32732"
AMBER = "#8a540e"
BORDER = "#ccd7e3"


class ExportApp:
    def __init__(self, root):
        self.root = root
        root.title("ESA DataSave · E4407B 迹线导出")
        root.configure(background=BACKGROUND)
        root.geometry("780x610")
        root.minsize(720, 610)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.events = Queue()
        self.busy = False
        self.controls = []
        self.address = tk.StringVar(value=DEFAULT_ADDRESS)
        documents = Path.home() / "Documents"
        self.directory = tk.StringVar(value=str(documents if documents.is_dir() else Path.home()))
        self.filename = tk.StringVar(value=f"trace_{datetime.now():%Y%m%d_%H%M%S}")
        self.device = tk.StringVar(value="尚未测试连接")
        self.stage = tk.StringVar(value="就绪")
        self.detail = tk.StringVar(value="在仪器面板设定扫描参数，然后导出当前 TRACE1。")
        self.last_folder = None
        self.address.trace_add("write", lambda *_: self.device.set("尚未测试连接"))

        self.configure_styles()
        self.build()
        root.after(75, self.poll_events)

    def configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Microsoft YaHei UI", 10), foreground=INK)
        style.configure("TButton", padding=(14, 8), background="#edf3fa", bordercolor=BORDER)
        style.map("TButton", background=[("active", "#dce9f6")])
        style.configure("Primary.TButton", background=BLUE, foreground="white", bordercolor=BLUE)
        style.map(
            "Primary.TButton",
            background=[("disabled", "#dbe4ed"), ("pressed", "#12477a"), ("active", "#1a70bd")],
            foreground=[("disabled", MUTED)],
        )
        style.configure("TEntry", padding=(9, 7), fieldbackground=SURFACE, bordercolor=BORDER)
        style.map("TEntry", bordercolor=[("focus", BLUE)], fieldbackground=[("disabled", BACKGROUND)])
        style.configure("Horizontal.TProgressbar", background=BLUE, troughcolor="#e3ebf3", bordercolor=BORDER)
        style.configure("Success.Horizontal.TProgressbar", background=GREEN)

    def build(self):
        header = tk.Frame(self.root, background=NAVY, padx=24, pady=17)
        header.pack(fill="x")
        tk.Label(
            header, text="ESA DataSave", background=NAVY, foreground="white",
            font=("Segoe UI Semibold", 23),
        ).pack(anchor="w")
        tk.Label(
            header, text="E4407B 频谱仪  /  迹线导出", background=NAVY,
            foreground="#bfd2e8", font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(self.root, background=BACKGROUND, padx=22, pady=13)
        body.pack(fill="both", expand=True)
        actions = tk.Frame(body, background=BACKGROUND)
        actions.pack(side="bottom", fill="x", pady=(0, 2))

        connection = self.card(body, "01   仪器连接")
        self.field(connection, 1, "VISA 地址", self.address, "测试连接", self.test_connection)
        self.label(connection, textvariable=self.device, color=MUTED).grid(
            row=2, column=1, columnspan=2, sticky="w", pady=(5, 0),
        )

        output = self.card(body, "02   保存设置")
        self.field(output, 1, "保存目录", self.directory, "浏览…", self.browse)
        self.field(output, 2, "文件名", self.filename)
        self.label(output, text=".csv", color=MUTED).grid(row=2, column=2, sticky="w", padx=(8, 0))

        status = self.card(body, "03   导出状态")
        self.status_label = self.label(status, textvariable=self.stage, bold=True)
        self.status_label.grid(row=1, column=0, columnspan=3, sticky="w")
        detail = self.label(status, textvariable=self.detail, color=MUTED, wraplength=630)
        detail.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(3, 5))
        status.bind("<Configure>", lambda event: detail.configure(wraplength=max(200, event.width - 32)))
        self.progress = ttk.Progressbar(status, mode="determinate", value=0)
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew")

        self.folder_button = ttk.Button(actions, text="打开保存目录", command=self.open_folder)
        self.folder_button.pack(side="left")
        self.folder_button.state(["disabled"])
        export_button = ttk.Button(
            actions, text="导出 TRACE1", command=self.start_export, style="Primary.TButton",
        )
        export_button.pack(side="right")
        self.controls.append(export_button)

    def card(self, parent, title):
        card = tk.Frame(
            parent, background=SURFACE, padx=15, pady=9,
            highlightbackground=BORDER, highlightthickness=1,
        )
        card.pack(fill="x", pady=(0, 10))
        card.columnconfigure(1, weight=1)
        self.label(card, text=title, bold=True).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        return card

    def label(self, parent, *, color=INK, bold=False, **options):
        return tk.Label(
            parent, background=SURFACE, foreground=color, anchor="w", justify="left",
            font=("Microsoft YaHei UI", 10, "bold" if bold else "normal"), **options,
        )

    def field(self, card, row, title, variable, button_text=None, command=None):
        self.label(card, text=title).grid(row=row, column=0, sticky="w", padx=(0, 12))
        entry = ttk.Entry(card, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        self.controls.append(entry)
        if button_text:
            button = ttk.Button(card, text=button_text, command=command)
            button.grid(row=row, column=2, sticky="ew", padx=(8, 0))
            self.controls.append(button)

    def browse(self):
        chosen = filedialog.askdirectory(parent=self.root, initialdir=self.directory.get())
        if chosen:
            self.directory.set(chosen)

    def open_folder(self):
        try:
            os.startfile(self.last_folder)
        except OSError as error:
            messagebox.showerror("无法打开目录", str(error), parent=self.root)

    def close(self):
        if self.busy:
            self.root.bell()
        else:
            self.root.destroy()

    def start(self, title, operation):
        if self.busy:
            return
        self.busy = True
        for widget in self.controls:
            widget.state(["disabled"])
        self.stage.set(title)
        self.detail.set("正在连接仪器…")
        self.status_label.configure(foreground=BLUE)
        self.progress.configure(mode="indeterminate", style="Horizontal.TProgressbar", value=0)
        self.progress.start(12)

        def worker():
            try:
                stage, detail, identity, folder = operation()
                self.events.put(("done", stage, detail, identity, folder))
            except Exception as error:
                logging.exception("%s失败", title)
                self.events.put(("done", "操作失败", str(error), None, None))

        Thread(target=worker, daemon=True).start()

    def poll_events(self):
        try:
            while True:
                kind, *values = self.events.get_nowait()
                if kind == "connection_failed":
                    self.device.set("连接测试失败")
                    continue
                if kind == "progress":
                    self.detail.set(values[0])
                    continue
                stage, detail, identity, folder = values
                self.busy = False
                self.progress.stop()
                failed = stage == "操作失败"
                has_warning = stage == "已保存，有清理提示"
                color = RED if failed else AMBER if has_warning else GREEN
                self.status_label.configure(foreground=color)
                self.progress.configure(
                    mode="determinate",
                    style="Horizontal.TProgressbar" if failed else "Success.Horizontal.TProgressbar",
                    value=0 if failed else 100,
                )
                for widget in self.controls:
                    widget.state(["!disabled"])
                self.stage.set(stage)
                self.detail.set(detail)
                if identity:
                    self.device.set(f"上次测试通过：{identity}")
                if folder:
                    self.last_folder = folder
                    self.folder_button.state(["!disabled"])
                if failed:
                    messagebox.showerror(stage, detail, parent=self.root)
                elif has_warning:
                    messagebox.showwarning(stage, detail, parent=self.root)
        except Empty:
            pass
        self.root.after(75, self.poll_events)

    def selected_address(self):
        address = self.address.get().strip()
        if not address:
            messagebox.showwarning("缺少 VISA 地址", "请先输入仪器的 VISA 资源地址。", parent=self.root)
        return address

    def test_connection(self):
        address = self.selected_address()
        if not address:
            return
        self.device.set("正在测试连接…")

        def operation():
            try:
                identity = check_connection(address)
            except Exception:
                self.events.put(("connection_failed",))
                raise
            return "连接测试通过", "E4407B 已响应，可开始导出。", identity, None

        self.start("测试连接", operation)

    def start_export(self):
        address = self.selected_address()
        if not address:
            return
        try:
            target = output_path(self.directory.get().strip(), self.filename.get())
            if target.exists():
                raise FileExistsError(f"{target.name} 已存在，请更换文件名。")
        except (ValueError, OSError) as error:
            messagebox.showwarning("请检查保存设置", str(error), parent=self.root)
            return

        def operation():
            warning = export_trace(address, target, lambda text: self.events.put(("progress", text)))
            if warning:
                return "已保存，有清理提示", f"{target}\n{warning}", None, target.parent
            return "导出完成", f"{target}\n仪器端临时文件已清理。", None, target.parent

        self.start("导出 TRACE1", operation)


def main():
    root = tk.Tk()
    ExportApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
