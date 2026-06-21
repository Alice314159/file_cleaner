import tkinter as tk

from config.settings import COLORS


class FlatButton(tk.Label):
    """A simple colored button that renders consistently on macOS Tk."""

    def __init__(self, parent, text, command, bg, fg="white",
                 hover_bg=None, disabled_bg=None, disabled_fg=None,
                 font=("Helvetica", 11), padx=14, pady=7, width=None):
        super().__init__(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            font=font,
            padx=padx,
            pady=pady,
            width=width,
            cursor="hand2",
            anchor="center",
            relief="flat",
            bd=0,
        )
        self.command = command
        self.base_bg = bg
        self.base_fg = fg
        self.hover_bg = hover_bg or bg
        self.disabled_bg = disabled_bg or COLORS["disabled"]
        self.disabled_fg = disabled_fg or COLORS["disabled_text"]
        self.enabled = True

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def configure(self, cnf=None, **kw):
        if cnf:
            kw.update(cnf)
        if not kw:
            return super().configure()

        state = kw.pop("state", None)
        if "bg" in kw:
            self.base_bg = kw["bg"]
        if "background" in kw:
            self.base_bg = kw["background"]
        if "fg" in kw:
            self.base_fg = kw["fg"]
        if "foreground" in kw:
            self.base_fg = kw["foreground"]
        if "hover_bg" in kw:
            self.hover_bg = kw.pop("hover_bg")
        if "disabled_bg" in kw:
            self.disabled_bg = kw.pop("disabled_bg")
        if "disabled_fg" in kw:
            self.disabled_fg = kw.pop("disabled_fg")

        result = super().configure(**kw)
        if state is not None:
            self._set_enabled(state != "disabled")
        return result

    config = configure

    def _set_enabled(self, enabled: bool):
        self.enabled = enabled
        if enabled:
            super().configure(bg=self.base_bg, fg=self.base_fg, cursor="hand2")
        else:
            super().configure(bg=self.disabled_bg, fg=self.disabled_fg, cursor="")

    def _on_enter(self, _event):
        if self.enabled:
            super().configure(bg=self.hover_bg)

    def _on_leave(self, _event):
        if self.enabled:
            super().configure(bg=self.base_bg)

    def _on_click(self, _event):
        if self.enabled and self.command:
            self.command()
