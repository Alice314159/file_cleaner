import queue
import threading

from core.scanner import scan_targets


class ScanWorker:
    def __init__(self, path, targets, excludes, max_depth):
        self.queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.path = path
        self.targets = targets
        self.excludes = excludes
        self.max_depth = max_depth

    def start(self):
        self.thread.start()

    def cancel(self):
        self.stop_event.set()

    def _run(self):
        try:
            results = scan_targets(
                self.path,
                self.targets,
                self.excludes,
                self.max_depth,
                progress_callback=lambda *args: self.queue.put(("progress", *args)),
                result_callback=lambda result: self.queue.put(("result", result)),
                stop_event=self.stop_event,
            )
            self.queue.put(("cancelled" if self.stop_event.is_set() else "done", results))
        except Exception as exc:
            self.queue.put(("error", f"{exc.__class__.__name__}: {exc}"))
