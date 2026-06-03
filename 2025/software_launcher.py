# -*- coding: utf-8 -*-
"""Small desktop launcher for the PV forecasting Streamlit console."""

from __future__ import annotations

import queue
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Button, Frame, Label, StringVar, Text, Tk, messagebox


ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
HEALTH_CHECK = ROOT / "tools" / "project_health_check.py"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def python_executable() -> str:
    executable = Path(sys.executable)
    if executable.name.lower() == "pythonw.exe":
        python = executable.with_name("python.exe")
        if python.exists():
            return str(python)
    return str(executable)


def find_free_port(start: int = 8501, limit: int = 40) -> int:
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("没有找到可用端口，请关闭占用 8501 附近端口的程序后重试。")


def streamlit_installed() -> bool:
    completed = subprocess.run(
        [python_executable(), "-c", "import streamlit"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=NO_WINDOW,
        check=False,
    )
    return completed.returncode == 0


def wait_until_ready(port: int, timeout_seconds: int = 35) -> bool:
    deadline = time.time() + timeout_seconds
    urls = [
        f"http://127.0.0.1:{port}/_stcore/health",
        f"http://127.0.0.1:{port}",
    ]
    while time.time() < deadline:
        for url in urls:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if 200 <= response.status < 500:
                        return True
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
        time.sleep(0.5)
    return False


class SoftwareLauncher:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("光伏日前预测软件启动器")
        self.root.geometry("760x520")
        self.root.minsize(680, 460)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.status = StringVar(value="未启动")
        self.process: subprocess.Popen[str] | None = None
        self.port: int | None = None
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()

        self.build_ui()
        self.root.after(120, self.flush_events)

    def build_ui(self) -> None:
        header = Frame(self.root, padx=18, pady=16)
        header.pack(fill=X)
        Label(
            header,
            text="光伏电站发电功率日前预测项目",
            font=("Microsoft YaHei UI", 18, "bold"),
            anchor="w",
        ).pack(fill=X)
        Label(
            header,
            text="桌面启动器负责在后台启动 Streamlit 控制台、打开浏览器、运行健康检查和停止服务。",
            font=("Microsoft YaHei UI", 10),
            anchor="w",
        ).pack(fill=X, pady=(6, 0))

        status_bar = Frame(self.root, padx=18)
        status_bar.pack(fill=X)
        Label(status_bar, text="状态：", font=("Microsoft YaHei UI", 10, "bold")).pack(side=LEFT)
        Label(status_bar, textvariable=self.status, anchor="w").pack(side=LEFT, fill=X, expand=True)

        buttons = Frame(self.root, padx=18, pady=14)
        buttons.pack(fill=X)
        Button(buttons, text="启动/打开软件", command=self.start_dashboard, width=16).pack(side=LEFT, padx=(0, 8))
        Button(buttons, text="打开浏览器界面", command=self.open_dashboard, width=16).pack(side=LEFT, padx=(0, 8))
        Button(buttons, text="运行健康检查", command=self.run_health_check, width=16).pack(side=LEFT, padx=(0, 8))
        Button(buttons, text="停止后台服务", command=self.stop_server, width=16).pack(side=LEFT, padx=(0, 8))
        Button(buttons, text="退出", command=self.close, width=10).pack(side=RIGHT)

        log_frame = Frame(self.root, padx=18)
        log_frame.pack(fill=BOTH, expand=True, pady=(0, 18))
        Label(log_frame, text="运行日志", font=("Microsoft YaHei UI", 10, "bold"), anchor="w").pack(fill=X)
        self.log = Text(log_frame, height=18, wrap="word")
        self.log.pack(fill=BOTH, expand=True, pady=(6, 0))
        self.write_log("建议演示时双击 start_software.vbs；需要看详细命令行输出时再运行 run.bat。")

    def write_log(self, text: str) -> None:
        self.log.insert(END, text.rstrip() + "\n")
        self.log.see(END)

    def post(self, kind: str, text: str) -> None:
        self.events.put((kind, text))

    def flush_events(self) -> None:
        while True:
            try:
                kind, text = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "status":
                self.status.set(text)
            else:
                self.write_log(text)
        self.root.after(120, self.flush_events)

    def start_dashboard(self) -> None:
        if self.process and self.process.poll() is None:
            self.open_dashboard()
            return
        if not streamlit_installed():
            self.status.set("缺少 Streamlit")
            self.write_log("未检测到 Streamlit。请先运行：python -m pip install -r requirements.txt")
            messagebox.showerror("依赖缺失", "未检测到 Streamlit，请先通过 run.bat 或 pip 安装 requirements.txt。")
            return

        try:
            self.port = find_free_port()
        except RuntimeError as exc:
            self.status.set("启动失败")
            self.write_log(str(exc))
            messagebox.showerror("端口不可用", str(exc))
            return

        command = [
            python_executable(),
            "-m",
            "streamlit",
            "run",
            str(APP),
            "--server.headless",
            "true",
            "--server.port",
            str(self.port),
            "--browser.gatherUsageStats",
            "false",
        ]
        self.write_log("启动后台服务：" + " ".join(command))
        self.status.set(f"正在启动 127.0.0.1:{self.port}")
        self.process = subprocess.Popen(
            command,
            cwd=ROOT.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=NO_WINDOW,
        )
        threading.Thread(target=self.collect_output, daemon=True).start()
        threading.Thread(target=self.wait_and_open, args=(self.port,), daemon=True).start()

    def collect_output(self) -> None:
        process = self.process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            self.post("log", line.rstrip())
        returncode = process.poll()
        self.post("status", f"后台服务已退出 returncode={returncode}")

    def wait_and_open(self, port: int) -> None:
        if wait_until_ready(port):
            url = f"http://127.0.0.1:{port}"
            self.post("status", f"已启动：{url}")
            self.post("log", "软件控制台已启动：" + url)
            webbrowser.open(url)
        else:
            self.post("status", "启动超时")
            self.post("log", "等待 Streamlit 就绪超时，请查看上方日志或改用 run.bat 调试。")

    def open_dashboard(self) -> None:
        if self.port and self.process and self.process.poll() is None:
            webbrowser.open(f"http://127.0.0.1:{self.port}")
            self.status.set(f"已打开：127.0.0.1:{self.port}")
        else:
            self.start_dashboard()

    def run_health_check(self) -> None:
        threading.Thread(target=self._run_health_check, daemon=True).start()

    def _run_health_check(self) -> None:
        self.post("status", "正在运行健康检查")
        command = [python_executable(), str(HEALTH_CHECK)]
        self.post("log", "运行：" + " ".join(command))
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT.parent,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
                creationflags=NO_WINDOW,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.post("status", "健康检查超时")
            self.post("log", "健康检查超过 120 秒。")
            return
        self.post("log", completed.stdout)
        if completed.returncode == 0:
            self.post("status", "健康检查通过")
        else:
            self.post("status", f"健康检查失败 returncode={completed.returncode}")

    def stop_server(self) -> None:
        if not self.process or self.process.poll() is not None:
            self.status.set("没有正在运行的后台服务")
            return
        self.write_log("正在停止后台服务。")
        self.process.terminate()
        try:
            self.process.wait(timeout=6)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=6)
        self.status.set("后台服务已停止")

    def close(self) -> None:
        if self.process and self.process.poll() is None:
            choice = messagebox.askyesnocancel("退出启动器", "是否同时停止后台 Streamlit 服务？")
            if choice is None:
                return
            if choice:
                self.stop_server()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    try:
        SoftwareLauncher().run()
    except Exception as exc:  # pragma: no cover - last-resort desktop diagnostics
        log_path = ROOT / "launcher_error.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        try:
            messagebox.showerror(
                "启动器启动失败",
                f"{exc}\n\n详细错误已写入：{log_path}",
            )
        except Exception:
            pass
        raise
