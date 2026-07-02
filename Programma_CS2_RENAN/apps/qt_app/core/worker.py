"""
Background worker pattern for Qt — replaces Kivy's Thread + Clock.schedule_once.

Usage:
    worker = Worker(some_function, arg1, arg2)
    worker.signals.result.connect(on_success)   # auto-marshals to main thread
    worker.signals.error.connect(on_error)
    QThreadPool.globalInstance().start(worker)
"""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    """Signals emitted by Worker — always received on the main thread."""

    finished = Signal()
    error = Signal(str)
    result = Signal(object)
    # F2 (TASKS#33): streaming partials from long-running fns. Emitted only
    # when the Worker was built with wants_progress=True.
    progress = Signal(object)


class Worker(QRunnable):
    """
    Generic background worker. Drop-in replacement for the Kivy pattern:
        Thread(target=fn, daemon=True).start()
        ...
        Clock.schedule_once(lambda dt: callback(result), 0)

    PySide6 Signal connections auto-marshal across threads, so
    worker.signals.result.connect(callback) just works.
    """

    def __init__(self, fn, *args, wants_progress: bool = False, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.wants_progress = wants_progress
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self):
        try:
            kwargs = dict(self.kwargs)
            if self.wants_progress:
                # F2: inject a thread-safe emitter; Qt auto-marshals the signal
                # to the main thread, same guarantee as result/error.
                def _emit_progress(chunk):
                    try:
                        self.signals.progress.emit(chunk)
                    except RuntimeError:
                        pass  # receiver GC'd mid-stream

                kwargs["progress_callback"] = _emit_progress
            result = self.fn(*self.args, **kwargs)
            try:
                self.signals.result.emit(result)
            except RuntimeError:
                pass  # Signal source deleted (receiver GC'd before worker finished)
        except Exception as e:
            try:
                self.signals.error.emit(str(e))
            except RuntimeError:
                pass
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                pass
