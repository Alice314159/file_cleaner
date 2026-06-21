import queue
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from config.manager import (
    load_config,
    normalize_max_depth,
    normalize_pattern_list,
    normalize_target,
    save_config,
)
from config.settings import COLORS, CONFIG_FILE, DANGEROUS_FOLDER_PATTERNS
from core.deleter import delete_item
from core.matcher import should_exclude
from services.import_export import read_rules, write_rules
from services.path_history import save_recent_path
from ui.left_panel import target_risk
from ui.widgets import FlatButton, Tooltip
from utils.formatters import fmt_modified, fmt_size
from utils.logger import LOG_FILE, LOGGER
from workers.scan_worker import ScanWorker


# ─── Main App ─────────────────────────────────────────────────────────────────



class FileCleanerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        LOGGER.info("app start config=%s log=%s", CONFIG_FILE, LOG_FILE)
        self.config_data = load_config()
        self.scan_results = []
        self.result_vars  = []   # BooleanVar per result row
        self._scan_thread = None
        self._scan_queue = None
        self._scan_stop_event = None
        self._scan_poll_job = None
        self._scan_cancelling = False
        self._scan_worker = None
        self.sort_column = "size"
        self.sort_reverse = True
        self._ignore_tree_select = False

        self.title("File Cleaner")
        self.geometry("1050x740")
        self.minsize(860, 600)
        self.configure(bg=COLORS["bg"])

        # macOS window style
        if sys.platform == "darwin":
            try:
                self.tk.call("::tk::unsupported::MacWindowStyle", "style", self._w, "document", "closeBox collapseBox resizeBox")
            except Exception:
                pass

        self._build_styles()
        self._build_ui()
        self._refresh_path_dropdown()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Styles ──────────────────────────────────────────────────────────────

    def _build_styles(self):
        s = ttk.Style(self)
        s.theme_use("default")

        s.configure("TFrame",       background=COLORS["bg"])
        s.configure("Card.TFrame",  background=COLORS["card"])
        s.configure("Panel.TFrame", background=COLORS["panel"])

        s.configure("TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=("Helvetica", 11))

        s.configure("Dim.TLabel",
            background=COLORS["card"],
            foreground=COLORS["text_dim"],
            font=("Helvetica", 10))

        s.configure("Title.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["text"],
            font=("Helvetica", 18, "bold"))

        s.configure("Tag.TLabel",
            font=("Helvetica", 9, "bold"),
            padding=(4, 1))

        s.configure("TCombobox",
            fieldbackground=COLORS["card"],
            background=COLORS["card"],
            foreground=COLORS["text"],
            selectbackground=COLORS["highlight"],
            selectforeground=COLORS["text"],
            arrowcolor=COLORS["accent"],
            borderwidth=0,
            padding=(8, 6))

        s.map("TCombobox",
            fieldbackground=[("readonly", COLORS["card"])],
            foreground=[("readonly", COLORS["text"])])

        s.configure("TCheckbutton",
            background=COLORS["card"],
            foreground=COLORS["text"],
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["accent"],
            font=("Helvetica", 11))

        s.configure("TScrollbar",
            background=COLORS["panel"],
            troughcolor=COLORS["bg"],
            arrowcolor=COLORS["text_dim"],
            borderwidth=0)

        s.configure("Treeview",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            fieldbackground=COLORS["surface"],
            rowheight=28,
            borderwidth=0,
            font=("Menlo", 10))
        s.configure("Treeview.Heading",
            background=COLORS["surface"],
            foreground=COLORS["text_dim"],
            borderwidth=0,
            padding=(8, 6),
            font=("Helvetica", 9, "bold"))
        s.map("Treeview",
            background=[("selected", COLORS["highlight"])],
            foreground=[("selected", COLORS["text"])])

    # ── UI Layout ────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Body: fixed 280px sidebar + flexible main area.
        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=0, pady=0)

        left = tk.Frame(body, bg=COLORS["panel"], width=280)
        left.pack_propagate(False)
        left.pack(side="left", fill="y")

        divider = tk.Frame(body, bg=COLORS["border"], width=1)
        divider.pack(side="left", fill="y")

        right = tk.Frame(body, bg=COLORS["bg"])
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

        # Status bar
        self.status_var = tk.StringVar(value="Ready - select a path and click Scan")
        sbar = tk.Frame(self, bg=COLORS["panel"], height=30)
        sbar.pack(fill="x", side="bottom")
        tk.Label(sbar, textvariable=self.status_var,
                 bg=COLORS["panel"], fg=COLORS["text_dim"],
                 font=("Helvetica", 11), anchor="w", padx=14).pack(fill="x", pady=4)

    def _build_left(self, parent):
        hdr = tk.Frame(parent, bg=COLORS["panel"], pady=14, padx=16)
        hdr.pack(fill="x")

        mark = tk.Label(hdr, text="FC", bg=COLORS["accent"], fg="white",
                        font=("Helvetica", 12, "bold"), padx=9, pady=5)
        mark.pack(side="left")

        title_wrap = tk.Frame(hdr, bg=COLORS["panel"])
        title_wrap.pack(side="left", padx=(12, 0))
        tk.Label(title_wrap, text="File Cleaner", bg=COLORS["panel"],
                 fg=COLORS["text"], font=("Helvetica", 18, "bold")).pack(anchor="w")
        tk.Label(title_wrap, text="Recursive project cleanup tool",
                 bg=COLORS["panel"], fg=COLORS["text_muted"],
                 font=("Helvetica", 10)).pack(anchor="w", pady=(1, 0))

        top_sep = tk.Frame(parent, bg=COLORS["border"], height=1)
        top_sep.pack(fill="x")

        # Action buttons
        btn_row = tk.Frame(parent, bg=COLORS["panel"])
        btn_row.pack(fill="x", padx=12, pady=(16, 0))

        self.scan_btn = self._btn(btn_row, "Scan", self._on_scan_button,
                                   bg=COLORS["accent"], fg="white")
        self.scan_btn.pack(fill="x", pady=(0, 8))

        self.delete_btn = self._btn(btn_row, "Move Selected to Trash", self._delete_selected,
                                     bg=COLORS["panel"], fg=COLORS["danger"],
                                     hover_bg=COLORS["danger_soft"],
                                     border_bg=COLORS["danger"], border_width=1)
        self.delete_btn.pack(fill="x")
        self.delete_btn.config(state="disabled")

        sep = tk.Frame(parent, bg=COLORS["border"], height=1)
        sep.pack(fill="x", padx=12, pady=14)

        tab_bar = tk.Frame(parent, bg=COLORS["panel"])
        tab_bar.pack(fill="x", padx=12, pady=(0, 10))
        self.left_tab_buttons = {}
        self.clean_tab_btn = self._btn(
            tab_bar,
            "Clean Targets",
            lambda: self._show_left_tab("clean"),
            bg=COLORS["accent"],
            fg="white",
            padx=10,
        )
        self.clean_tab_btn.pack(side="left", fill="x", expand=True)
        self.exclude_tab_btn = self._btn(
            tab_bar,
            "Exclude Targets",
            lambda: self._show_left_tab("exclude"),
            bg=COLORS["card"],
            fg=COLORS["text"],
            padx=10,
        )
        self.exclude_tab_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.left_tab_buttons["clean"] = self.clean_tab_btn
        self.left_tab_buttons["exclude"] = self.exclude_tab_btn

        self.left_pages = tk.Frame(parent, bg=COLORS["panel"])
        self.left_pages.pack(fill="both", expand=True)
        self.left_pages.grid_rowconfigure(0, weight=1)
        self.left_pages.grid_columnconfigure(0, weight=1)
        self.clean_targets_page = tk.Frame(self.left_pages, bg=COLORS["panel"])
        self.exclude_targets_page = tk.Frame(self.left_pages, bg=COLORS["panel"])
        self.clean_targets_page.grid(row=0, column=0, sticky="nsew")
        self.exclude_targets_page.grid(row=0, column=0, sticky="nsew")
        self._active_left_tab = None

        # Clean targets page
        targets_head = tk.Frame(self.clean_targets_page, bg=COLORS["panel"])
        targets_head.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(targets_head, text="CLEAN TARGETS", bg=COLORS["panel"],
                 fg=COLORS["text_muted"], font=("Helvetica", 10, "bold")).pack(side="left")
        self.targets_count_var = tk.StringVar(value=self._target_count_text())
        add_target_btn = self._btn(targets_head, "+ Add", self._open_add_target_dialog,
                                   bg=COLORS["success"], fg="white", padx=9)
        add_target_btn.pack(side="right", padx=(8, 0))
        tk.Label(targets_head, textvariable=self.targets_count_var, bg=COLORS["panel"],
                 fg=COLORS["text_muted"], font=("Helvetica", 10)).pack(side="right", padx=(0, 8))

        target_tools = tk.Frame(self.clean_targets_page, bg=COLORS["panel"])
        target_tools.pack(fill="x", padx=12, pady=(0, 8))

        self.target_filter_var = tk.StringVar()
        self.target_filter_var.trace_add("write", lambda *_: self._build_targets_list())
        target_filter = tk.Entry(target_tools, textvariable=self.target_filter_var,
                                 bg=COLORS["card"], fg=COLORS["text"],
                                 insertbackground=COLORS["text"],
                                 relief="flat", font=("Helvetica", 10),
                                 highlightthickness=1,
                                 highlightbackground=COLORS["border"],
                                 highlightcolor=COLORS["accent"])
        target_filter.pack(side="left", fill="x", expand=True, ipady=5)

        # Scrollable targets list
        targets_list_wrap = tk.Frame(self.clean_targets_page, bg=COLORS["panel"],
                                     highlightthickness=1,
                                     highlightbackground=COLORS["border_soft"])
        targets_list_wrap.pack(fill="both", expand=True)
        self.targets_canvas = tk.Canvas(targets_list_wrap, bg=COLORS["panel"], highlightthickness=0)
        self.targets_scrollbar = self._scrollbar(targets_list_wrap, self.targets_canvas.yview)
        self.targets_frame = tk.Frame(self.targets_canvas, bg=COLORS["panel"])

        self.targets_frame.bind("<Configure>",
            lambda e: self.targets_canvas.configure(scrollregion=self.targets_canvas.bbox("all")))
        self.targets_canvas_window = self.targets_canvas.create_window((0, 0), window=self.targets_frame, anchor="nw")
        self.targets_canvas.bind("<Configure>",
            lambda e: self.targets_canvas.itemconfigure(self.targets_canvas_window, width=e.width))
        self.targets_canvas.configure(yscrollcommand=self.targets_scrollbar.set)

        self.targets_canvas.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.targets_scrollbar.pack(side="right", fill="y")
        self._bind_canvas_scroll(self.targets_canvas, self.targets_frame)

        self._build_targets_list()

        # Exclude targets page
        settings_frame = tk.Frame(self.exclude_targets_page, bg=COLORS["panel"])
        settings_frame.pack(fill="both", expand=True, padx=12, pady=(0, 14))

        exclude_head = tk.Frame(settings_frame, bg=COLORS["panel"])
        exclude_head.pack(fill="x", pady=(4, 4))
        tk.Label(exclude_head, text="EXCLUDE PATHS", bg=COLORS["panel"],
                 fg=COLORS["text_muted"], font=("Helvetica", 9, "bold")).pack(side="left")
        self.exclude_count_var = tk.StringVar()
        tk.Label(exclude_head, textvariable=self.exclude_count_var,
                 bg=COLORS["panel"], fg=COLORS["text_muted"],
                 font=("Helvetica", 9)).pack(side="right")

        self.exclude_input_var = tk.StringVar()
        exclude_row = tk.Frame(settings_frame, bg=COLORS["panel"])
        exclude_row.pack(fill="x")
        exclude_entry = tk.Entry(exclude_row, textvariable=self.exclude_input_var,
                                 bg=COLORS["card"], fg=COLORS["text_dim"],
                                 insertbackground=COLORS["text"],
                                 relief="flat", font=("Helvetica", 10),
                                 highlightthickness=1,
                                 highlightbackground=COLORS["border"],
                                 highlightcolor=COLORS["accent"])
        exclude_entry.pack(side="left", fill="x", expand=True, ipady=5)
        exclude_entry.bind("<Return>", lambda _e: self._add_exclude_pattern())
        add_exclude_btn = self._btn(exclude_row, "+ Add", self._add_exclude_pattern,
                                    bg=COLORS["card"], fg=COLORS["text"], padx=8, width=6)
        add_exclude_btn.pack(side="left", padx=(6, 0))
        exclude_pick_row = tk.Frame(settings_frame, bg=COLORS["panel"])
        exclude_pick_row.pack(fill="x", pady=(6, 0))
        add_exclude_file_btn = self._btn(exclude_pick_row, "+ File", self._add_exclude_file,
                                         bg=COLORS["card"], fg=COLORS["text"], padx=8)
        add_exclude_file_btn.pack(side="left", fill="x", expand=True)
        add_exclude_path_btn = self._btn(exclude_pick_row, "+ Path", self._add_exclude_path,
                                         bg=COLORS["card"], fg=COLORS["text"], padx=8)
        add_exclude_path_btn.pack(side="left", fill="x", expand=True, padx=(6, 0))
        tk.Label(settings_frame, text="Comma-separated names, globs, or paths to skip during scan and delete. Defaults include Python virtual env folders.",
                 bg=COLORS["panel"], fg=COLORS["text_muted"],
                 font=("Helvetica", 9), wraplength=300, justify="left").pack(anchor="w", pady=(4, 0))

        exclude_list_wrap = tk.Frame(settings_frame, bg=COLORS["panel"],
                                     highlightthickness=1,
                                     highlightbackground=COLORS["border_soft"])
        exclude_list_wrap.pack(fill="both", expand=True, pady=(6, 0))
        self.exclude_canvas = tk.Canvas(exclude_list_wrap, bg=COLORS["panel"], highlightthickness=0)
        exclude_scrollbar = self._scrollbar(exclude_list_wrap, self.exclude_canvas.yview)
        self.exclude_list_frame = tk.Frame(self.exclude_canvas, bg=COLORS["panel"])
        self.exclude_list_frame.bind(
            "<Configure>",
            lambda _e: self.exclude_canvas.configure(scrollregion=self.exclude_canvas.bbox("all")),
        )
        self.exclude_canvas_window = self.exclude_canvas.create_window(
            (0, 0), window=self.exclude_list_frame, anchor="nw"
        )
        self.exclude_canvas.bind(
            "<Configure>",
            lambda e: self.exclude_canvas.itemconfigure(self.exclude_canvas_window, width=e.width),
        )
        self.exclude_canvas.configure(yscrollcommand=exclude_scrollbar.set)
        self.exclude_canvas.pack(side="left", fill="both", expand=True)
        exclude_scrollbar.pack(side="right", fill="y")
        self._bind_canvas_scroll(self.exclude_canvas, self.exclude_list_frame)
        self._refresh_exclude_list()

        depth_row = tk.Frame(settings_frame, bg=COLORS["panel"])
        depth_row.pack(fill="x", pady=(8, 0))
        tk.Label(depth_row, text="Max depth", bg=COLORS["panel"],
                 fg=COLORS["text_muted"], font=("Helvetica", 10)).pack(side="left")
        self.max_depth_var = tk.StringVar(value=str(self.config_data.get("max_depth", "")))
        depth_entry = tk.Entry(depth_row, textvariable=self.max_depth_var,
                               bg=COLORS["card"], fg=COLORS["text_dim"],
                               insertbackground=COLORS["text"],
                               relief="flat", font=("Helvetica", 10),
                               width=7,
                               highlightthickness=1,
                               highlightbackground=COLORS["border"],
                               highlightcolor=COLORS["accent"])
        depth_entry.pack(side="right", ipady=5)
        depth_entry.bind("<FocusOut>", lambda _e: self._save_scan_options())
        depth_entry.bind("<Return>", lambda _e: self._save_scan_options())

        config_row = tk.Frame(settings_frame, bg=COLORS["panel"])
        config_row.pack(fill="x", pady=(10, 0))
        import_btn = self._btn(config_row, "Import", self._import_rules,
                               bg=COLORS["card"], fg=COLORS["text"], padx=10)
        import_btn.pack(side="left")
        export_btn = self._btn(config_row, "Export", self._export_rules,
                               bg=COLORS["card"], fg=COLORS["text"], padx=10)
        export_btn.pack(side="left", padx=(8, 0))
        self._show_left_tab("clean")

    def _show_left_tab(self, tab_name: str):
        if not hasattr(self, "clean_targets_page"):
            return
        if tab_name == self._active_left_tab:
            return

        if tab_name == "exclude":
            self.exclude_targets_page.tkraise()
            active = "exclude"
        else:
            self.clean_targets_page.tkraise()
            active = "clean"

        self._active_left_tab = active
        for name, button in getattr(self, "left_tab_buttons", {}).items():
            if name == active:
                button.config(
                    bg=COLORS["accent"],
                    fg="white",
                    hover_bg=COLORS["accent_hover"],
                )
            else:
                button.config(
                    bg=COLORS["card"],
                    fg=COLORS["text"],
                    hover_bg=COLORS["card_hover"],
                )

    def _build_targets_list(self):
        for w in self.targets_frame.winfo_children():
            w.destroy()
        if hasattr(self, "targets_canvas"):
            self.targets_canvas.yview_moveto(0)

        if hasattr(self, "targets_count_var"):
            self.targets_count_var.set(self._target_count_text())

        self.target_check_vars = []
        query = ""
        if hasattr(self, "target_filter_var"):
            query = self.target_filter_var.get().strip().lower()

        visible = [
            (i, t) for i, t in enumerate(self.config_data["targets"])
            if not query
            or query in t["pattern"].lower()
            or query in t["type"].lower()
            or query in t.get("match_mode", "exact").lower()
            or query in ("builtin" if t.get("builtin") else "custom")
            or query in target_risk(t)[0].lower()
        ]

        if not visible:
            tk.Label(self.targets_frame, text="No matching targets",
                     bg=COLORS["panel"], fg=COLORS["text_muted"],
                     font=("Helvetica", 10)).pack(fill="x", pady=10)
            self._refresh_canvas_scroll(self.targets_canvas, self.targets_frame)
            return

        grouped = [
            ("FOLDERS", [(i, t) for i, t in visible if t["type"] == "folder"]),
            ("FILE EXTENSIONS", [(i, t) for i, t in visible if t["type"] == "ext"]),
            ("FILES", [(i, t) for i, t in visible if t["type"] == "file"]),
        ]

        for title, items in grouped:
            if not items:
                continue
            tk.Label(
                self.targets_frame,
                text=f"{title}  {len(items)}",
                bg=COLORS["panel"],
                fg=COLORS["text_muted"],
                font=("Helvetica", 8, "bold"),
                anchor="w",
            ).pack(fill="x", padx=(2, 0), pady=(8, 3))
            for i, t in items:
                self._build_target_row(i, t)

        self._refresh_canvas_scroll(self.targets_canvas, self.targets_frame)

    def _build_target_row(self, i, t):
        var = tk.BooleanVar(value=t["enabled"])
        self.target_check_vars.append(var)
        enabled = bool(t["enabled"])
        row_bg = COLORS["card"] if enabled else COLORS["panel"]
        fg = COLORS["text"] if enabled else COLORS["disabled_text"]
        muted_fg = COLORS["text_muted"] if enabled else COLORS["disabled_text"]
        border = COLORS["border_soft"] if enabled else COLORS["panel"]

        row = tk.Frame(self.targets_frame, bg=row_bg, highlightthickness=1,
                       highlightbackground=border)
        row.pack(fill="x", pady=2)

        cb = tk.Checkbutton(row, variable=var,
                             bg=row_bg,
                             activebackground=row_bg,
                             selectcolor=COLORS["accent"],
                             relief="flat", bd=0,
                             command=lambda i=i, v=var: self._toggle_target(i, v))
        cb.pack(side="left", padx=(4, 2), pady=4)

        tag_lbl = tk.Label(row, text=t["type"],
                            bg=row_bg, fg=COLORS["folder_tag"] if enabled else COLORS["disabled_text"],
                            font=("Helvetica", 8, "bold"),
                            padx=5, pady=1, width=6,
                            highlightthickness=1,
                            highlightbackground=COLORS["folder_tag"] if enabled else COLORS["border"])
        tag_lbl.pack(side="left", padx=(0, 6))

        risk_text, risk_bg = target_risk(t)
        risk_lbl = tk.Label(row, text=risk_text,
                            bg=risk_bg if enabled else COLORS["border_soft"],
                            fg=COLORS["text"] if enabled else COLORS["disabled_text"],
                            font=("Helvetica", 8, "bold"),
                            padx=5, pady=1, width=4)
        risk_lbl.pack(side="left", padx=(0, 6))

        tk.Label(row, text=t["pattern"],
                 bg=row_bg, fg=fg,
                 font=("Helvetica", 10), anchor="w").pack(side="left", fill="x", expand=True)

        mode = t.get("match_mode", "exact")
        if mode != "exact":
            tk.Label(row, text=mode,
                     bg=row_bg, fg=muted_fg,
                     font=("Helvetica", 8), padx=4).pack(side="left", padx=(4, 0))

        if t.get("builtin"):
            del_btn = tk.Label(row, text="lock", bg=row_bg,
                               fg=muted_fg, font=("Helvetica", 8))
            del_btn.pack(side="right", padx=(6, 7))
            return

        del_btn = tk.Label(row, text="x", bg=row_bg,
                           fg=muted_fg, font=("Helvetica", 10),
                           cursor="hand2")
        del_btn.pack(side="right", padx=(6, 7))
        del_btn.bind("<Button-1>", lambda e, i=i: self._remove_target(i))
        del_btn.bind("<Enter>", lambda e, w=del_btn: w.config(fg=COLORS["danger"]))
        del_btn.bind("<Leave>", lambda e, w=del_btn: w.config(fg=COLORS["text_muted"]))

    def _build_right(self, parent):
        # Toolbar
        toolbar = tk.Frame(parent, bg=COLORS["bg"], pady=10, padx=24)
        toolbar.pack(fill="x")

        summary = tk.Frame(toolbar, bg=COLORS["bg"])
        summary.pack(side="left", fill="x", expand=True)

        self.result_summary_var = tk.StringVar(value="No scan results yet")
        tk.Label(summary, textvariable=self.result_summary_var,
                 bg=COLORS["bg"], fg=COLORS["text_dim"],
                 font=("Helvetica", 11, "bold")).pack(side="left")

        self.selection_toggle_btn = self._btn(toolbar, "Select All", self._toggle_result_selection,
                                              bg=COLORS["card"], fg=COLORS["text"], padx=12, width=11)
        self.selection_toggle_btn.pack(side="right", padx=(8, 0))
        self.selection_toggle_btn.config(state="disabled")

        path_panel = tk.Frame(toolbar, bg=COLORS["bg"])
        path_panel.pack(side="right", fill="x", expand=True, padx=(12, 0))
        path_head = tk.Frame(path_panel, bg=COLORS["bg"])
        path_head.pack(fill="x")
        tk.Label(path_head, text="SCAN PATH", bg=COLORS["bg"],
                 fg=COLORS["text_muted"], font=("Helvetica", 8, "bold")).pack(side="left")

        path_row = tk.Frame(path_panel, bg=COLORS["bg"])
        path_row.pack(fill="x", pady=(4, 0))
        self.path_var = tk.StringVar()
        self.path_var.trace_add("write", lambda *_: self._sync_path_display())
        self.path_combo = ttk.Combobox(path_row, textvariable=self.path_var,
                                        font=("Helvetica", 10), state="normal")
        self.path_combo.pack(side="left", fill="x", expand=True)
        browse_btn = self._btn(path_row, "Browse", self._browse_path,
                               bg=COLORS["card"], fg=COLORS["text"], padx=10)
        browse_btn.pack(side="left", padx=(8, 0))

        self.path_display_var = tk.StringVar(value="No folder selected")
        self.path_display_label = tk.Label(
            path_panel,
            textvariable=self.path_display_var,
            bg=COLORS["bg"],
            fg=COLORS["text_dim"],
            font=("Menlo", 9),
            anchor="e",
        )
        self.path_display_label.pack(fill="x", pady=(3, 0))
        self.path_display_label.bind("<Enter>", self._show_path_tooltip)
        self.path_display_label.bind("<Leave>", lambda _e: self._hide_path_display_tooltip())
        self.path_display_tooltip = Tooltip(self.path_display_label)
        self._sync_path_display()

        # Results list
        list_frame = tk.Frame(parent, bg=COLORS["surface"], highlightthickness=1,
                              highlightbackground=COLORS["border"])
        list_frame.pack(fill="both", expand=True, padx=(0, 0), pady=(0, 0))

        cols = ("sel", "kind", "name", "path", "size", "modified")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings",
                                   selectmode="extended")

        self.tree.heading("sel",  text="",         anchor="center")
        self.tree.heading("kind", text="Type",     anchor="w",
                          command=lambda: self._sort_results("kind"))
        self.tree.heading("name", text="Name",     anchor="w",
                          command=lambda: self._sort_results("name"))
        self.tree.heading("path", text="Path",     anchor="w",
                          command=lambda: self._sort_results("path"))
        self.tree.heading("size", text="Size",     anchor="e",
                          command=lambda: self._sort_results("size"))
        self.tree.heading("modified", text="Modified", anchor="w",
                          command=lambda: self._sort_results("modified"))

        self.tree.column("sel",  width=68,  stretch=False, anchor="center")
        self.tree.column("kind", width=96,  stretch=False, anchor="w")
        self.tree.column("name", width=210, stretch=False, anchor="w")
        self.tree.column("path", width=360, stretch=True,  anchor="w")
        self.tree.column("size", width=86,  stretch=False, anchor="e")
        self.tree.column("modified", width=130, stretch=False, anchor="w")

        vsb = ttk.Scrollbar(list_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.empty_state = tk.Label(
            list_frame,
            text="📁\nChoose a scan path, then run Scan",
            bg=COLORS["surface"],
            fg=COLORS["text_muted"],
            font=("Helvetica", 15, "bold"),
            padx=20,
            pady=12,
        )
        self.empty_state.place(relx=0.5, rely=0.42, anchor="center")

        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Motion>", self._on_tree_motion)
        self.tree.bind("<Leave>", self._on_tree_leave)
        self._bind_widget_scroll(self.tree, self.tree)
        self.path_tooltip = Tooltip(self.tree)
        self._tooltip_row = None
        self._hover_row = None
        self.tree.tag_configure("folder", foreground=COLORS["warning"])
        self.tree.tag_configure("file",   foreground=COLORS["text"])
        self.tree.tag_configure("hover", background=COLORS["row_hover"])

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _btn(self, parent, text, cmd, bg=None, fg=None, padx=14, width=None,
             hover_bg=None, border_bg=None, border_width=0):
        bg = bg or COLORS["accent"]
        fg = fg or "white"
        return FlatButton(
            parent,
            text=text,
            command=cmd,
            bg=bg,
            fg=fg,
            hover_bg=hover_bg or self._lighten(bg),
            font=("Helvetica", 11, "bold"),
            padx=padx,
            pady=7,
            width=width,
            border_bg=border_bg,
            border_width=border_width,
        )

    def _scrollbar(self, parent, command):
        return tk.Scrollbar(
            parent,
            orient="vertical",
            command=command,
            width=12,
            bg=COLORS["card"],
            activebackground=COLORS["accent"],
            troughcolor=COLORS["panel"],
            relief="flat",
            bd=0,
            highlightthickness=0,
        )

    def _bind_canvas_scroll(self, canvas, *widgets):
        self._bind_widget_scroll(canvas, canvas)
        for widget in widgets:
            self._bind_widget_scroll(widget, canvas)

    def _bind_widget_scroll(self, widget, scroll_target):
        def _on_mousewheel(event):
            units = self._scroll_units(event)
            if units:
                scroll_target.yview_scroll(units, "units")
            return "break"

        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)
        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Shift-MouseWheel>", _on_mousewheel)

    def _scroll_units(self, event):
        if getattr(event, "num", None) == 4:
            return -1
        if getattr(event, "num", None) == 5:
            return 1

        delta = getattr(event, "delta", 0)
        if not delta:
            return 0

        # Windows commonly reports +/-120. macOS often reports small deltas
        # such as +/-1, which int(delta / 120) would collapse to zero.
        if abs(delta) >= 120:
            return -int(delta / 120)
        return -1 if delta > 0 else 1

    def _refresh_canvas_scroll(self, canvas, content):
        def bind_descendants(widget):
            self._bind_canvas_scroll(canvas, widget)
            for child in widget.winfo_children():
                bind_descendants(child)

        bind_descendants(content)
        content.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _lighten(self, hex_color):
        mapping = {
            COLORS["accent"]:  COLORS["accent_hover"],
            COLORS["danger"]:  COLORS["danger_hover"],
            COLORS["success"]: COLORS["success_hover"],
            COLORS["card"]:    COLORS["card_hover"],
            COLORS["card_hover"]: COLORS["border"],
        }
        return mapping.get(hex_color, hex_color)

    def _refresh_path_dropdown(self):
        paths = self.config_data.get("recent_paths", [])
        self.path_combo["values"] = paths
        if paths:
            self.path_var.set(paths[0])
        else:
            self._sync_path_display()

    def _sync_path_display(self):
        if not hasattr(self, "path_display_var"):
            return

        path = self.path_var.get().strip()
        self.path_display_var.set(self._display_scan_path(path) if path else "No folder selected")

    def _resize_path_display(self, event):
        if hasattr(self, "path_display_label"):
            self.path_display_label.config(wraplength=max(140, event.width - 22))

    def _display_scan_path(self, path):
        path = str(path)
        max_chars = 96
        if len(path) <= max_chars:
            return path
        head = path[:38]
        tail = path[-(max_chars - len(head) - 3):]
        return f"{head}...{tail}"

    def _show_path_tooltip(self, event):
        path = self.path_var.get().strip()
        if not path or not hasattr(self, "path_display_tooltip"):
            return
        self.path_display_tooltip.show(path, event.x_root + 12, event.y_root + 16)

    def _hide_path_display_tooltip(self):
        if hasattr(self, "path_display_tooltip"):
            self.path_display_tooltip.hide()

    def _save_path(self, path: str):
        paths = save_recent_path(self.config_data, path)
        self.path_combo["values"] = paths
        save_config(self.config_data)

    # ── Event Handlers ───────────────────────────────────────────────────────

    def _browse_path(self):
        initial = self.path_var.get() or str(Path.home())
        folder = filedialog.askdirectory(initialdir=initial, title="Select folder to scan")
        if folder:
            self.path_var.set(folder)

    def _toggle_target(self, idx, var):
        self.config_data["targets"][idx]["enabled"] = var.get()
        if hasattr(self, "targets_count_var"):
            self.targets_count_var.set(self._target_count_text())
        save_config(self.config_data)

    def _set_all_targets(self, enabled: bool):
        for target in self.config_data["targets"]:
            target["enabled"] = enabled
        save_config(self.config_data)
        self._build_targets_list()

    def _target_count_text(self):
        enabled_targets = [t for t in self.config_data["targets"] if t["enabled"]]
        total = len(self.config_data["targets"])
        folder_count = sum(1 for t in enabled_targets if t["type"] == "folder")
        ext_count = sum(1 for t in enabled_targets if t["type"] == "ext")
        file_count = sum(1 for t in enabled_targets if t["type"] == "file")
        return f"{len(enabled_targets)}/{total} enabled · F{folder_count} E{ext_count} File{file_count}"

    def _save_scan_options(self):
        max_depth = normalize_max_depth(self.max_depth_var.get() if hasattr(self, "max_depth_var") else "")
        self.config_data["exclude_patterns"] = normalize_pattern_list(
            self.config_data.get("exclude_patterns", [])
        )
        self.config_data["exclude_defaults_applied"] = True
        self.config_data["max_depth"] = max_depth
        if hasattr(self, "max_depth_var"):
            self.max_depth_var.set(max_depth)
        save_config(self.config_data)
        self.status_var.set("Scan options saved")

    def _set_exclude_patterns(self, patterns, status="Exclude paths saved"):
        normalized = []
        seen = set()
        for pattern in normalize_pattern_list(patterns):
            key = pattern.replace("\\", "/")
            if key in seen:
                continue
            normalized.append(pattern)
            seen.add(key)

        self.config_data["exclude_patterns"] = normalized
        self.config_data["exclude_defaults_applied"] = True
        save_config(self.config_data)
        self._refresh_exclude_list()
        self.status_var.set(status)

    def _refresh_exclude_list(self):
        if not hasattr(self, "exclude_list_frame"):
            return

        for child in self.exclude_list_frame.winfo_children():
            child.destroy()

        patterns = normalize_pattern_list(self.config_data.get("exclude_patterns", []))
        if hasattr(self, "exclude_count_var"):
            self.exclude_count_var.set(f"{len(patterns)} item(s)")

        if not patterns:
            tk.Label(
                self.exclude_list_frame,
                text="No exclude paths",
                bg=COLORS["panel"],
                fg=COLORS["text_muted"],
                font=("Helvetica", 9),
            ).pack(anchor="w", pady=(2, 0))
            self._refresh_canvas_scroll(self.exclude_canvas, self.exclude_list_frame)
            return

        for idx, pattern in enumerate(patterns):
            row = tk.Frame(self.exclude_list_frame, bg=COLORS["card"], highlightthickness=1,
                           highlightbackground=COLORS["panel"])
            row.pack(fill="x", pady=2)

            tk.Label(
                row,
                text=pattern,
                bg=COLORS["card"],
                fg=COLORS["text_dim"],
                font=("Menlo", 9),
                anchor="w",
                justify="left",
                wraplength=245,
            ).pack(side="left", fill="x", expand=True, padx=(8, 4), pady=5)

            del_btn = tk.Label(row, text="x", bg=COLORS["card"],
                               fg=COLORS["text_muted"], font=("Helvetica", 10),
                               cursor="hand2")
            del_btn.pack(side="right", padx=(4, 8))
            del_btn.bind("<Button-1>", lambda _e, i=idx: self._remove_exclude_pattern(i))
            del_btn.bind("<Enter>", lambda e, w=del_btn: w.config(fg=COLORS["danger"]))
            del_btn.bind("<Leave>", lambda e, w=del_btn: w.config(fg=COLORS["text_muted"]))

        self._refresh_canvas_scroll(self.exclude_canvas, self.exclude_list_frame)

    def _add_exclude_pattern(self):
        raw = self.exclude_input_var.get().strip() if hasattr(self, "exclude_input_var") else ""
        patterns_to_add = normalize_pattern_list(raw)
        if not patterns_to_add:
            messagebox.showinfo("Empty Exclude Path", "Enter a path, name, or glob pattern to exclude.")
            return

        patterns = normalize_pattern_list(self.config_data.get("exclude_patterns", []))
        existing = {p.replace("\\", "/") for p in patterns}
        added = 0
        for pattern in patterns_to_add:
            key = pattern.replace("\\", "/")
            if key in existing:
                continue
            patterns.append(pattern)
            existing.add(key)
            added += 1

        self.exclude_input_var.set("")
        if added:
            self._set_exclude_patterns(patterns, f"Added {added} exclude path(s)")
        else:
            self.status_var.set("Exclude path already exists")

    def _append_exclude_pattern(self, pattern, status="Exclude target added"):
        pattern = str(pattern).strip()
        if not pattern:
            return

        patterns = normalize_pattern_list(self.config_data.get("exclude_patterns", []))
        normalized_pattern = pattern.replace("\\", "/")
        existing = {p.replace("\\", "/") for p in patterns}
        if normalized_pattern in existing:
            self.status_var.set("Exclude target already exists")
            return

        patterns.append(pattern)
        self._set_exclude_patterns(patterns, status)

    def _add_exclude_file(self):
        initial = self.path_var.get().strip() or str(Path.home())
        path = filedialog.askopenfilename(title="Select file to exclude", initialdir=initial)
        if path:
            self._append_exclude_pattern(path, "Exclude file added")

    def _add_exclude_path(self):
        initial = self.path_var.get().strip() or str(Path.home())
        folder = filedialog.askdirectory(initialdir=initial, title="Select path to exclude")
        if folder:
            self._append_exclude_pattern(folder, "Exclude path added")

    def _remove_exclude_pattern(self, idx):
        patterns = normalize_pattern_list(self.config_data.get("exclude_patterns", []))
        if idx < 0 or idx >= len(patterns):
            return
        removed = patterns.pop(idx)
        self._set_exclude_patterns(patterns, f"Removed exclude path: {removed}")

    def _export_rules(self):
        path = filedialog.asksaveasfilename(
            title="Export clean rules",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            write_rules(path, self.config_data)
            self.status_var.set(f"Exported clean rules to {path}")
        except Exception as exc:
            messagebox.showerror("Export Failed", str(exc))

    def _import_rules(self):
        path = filedialog.askopenfilename(
            title="Import clean rules",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            payload = read_rules(path)
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc))
            return

        targets = payload.get("targets", [])
        if not targets:
            messagebox.showerror("Import Failed", "No valid targets found in this file.")
            return

        self.config_data["targets"] = targets
        self.config_data["exclude_patterns"] = normalize_pattern_list(payload.get("exclude_patterns", []))
        self.config_data["exclude_defaults_applied"] = True
        self.config_data["max_depth"] = normalize_max_depth(payload.get("max_depth", ""))
        save_config(self.config_data)

        self._refresh_exclude_list()
        if hasattr(self, "max_depth_var"):
            self.max_depth_var.set(self.config_data.get("max_depth", ""))
        self._build_targets_list()
        self.status_var.set(f"Imported {len(targets)} clean targets")

    def _open_add_target_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add Clean Target")
        dialog.configure(bg=COLORS["panel"])
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        form = tk.Frame(dialog, bg=COLORS["panel"], padx=18, pady=16)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Type", bg=COLORS["panel"], fg=COLORS["text_muted"],
                 font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky="w")
        kind_var = tk.StringVar(value="folder")
        type_row = tk.Frame(form, bg=COLORS["panel"])
        type_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 12))
        for label, value in (("folder", "folder"), ("ext", "ext"), ("file", "file")):
            tk.Radiobutton(
                type_row,
                text=label,
                value=value,
                variable=kind_var,
                bg=COLORS["panel"],
                fg=COLORS["text"],
                selectcolor=COLORS["card"],
                activebackground=COLORS["panel"],
                activeforeground=COLORS["text"],
                font=("Helvetica", 10),
            ).pack(side="left", padx=(0, 12))

        tk.Label(form, text="Name / Pattern", bg=COLORS["panel"], fg=COLORS["text_muted"],
                 font=("Helvetica", 10, "bold")).grid(row=2, column=0, sticky="w")
        pattern_var = tk.StringVar()
        pattern_entry = tk.Entry(
            form,
            textvariable=pattern_var,
            bg=COLORS["card"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            relief="flat",
            font=("Helvetica", 11),
            width=34,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
        )
        pattern_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 12), ipady=6)

        tk.Label(form, text="Match mode", bg=COLORS["panel"], fg=COLORS["text_muted"],
                 font=("Helvetica", 10, "bold")).grid(row=4, column=0, sticky="w")
        mode_var = tk.StringVar(value="exact")
        mode_cb = ttk.Combobox(form, textvariable=mode_var,
                               values=["exact", "contains", "regex"],
                               width=14, state="readonly", font=("Helvetica", 10))
        mode_cb.grid(row=5, column=0, sticky="w", pady=(6, 12))

        enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            form,
            text="Enabled",
            variable=enabled_var,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            activebackground=COLORS["panel"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["card"],
            font=("Helvetica", 10),
        ).grid(row=5, column=1, sticky="e", pady=(6, 12))

        actions = tk.Frame(form, bg=COLORS["panel"])
        actions.grid(row=6, column=0, columnspan=2, sticky="e", pady=(4, 0))

        cancel_btn = self._btn(actions, "Cancel", dialog.destroy,
                               bg=COLORS["card"], fg=COLORS["text"], padx=12)
        cancel_btn.pack(side="left", padx=(0, 8))
        save_btn = self._btn(
            actions,
            "Add",
            lambda: self._create_target_from_dialog(
                dialog, kind_var.get(), pattern_var.get(), mode_var.get(), enabled_var.get()
            ),
            bg=COLORS["success"],
            fg="white",
            padx=14,
        )
        save_btn.pack(side="left")

        form.grid_columnconfigure(0, weight=1)
        pattern_entry.focus_set()
        dialog.bind("<Return>", lambda _e: self._create_target_from_dialog(
            dialog, kind_var.get(), pattern_var.get(), mode_var.get(), enabled_var.get()
        ))
        self._center_dialog(dialog)

    def _center_dialog(self, dialog):
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - dialog.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_height()) // 3)
        dialog.geometry(f"+{x}+{y}")

    def _create_target_from_dialog(self, dialog, kind, pattern, match_mode, enabled):
        target = self._build_custom_target(kind, pattern, match_mode, enabled)
        if not target:
            return

        self.config_data["targets"].append(target)
        save_config(self.config_data)
        self._build_targets_list()
        dialog.destroy()
        self.status_var.set(f"Added clean target {target['pattern']}")

    def _build_custom_target(self, kind, pattern, match_mode, enabled):
        pattern = pattern.strip()
        kind = str(kind).strip().lower()
        match_mode = str(match_mode).strip().lower()

        if kind == "ext" and match_mode != "regex":
            pattern = pattern.lstrip("*").strip()
            if pattern and not pattern.startswith("."):
                pattern = "." + pattern

        if kind == "folder":
            lowered = pattern.lower()
            if lowered in DANGEROUS_FOLDER_PATTERNS or "/" in pattern or "\\" in pattern or pattern.startswith("~"):
                messagebox.showwarning("Unsafe Target", "This folder target is too risky. Use a specific folder name.")
                return None

        if kind == "file" and ("/" in pattern or "\\" in pattern):
            messagebox.showerror("Invalid Target", "File targets must be a filename, not a path.")
            return None

        if match_mode == "regex":
            try:
                re.compile(pattern)
            except re.error as exc:
                messagebox.showerror("Invalid Regex", f"Pattern is not a valid regular expression:\n{exc}")
                return None

        target = normalize_target({
            "type": kind,
            "pattern": pattern,
            "enabled": enabled,
            "builtin": False,
            "match_mode": match_mode,
        })
        if not target:
            messagebox.showerror("Invalid Target", "Name / Pattern cannot be empty.")
            return None

        duplicate = any(
            t["type"] == target["type"]
            and t["pattern"] == target["pattern"]
            and t.get("match_mode", "exact") == target.get("match_mode", "exact")
            for t in self.config_data["targets"]
        )
        if duplicate:
            messagebox.showinfo("Duplicate Target", "This clean target already exists.")
            return None

        existing_ids = {t.get("id") for t in self.config_data["targets"]}
        base_id = target["id"]
        suffix = 2
        while target["id"] in existing_ids:
            target["id"] = f"{base_id}_{suffix}"
            suffix += 1
        return target

    def _remove_target(self, idx):
        if self.config_data["targets"][idx].get("builtin"):
            messagebox.showinfo("Built-in Target", "Built-in targets can be disabled, but not deleted.")
            return
        self.config_data["targets"].pop(idx)
        save_config(self.config_data)
        self._build_targets_list()

    # ── Scanning (thread-safe via queue.Queue) ──────────────────────────────
    #
    # The previous implementation called self.after(...) directly from the
    # background scan thread on every matched item / progress tick. Tkinter
    # is not thread-safe, and under a large tree (many node_modules /
    # __pycache__ folders) this flooded the main thread's event queue faster
    # than it could be drained, making the whole app appear to hang/"busy".
    #
    # Fix: the worker thread only ever pushes plain data onto a
    # queue.Queue(). The main thread polls that queue on a fixed timer via
    # self.after() and drains it in capped batches, so the UI thread always
    # stays responsive no matter how fast results come in.

    def _on_scan_button(self):
        if self._scan_thread is not None and self._scan_thread.is_alive():
            # Acts as a Cancel button while a scan is running.
            self._cancel_scan()
            return
        self._start_scan()

    def _start_scan(self):
        path = self.path_var.get().strip()
        if not path or not Path(path).is_dir():
            messagebox.showerror("Invalid Path", "Please select a valid directory.")
            return

        self._save_path(path)
        self._save_scan_options()
        self._clear_results()

        LOGGER.info("ui scan requested path=%s log_file=%s", path, LOG_FILE)
        self.scan_btn.config(state="normal", text="Cancel", bg=COLORS["danger"],
                             hover_bg=COLORS["danger_hover"])
        self.status_var.set(f"Scanning {path} ...")

        self._scan_cancelling = False
        self._scan_error = None
        self._scan_final_results = None

        targets_snapshot = [dict(t) for t in self.config_data["targets"]]
        excludes_snapshot = list(self.config_data.get("exclude_patterns", []))
        max_depth_snapshot = self.config_data.get("max_depth", "")
        self._scan_worker = ScanWorker(path, targets_snapshot, excludes_snapshot, max_depth_snapshot)
        self._scan_queue = self._scan_worker.queue
        self._scan_stop_event = self._scan_worker.stop_event
        self._scan_thread = self._scan_worker.thread
        self._scan_worker.start()

        if self._scan_poll_job is not None:
            self.after_cancel(self._scan_poll_job)
        self._scan_poll_job = self.after(30, self._poll_scan_queue)

    def _cancel_scan(self):
        LOGGER.info("ui scan cancel requested")
        if self._scan_stop_event is not None:
            self._scan_stop_event.set()
        self._scan_cancelling = True
        self._drop_pending_scan_messages()
        self.status_var.set("Cancelling scan...")
        self.scan_btn.config(state="disabled", text="Cancelling...")

    def _drop_pending_scan_messages(self):
        if self._scan_queue is None:
            return
        dropped = 0
        while True:
            try:
                self._scan_queue.get_nowait()
                dropped += 1
            except queue.Empty:
                break
        if dropped:
            LOGGER.info("ui dropped pending scan messages count=%s during cancel", dropped)

    def _poll_scan_queue(self):
        """Runs on the MAIN/UI thread only. Drains the queue in capped
        batches so a flood of matches never blocks the event loop for long."""
        if self._scan_queue is None:
            return

        MAX_PER_TICK = 1500 if self._scan_cancelling else 500
        processed = 0
        last_status = None
        finished_kind = None
        finished_payload = None
        result_batch = []

        while processed < MAX_PER_TICK:
            try:
                item = self._scan_queue.get_nowait()
            except queue.Empty:
                break

            processed += 1
            kind = item[0]
            if kind == "progress":
                _, scanned_dirs, matched, current_path = item
                last_status = (
                    f"Scanning... {scanned_dirs} folders visited, "
                    f"{matched} item(s) matched - {current_path}"
                )
            elif kind == "result":
                if not self._scan_cancelling:
                    result_batch.append(item[1])
            elif kind in ("done", "cancelled", "error"):
                finished_kind = kind
                finished_payload = item[1] if len(item) > 1 else None
                break

        if result_batch:
            self._append_scan_results(result_batch)
            self.status_var.set(f"Rendering scan results... {len(self.scan_results)} item(s)")

        if result_batch or finished_kind is not None or processed >= MAX_PER_TICK:
            try:
                remaining = self._scan_queue.qsize()
            except Exception:
                remaining = "unknown"
            LOGGER.info(
                "ui scan queue tick processed=%s result_batch=%s total_displayed=%s finished=%s remaining=%s",
                processed,
                len(result_batch),
                len(self.scan_results),
                finished_kind or "-",
                remaining,
            )

        if last_status:
            self.status_var.set(last_status)

        if finished_kind is not None:
            self._scan_poll_job = None
            if finished_kind == "error":
                LOGGER.error("ui scan worker error=%s", finished_payload)
                self._show_scan_error(finished_payload)
            elif finished_kind == "cancelled":
                LOGGER.info("ui scan worker cancelled partial_results=%s", len(finished_payload or []))
                self._show_scan_cancelled(finished_payload or [])
            else:
                LOGGER.info("ui scan worker done results=%s", len(finished_payload or []))
                self._show_results(finished_payload or [])
            return

        # Still scanning - schedule next poll tick.
        self._scan_poll_job = self.after(30, self._poll_scan_queue)

    def _reset_scan_button(self):
        self.scan_btn.config(state="normal", text="Scan", bg=COLORS["accent"],
                             hover_bg=COLORS["accent_hover"])

    def _show_results(self, results):
        try:
            total_size = sum(r["size"] for r in results)

            self._sync_streamed_results(results)
            self._update_result_summary()

            count = len(results)
            if count:
                self.empty_state.place_forget()
            else:
                self.empty_state.config(text="📁\nNo matching clean targets found")
                self.empty_state.place(relx=0.5, rely=0.42, anchor="center")

            self.delete_btn.config(state="normal" if results else "disabled")
            self._set_selection_toggle_enabled(bool(results))
            self.status_var.set(f"Scan complete - {count} item(s) found, {fmt_size(total_size)} total")
            LOGGER.info("ui scan complete results=%s bytes=%s", count, total_size)
        except Exception as exc:
            LOGGER.exception("ui scan result rendering failed")
            self._show_scan_error(f"{exc.__class__.__name__}: {exc}", show_dialog=False)
        finally:
            self._finish_scan_ui()

    def _show_scan_cancelled(self, partial_results):
        self._sync_streamed_results(partial_results)
        self._update_result_summary()

        has_results = bool(self.scan_results)
        if has_results:
            self.empty_state.place_forget()
        else:
            self.empty_state.config(text="📁\nScan cancelled")
            self.empty_state.place(relx=0.5, rely=0.42, anchor="center")

        self.delete_btn.config(state="normal" if has_results else "disabled")
        self._set_selection_toggle_enabled(has_results)
        self.status_var.set(f"Scan cancelled - {len(partial_results)} item(s) found before stopping")
        LOGGER.info("ui scan cancelled partial_results=%s", len(partial_results))
        self._finish_scan_ui()

    def _sync_streamed_results(self, results):
        current_paths = {r.get("path") for r in self.scan_results}
        missing = [r for r in results if r.get("path") not in current_paths]
        if missing:
            self._append_scan_results(missing)

        if len(self.scan_results) != len(results):
            self.scan_results = list(results)
            self.result_vars = [tk.BooleanVar(value=True) for _ in self.scan_results]
            self._render_results_tree()

    def _finish_scan_ui(self):
        self._reset_scan_button()
        self._scan_thread = None
        self._scan_queue = None
        self._scan_stop_event = None
        self._scan_cancelling = False
        self._scan_worker = None

    def _append_scan_result(self, result):
        self._append_scan_results([result])

    def _append_scan_results(self, results):
        if not results:
            return

        self._ignore_tree_select = True
        start_count = len(self.scan_results)
        for result in results:
            idx = len(self.scan_results)
            self.scan_results.append(result)
            self.result_vars.append(tk.BooleanVar(value=True))

            tags = (result["kind"],)

            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                tags=tags,
                values=(
                    "☑",
                    result["kind"],
                    result["name"],
                    self._display_path(result["path"]),
                    fmt_size(result["size"]),
                    fmt_modified(result.get("modified", 0)),
                ),
            )
        self._ignore_tree_select = False

        self.empty_state.place_forget()
        self._update_result_summary()
        self._update_selection_toggle_state()
        count = len(self.scan_results)
        if count <= 20 or count % 100 == 0 or len(results) > 1:
            LOGGER.info(
                "ui results appended batch=%s total=%s first_new=%s",
                len(results),
                count,
                start_count + 1,
            )

    def _show_scan_error(self, message: str, show_dialog=True):
        self.scan_results = []
        self.result_vars = []
        self.tree.delete(*self.tree.get_children())
        self.result_summary_var.set("Scan failed")
        self.empty_state.config(text="📁\nScan failed")
        self.empty_state.place(relx=0.5, rely=0.42, anchor="center")
        self.delete_btn.config(state="disabled")
        self._set_selection_toggle_enabled(False)
        self._finish_scan_ui()
        self.status_var.set(f"Scan failed - {message}")
        LOGGER.error("ui scan failed message=%s", message)
        if show_dialog:
            messagebox.showerror("Scan Failed", message)

    def _render_results_tree(self):
        self._ignore_tree_select = True
        self.tree.delete(*self.tree.get_children())

        for i, r in enumerate(self.scan_results):
            selected = self.result_vars[i].get() if i < len(self.result_vars) else True
            tags = (r["kind"],)
            self.tree.insert("", "end", iid=str(i), tags=tags,
                             values=("☑" if selected else "☐",
                                     r["kind"], r["name"], self._display_path(r["path"]),
                                     fmt_size(r["size"]), fmt_modified(r.get("modified", 0))))

        self._ignore_tree_select = False

    def _sort_results(self, column: str):
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = column in ("size", "modified")
        self._apply_result_sort()
        self._render_results_tree()

    def _apply_result_sort(self):
        if not self.scan_results:
            return

        paired = list(zip(self.scan_results, self.result_vars))

        def sort_key(item):
            result = item[0]
            if self.sort_column == "size":
                return result.get("size", 0)
            if self.sort_column == "modified":
                return result.get("modified", 0)
            return str(result.get(self.sort_column, "")).lower()

        paired.sort(key=sort_key, reverse=self.sort_reverse)
        self.scan_results = [p[0] for p in paired]
        self.result_vars = [p[1] for p in paired]

    def _update_result_summary(self):
        total = len(self.scan_results)
        selected_items = [
            r for r, v in zip(self.scan_results, self.result_vars)
            if v.get()
        ]
        selected = len(selected_items)
        selected_folders = sum(1 for r in selected_items if r["kind"] == "folder")
        selected_files = selected - selected_folders
        selected_file_size = sum(r["size"] for r in selected_items if r["kind"] == "file")

        if total:
            self.result_summary_var.set(
                f"Total {total} · Selected {selected} "
                f"({selected_folders} folders, {selected_files} files) · "
                f"Selected file size {fmt_size(selected_file_size)}"
            )
        else:
            self.result_summary_var.set("No matching clean targets found")

    def _clear_results(self):
        self.scan_results = []
        self.result_vars  = []
        self.tree.delete(*self.tree.get_children())
        self.result_summary_var.set("Scanning...")
        self.delete_btn.config(state="disabled")
        self._set_selection_toggle_enabled(False)
        self.empty_state.config(text="📁\nScanning clean targets...")
        self.empty_state.place(relx=0.5, rely=0.42, anchor="center")

    def _on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        if col != "#1":   # only toggle on checkbox column
            return
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        idx = int(row_id)
        var = self.result_vars[idx]
        var.set(not var.get())
        vals = list(self.tree.item(row_id, "values"))
        vals[0] = "☑" if var.get() else "☐"
        self.tree.item(row_id, values=vals)
        self._update_result_summary()
        self._update_selection_toggle_state()

    def _on_tree_select(self, _event):
        # Native Treeview selection is only visual. Cleanup selection is driven
        # by the checkbox column; syncing both ways caused large scans to
        # repeatedly redraw the whole table and made the UI look stuck.
        return

    def _on_tree_motion(self, event):
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        self._set_hover_row(row_id)
        if col != "#4" or not row_id:
            self._hide_path_tooltip()
            return

        try:
            idx = int(row_id)
        except ValueError:
            self._hide_path_tooltip()
            return

        if idx < 0 or idx >= len(self.scan_results):
            self._hide_path_tooltip()
            return

        path = self.scan_results[idx].get("path", "")
        if not path:
            self._hide_path_tooltip()
            return

        self._tooltip_row = row_id
        self.path_tooltip.show(path, event.x_root + 14, event.y_root + 16)

    def _on_tree_leave(self, _event):
        self._hide_path_tooltip()
        self._set_hover_row("")

    def _hide_path_tooltip(self):
        self._tooltip_row = None
        if hasattr(self, "path_tooltip"):
            self.path_tooltip.hide()

    def _set_hover_row(self, row_id):
        if row_id == self._hover_row:
            return
        if self._hover_row and self.tree.exists(self._hover_row):
            tags = tuple(t for t in self.tree.item(self._hover_row, "tags") if t != "hover")
            self.tree.item(self._hover_row, tags=tags)
        self._hover_row = row_id
        if row_id and self.tree.exists(row_id):
            tags = tuple(self.tree.item(row_id, "tags"))
            if "hover" not in tags:
                self.tree.item(row_id, tags=tags + ("hover",))

    def _display_path(self, path):
        path = str(path)
        max_chars = 64
        if len(path) <= max_chars:
            return path
        head = path[:22]
        tail = path[-(max_chars - len(head) - 3):]
        return f"{head}...{tail}"

    def _select_all(self):
        self._ignore_tree_select = True
        for i, var in enumerate(self.result_vars):
            var.set(True)
            vals = list(self.tree.item(str(i), "values"))
            vals[0] = "☑"
            self.tree.item(str(i), values=vals)
        self._ignore_tree_select = False
        self._update_result_summary()
        self._update_selection_toggle_state()

    def _select_none(self):
        self._ignore_tree_select = True
        for i, var in enumerate(self.result_vars):
            var.set(False)
            vals = list(self.tree.item(str(i), "values"))
            vals[0] = "☐"
            self.tree.item(str(i), values=vals)
        self._ignore_tree_select = False
        self._update_result_summary()
        self._update_selection_toggle_state()

    def _toggle_result_selection(self):
        if not self.result_vars:
            return
        if all(v.get() for v in self.result_vars):
            self._select_none()
        else:
            self._select_all()

    def _set_selection_toggle_enabled(self, enabled: bool):
        if not hasattr(self, "selection_toggle_btn"):
            return
        self.selection_toggle_btn.config(state="normal" if enabled else "disabled")
        self._update_selection_toggle_state()

    def _update_selection_toggle_state(self):
        if not hasattr(self, "selection_toggle_btn"):
            return
        if not self.result_vars:
            self.selection_toggle_btn.config(text="Select All")
            return
        text = "Select None" if all(v.get() for v in self.result_vars) else "Select All"
        self.selection_toggle_btn.config(text=text)

    def _delete_selected(self):
        self._save_scan_options()
        selected = [(i, r) for i, r in enumerate(self.scan_results) if self.result_vars[i].get()]
        if not selected:
            messagebox.showinfo("Nothing selected", "Please check items to move.")
            return

        protected, selected = self._split_whitelisted_items(selected)
        if not selected:
            messagebox.showinfo(
                "Whitelist Protected",
                f"{len(protected)} selected item(s) match the whitelist and will not be moved.",
            )
            self.status_var.set(f"Skipped - {len(protected)} selected item(s) protected by whitelist")
            return

        total_size = sum(r["size"] for _, r in selected)
        folder_count = sum(1 for _, r in selected if r["kind"] == "folder")
        file_count = len(selected) - folder_count
        preview = "\n".join(f"- {r['path']}" for _, r in selected[:8])
        if len(selected) > 8:
            preview += f"\n... and {len(selected) - 8} more"

        msg = (
            "Move selected items to Trash/Recycle Bin?\n\n"
            f"Items: {len(selected)} ({folder_count} folders, {file_count} files)\n"
            f"Total size: {fmt_size(total_size)}\n\n"
            f"{preview}\n\n"
            "You can restore them from the system Trash/Recycle Bin."
        )
        if protected:
            msg += f"\n\nWhitelist protected: {len(protected)} selected item(s) will be skipped."
        if not messagebox.askyesno("Confirm Move", msg, icon="warning"):
            return

        ok, fail = 0, 0
        moved_indices = set()
        for i, r in selected:
            if delete_item(r["path"]):
                moved_indices.add(i)
                ok += 1
            else:
                fail += 1

        # Remove moved items from lists and redraw so tree item ids stay aligned.
        self.scan_results = [r for i, r in enumerate(self.scan_results) if i not in moved_indices]
        self.result_vars  = [v for i, v in enumerate(self.result_vars) if i not in moved_indices]
        self._render_results_tree()
        self._update_result_summary()

        skipped = len(protected)
        self.status_var.set(f"Done - {ok} moved to trash, {fail} failed, {skipped} whitelist skipped")
        if fail:
            messagebox.showwarning("Some failures", f"{fail} item(s) could not be moved to Trash/Recycle Bin.")

        has_results = bool(self.scan_results)
        self.delete_btn.config(state="normal" if has_results else "disabled")
        self._set_selection_toggle_enabled(has_results)
        if has_results:
            self.empty_state.place_forget()
        else:
            self.empty_state.config(text="All selected items moved to trash")
            self.empty_state.place(relx=0.5, rely=0.42, anchor="center")

    def _split_whitelisted_items(self, indexed_results):
        patterns = normalize_pattern_list(self.config_data.get("exclude_patterns", []))
        if not patterns:
            return [], indexed_results

        root_text = self.path_var.get().strip()
        root = Path(root_text) if root_text else Path("/")
        protected = []
        allowed = []
        for item in indexed_results:
            _idx, result = item
            try:
                blocked = should_exclude(Path(result["path"]), root, patterns)
            except Exception:
                blocked = False
            if blocked:
                protected.append(item)
            else:
                allowed.append(item)
        if protected:
            LOGGER.info("delete skipped whitelist count=%s", len(protected))
        return protected, allowed

    def _on_close(self):
        LOGGER.info("app closing")
        # Make sure the polling loop and background thread don't keep the
        # app alive or throw errors against destroyed widgets on exit.
        if self._scan_stop_event is not None:
            self._scan_stop_event.set()
        if self._scan_poll_job is not None:
            try:
                self.after_cancel(self._scan_poll_job)
            except Exception:
                pass
        self.destroy()


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    app = FileCleanerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
