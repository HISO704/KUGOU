import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime

APP_NAME = "酷狗音乐转换器"
SUPPORTED = {".kgm", ".kgma", ".kgg", ".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma"}

class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("980x700")
        self.root.minsize(820, 600)
        self.root.configure(bg="#f4f6fa")

        self.files = []
        self.events = queue.Queue()
        self.busy = False
        self.total = 0
        self.success = 0
        self.failed = 0

        self._setup_style()
        self._build_ui()
        self.root.after(100, self._poll_events)
        self._log("程序已启动。添加文件后点击“开始转换”。")
        self._log("提示：KGM/KGMA/KGG 可能是专有加密格式，本版本会提示不支持，不会伪造 MP3。")

    def _setup_style(self):
        style = ttk.Style()
        try:
            if "vista" in style.theme_names():
                style.theme_use("vista")
            else:
                style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=(10, 7), font=("Microsoft YaHei UI", 9))
        style.configure("Accent.TButton", padding=(14, 8), font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Treeview", rowheight=28, font=("Microsoft YaHei UI", 9))
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("TLabel", font=("Microsoft YaHei UI", 9))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 20, "bold"), foreground="#172033")
        style.configure("Sub.TLabel", font=("Microsoft YaHei UI", 9), foreground="#667085")
        style.configure("Status.TLabel", font=("Microsoft YaHei UI", 9), foreground="#344054")

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 14))
        title_area = ttk.Frame(header)
        title_area.pack(side="left", fill="x", expand=True)
        ttk.Label(title_area, text="酷狗音乐转换器", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_area, text="批量管理 · 转换进度 · 输出目录 · 运行日志", style="Sub.TLabel").pack(anchor="w", pady=(3, 0))
        self.status_pill = tk.Label(header, text="● 就绪", bg="#e7f7ed", fg="#16794b",
                                    font=("Microsoft YaHei UI", 9, "bold"), padx=12, pady=6)
        self.status_pill.pack(side="right", anchor="n")

        toolbar = ttk.Frame(main)
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Button(toolbar, text="＋ 添加文件", command=self.add_files).pack(side="left")
        ttk.Button(toolbar, text="▣ 添加文件夹", command=self.add_folder).pack(side="left", padx=(7, 0))
        ttk.Button(toolbar, text="移除选中", command=self.remove_selected).pack(side="left", padx=(7, 0))
        ttk.Button(toolbar, text="清空列表", command=self.clear_files).pack(side="left", padx=(7, 0))
        ttk.Button(toolbar, text="打开输出目录", command=self.open_output).pack(side="right")

        list_card = ttk.LabelFrame(main, text=" 文件列表 ", padding=10)
        list_card.pack(fill="both", expand=True)

        columns = ("name", "format", "size", "state")
        self.tree = ttk.Treeview(list_card, columns=columns, show="headings", selectmode="extended")
        self.tree.heading("name", text="文件名称 / 路径")
        self.tree.heading("format", text="格式")
        self.tree.heading("size", text="大小")
        self.tree.heading("state", text="状态")
        self.tree.column("name", width=560, anchor="w")
        self.tree.column("format", width=90, anchor="center")
        self.tree.column("size", width=100, anchor="e")
        self.tree.column("state", width=130, anchor="center")
        vsb = ttk.Scrollbar(list_card, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(list_card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        list_card.columnconfigure(0, weight=1)
        list_card.rowconfigure(0, weight=1)

        output_card = ttk.LabelFrame(main, text=" 输出设置 ", padding=10)
        output_card.pack(fill="x", pady=(12, 0))
        ttk.Label(output_card, text="保存到：").grid(row=0, column=0, sticky="w")
        self.out_var = tk.StringVar(value=str(Path.home() / "Music" / "MP3输出"))
        ttk.Entry(output_card, textvariable=self.out_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(output_card, text="浏览…", command=self.choose_output).grid(row=0, column=2)
        output_card.columnconfigure(1, weight=1)
        ttk.Label(output_card, text="MP3 音质：").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.quality_var = tk.StringVar(value="高音质（约 190 kbps VBR）")
        self.quality_combo = ttk.Combobox(
            output_card, textvariable=self.quality_var, state="readonly",
            values=("最高音质（约 245 kbps VBR）", "高音质（约 190 kbps VBR）", "标准音质（约 130 kbps VBR）"),
            width=30
        )
        self.quality_combo.grid(row=1, column=1, sticky="w", padx=8, pady=(8, 0))

        progress_card = ttk.LabelFrame(main, text=" 转换进度 ", padding=10)
        progress_card.pack(fill="x", pady=(12, 0))
        progress_top = ttk.Frame(progress_card)
        progress_top.pack(fill="x")
        self.progress_text = tk.StringVar(value="等待开始")
        self.count_text = tk.StringVar(value="0 / 0")
        ttk.Label(progress_top, textvariable=self.progress_text, style="Status.TLabel").pack(side="left")
        ttk.Label(progress_top, textvariable=self.count_text).pack(side="right")
        self.progress = ttk.Progressbar(progress_card, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(8, 6))
        stats = ttk.Frame(progress_card)
        stats.pack(fill="x")
        self.success_text = tk.StringVar(value="成功 0")
        self.failed_text = tk.StringVar(value="失败 0")
        ttk.Label(stats, textvariable=self.success_text, foreground="#16794b").pack(side="left")
        ttk.Label(stats, textvariable=self.failed_text, foreground="#b42318").pack(side="left", padx=18)
        self.start_btn = ttk.Button(stats, text="▶ 开始转换", style="Accent.TButton", command=self.start_conversion)
        self.start_btn.pack(side="right")

        log_card = ttk.LabelFrame(main, text=" 转换日志 ", padding=8)
        log_card.pack(fill="both", expand=False, pady=(12, 0))
        log_toolbar = ttk.Frame(log_card)
        log_toolbar.pack(fill="x", pady=(0, 5))
        ttk.Label(log_toolbar, text="记录每个文件的处理结果和错误原因", style="Sub.TLabel").pack(side="left")
        ttk.Button(log_toolbar, text="清空日志", command=self.clear_log).pack(side="right")
        log_frame = ttk.Frame(log_card)
        log_frame.pack(fill="both", expand=True)
        self.log_box = tk.Text(log_frame, height=7, wrap="word", font=("Consolas", 9),
                               bg="#101828", fg="#d0d5dd", insertbackground="white",
                               relief="flat", padx=10, pady=8, state="disabled")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=log_scroll.set)
        self.log_box.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        footer = ttk.Frame(main)
        footer.pack(fill="x", pady=(9, 0))
        ttk.Label(footer, text="支持普通音频转 MP3；KGM/KGMA/KGG 需另有合法兼容解码方案。", style="Sub.TLabel").pack(side="left")
        ttk.Button(footer, text="格式说明", command=self.show_help).pack(side="right")

    def _fmt_size(self, size):
        if size < 1024:
            return f"{size} B"
        if size < 1024**2:
            return f"{size/1024:.1f} KB"
        if size < 1024**3:
            return f"{size/1024**2:.1f} MB"
        return f"{size/1024**3:.2f} GB"

    def _row_status(self, path, status):
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            if values and values[0] == path:
                self.tree.set(item, "state", status)
                break

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="选择音乐文件",
            filetypes=[("音乐文件", "*.kgm *.kgma *.kgg *.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma"),
                       ("所有文件", "*.*")]
        )
        self._add_paths(paths)

    def add_folder(self):
        folder = filedialog.askdirectory(title="选择音乐文件夹")
        if not folder:
            return
        paths = [str(p) for p in Path(folder).rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED]
        self._add_paths(paths)

    def _add_paths(self, paths):
        known = set(self.files)
        added = 0
        for raw in paths:
            p = str(Path(raw))
            if p in known:
                continue
            try:
                size = Path(p).stat().st_size
            except OSError:
                size = 0
            self.files.append(p)
            self.tree.insert("", "end", values=(p, Path(p).suffix.lower().lstrip(".").upper(), self._fmt_size(size), "等待处理"))
            known.add(p)
            added += 1
        self._log(f"添加文件：新增 {added} 个，当前共 {len(self.files)} 个。")
        self.status_pill.configure(text="● 已添加文件", bg="#eaf2ff", fg="#175cd3")

    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        removed = []
        for iid in selected:
            path = self.tree.item(iid, "values")[0]
            removed.append(path)
            self.tree.delete(iid)
        self.files = [p for p in self.files if p not in set(removed)]
        self._log(f"从列表移除 {len(removed)} 个文件。")

    def clear_files(self):
        if self.busy:
            messagebox.showwarning("正在处理", "转换期间不能清空文件列表。")
            return
        self.files.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.progress["value"] = 0
        self.progress_text.set("等待开始")
        self.count_text.set("0 / 0")
        self.success_text.set("成功 0")
        self.failed_text.set("失败 0")
        self._log("文件列表已清空。")

    def choose_output(self):
        folder = filedialog.askdirectory(title="选择 MP3 输出目录")
        if folder:
            self.out_var.set(folder)
            self._log(f"输出目录已设置为：{folder}")

    def open_output(self):
        folder = Path(self.out_var.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))
        except Exception as exc:
            messagebox.showerror("无法打开目录", str(exc))

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self._log("日志已清空。")

    def _log(self, text):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{stamp}] {text}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def find_ffmpeg(self):
        # Prefer bundled FFmpeg beside the app, then PyInstaller's extracted bundle,
        # then the system PATH. FFmpeg is distributed as a separate executable.
        candidates = []
        if getattr(__import__("sys"), "frozen", False):
            app_dir = Path(__import__("sys").executable).resolve().parent
            candidates.append(app_dir / "ffmpeg" / "bin" / "ffmpeg.exe")
            candidates.append(app_dir / "ffmpeg.exe")
            bundle_dir = getattr(__import__("sys"), "_MEIPASS", None)
            if bundle_dir:
                candidates.append(Path(bundle_dir) / "ffmpeg" / "bin" / "ffmpeg.exe")
                candidates.append(Path(bundle_dir) / "ffmpeg.exe")
        else:
            project_dir = Path(__file__).resolve().parents[1]
            candidates.append(project_dir / "ffmpeg" / "bin" / "ffmpeg.exe")
            candidates.append(project_dir / "ffmpeg.exe")
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return shutil.which("ffmpeg")

    def _unique_target(self, output, stem):
        """Return a new output path without overwriting any existing file."""
        candidate = output / f"{stem}.mp3"
        if not candidate.exists():
            return candidate
        number = 1
        while True:
            candidate = output / f"{stem}_converted_{number}.mp3"
            if not candidate.exists():
                return candidate
            number += 1

    def show_help(self):
        messagebox.showinfo(
            "格式兼容性与第三方许可",
            "普通音频（MP3/WAV/FLAC/M4A/AAC/OGG/OPUS/WMA）：通过 FFmpeg 转换。\n\n"
            "KGM/KGMA/KGG：可能是酷狗专有加密格式，FFmpeg 通常不能直接解码。"
            "此版本会标记为“当前不支持”，不会伪造 MP3。需要在获得授权并确认兼容后，"
            "再集成合法的解码组件。\n\n"
            "构建 EXE：在 Windows 上安装 Python，然后双击 build.bat。\\n\\n"
            "第三方组件：本软件可调用 FFmpeg。FFmpeg 的具体许可取决于所用构建及启用的外部库；"
            "分发时请随包附上对应许可文本、来源与构建信息，并确认所用构建允许再分发。"
        )

    def start_conversion(self):
        if self.busy:
            return
        if not self.files:
            messagebox.showwarning("没有文件", "请先添加音乐文件。")
            return
        output = Path(self.out_var.get()).expanduser()
        try:
            output.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("输出目录不可用", str(exc))
            return

        ffmpeg = self.find_ffmpeg()
        self.busy = True
        self.total = len(self.files)
        self.success = 0
        self.failed = 0
        self.progress["value"] = 0
        self.progress_text.set("准备转换…")
        self.count_text.set(f"0 / {self.total}")
        self.success_text.set("成功 0")
        self.failed_text.set("失败 0")
        self.start_btn.configure(state="disabled")
        self.status_pill.configure(text="● 正在转换", bg="#fff4e5", fg="#b54708")
        for p in self.files:
            self._row_status(p, "处理中")
        self._log(f"开始任务：{self.total} 个文件；输出目录：{output}")
        quality = self.quality_var.get()
        qvalue = {
            "最高音质（约 245 kbps VBR）": "0",
            "高音质（约 190 kbps VBR）": "2",
            "标准音质（约 130 kbps VBR）": "4",
        }.get(quality, "2")
        threading.Thread(target=self._worker, args=(list(self.files), output, ffmpeg, qvalue), daemon=True).start()

    def _worker(self, files, output, ffmpeg, qvalue):
        success = 0
        failed = 0
        total = len(files)
        for idx, raw in enumerate(files, start=1):
            src = Path(raw)
            suffix = src.suffix.lower()
            self.events.put(("current", idx, total, src.name))
            if suffix in {".kgm", ".kgma", ".kgg"}:
                failed += 1
                self.events.put(("result", raw, "当前不支持", f"未转换：{src.name} — 酷狗专有格式；当前版本没有合法兼容的解码器。"))
            elif not ffmpeg:
                failed += 1
                self.events.put(("result", raw, "失败", f"失败：{src.name} — 未找到 FFmpeg。请安装并将 ffmpeg.exe 加入 PATH。"))
            else:
                target = self._unique_target(output, src.stem)
                if target.resolve() == src.resolve():
                    target = self._unique_target(output, f"{src.stem}_converted")
                cmd = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                       "-i", str(src), "-map", "0:a:0", "-vn", "-codec:a", "libmp3lame", "-q:a", qvalue, str(target)]
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
                    if proc.returncode == 0 and target.exists() and target.stat().st_size > 0:
                        success += 1
                        self.events.put(("result", raw, "成功", f"成功：{src.name} → {target.name}"))
                    else:
                        failed += 1
                        lines = (proc.stderr or "FFmpeg 未返回详细错误").strip().splitlines()
                        self.events.put(("result", raw, "失败", f"失败：{src.name} — {lines[-1][:260] if lines else '未知错误'}"))
                        if target.exists() and target.stat().st_size == 0:
                            target.unlink(missing_ok=True)
                except Exception as exc:
                    failed += 1
                    self.events.put(("result", raw, "失败", f"失败：{src.name} — {exc}"))
            self.events.put(("progress", idx, total, success, failed))
        self.events.put(("done", success, failed, total))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "current":
                    _, idx, total, name = event
                    self.progress_text.set(f"正在处理：{name}")
                elif kind == "result":
                    _, path, state, logline = event
                    self._row_status(path, state)
                    self._log(logline)
                elif kind == "progress":
                    _, idx, total, success, failed = event
                    self.progress["value"] = int(idx * 100 / total)
                    self.count_text.set(f"{idx} / {total}")
                    self.success_text.set(f"成功 {success}")
                    self.failed_text.set(f"失败 {failed}")
                elif kind == "done":
                    _, success, failed, total = event
                    self.busy = False
                    self.start_btn.configure(state="normal")
                    self.progress_text.set("任务完成")
                    self.status_pill.configure(text="● 已完成", bg="#e7f7ed", fg="#16794b")
                    self._log(f"任务结束：总计 {total}，成功 {success}，失败/不支持 {failed}。")
                    messagebox.showinfo("转换完成", f"总计：{total}\n成功：{success}\n失败或当前不支持：{failed}")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)


def main():
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.1)
    except tk.TclError:
        pass
    ConverterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
