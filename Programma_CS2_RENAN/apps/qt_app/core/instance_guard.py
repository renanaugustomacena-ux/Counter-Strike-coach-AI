"""Second-launch handling — raise the running dashboard instead of a dialog.

The close button hides the window to the tray (CLOSE_TO_TRAY), so the next
launch used to be refused with "Macena is already running — check the
system tray".  The kernel mutex in ``core/lifecycle.py`` remains the lock;
this module adds the courtesy on top: the first instance listens on a
``QLocalServer``, a second launch connects, sends ``RAISE`` and exits, and
the first instance shows, raises and activates its window.

Lifetime rules (learned the hard way — a stale DeferredDelete posted from
a nested event loop aborted the process on the next forced flush):
no ``deleteLater`` anywhere in here; accepted sockets stay children of the
server and die with it; the server is deleted synchronously in ``close()``;
slots are bound methods (``sender()``), never lambdas that capture ``self``.
"""

from __future__ import annotations

from typing import Callable, Optional

import shiboken6
from PySide6.QtCore import QEventLoop, QObject, QTimer, Slot
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.instance_guard")

RAISE_COMMAND = b"RAISE\n"
_ACK = b"OK\n"


class InstanceGuard(QObject):
    """Owned by the first instance; calls ``on_raise`` for every RAISE received."""

    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._name = name
        self._server: Optional[QLocalServer] = None
        self._on_raise: Optional[Callable[[], None]] = None

    def listen(self, on_raise: Callable[[], None]) -> bool:
        self._on_raise = on_raise
        # A crashed instance can leave the socket file behind on POSIX;
        # removing it first is a no-op on Windows named pipes.
        QLocalServer.removeServer(self._name)
        server = QLocalServer(self)
        if not server.listen(self._name):
            logger.warning(
                "Instance guard cannot listen on %s: %s", self._name, server.errorString()
            )
            shiboken6.delete(server)
            return False
        server.newConnection.connect(self._on_new_connection)
        self._server = server
        return True

    def close(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            server.close()
            if shiboken6.isValid(server):
                shiboken6.delete(server)  # synchronous: takes its accepted sockets along
        QLocalServer.removeServer(self._name)

    # ── internals ──

    @Slot()
    def _on_new_connection(self) -> None:
        while self._server is not None and self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            if sock is None:
                return
            sock.readyRead.connect(self._on_ready_read)
            self._consume(sock)  # bytes may already be buffered

    @Slot()
    def _on_ready_read(self) -> None:
        sock = self.sender()
        if isinstance(sock, QLocalSocket):
            self._consume(sock)

    def _consume(self, sock: QLocalSocket) -> None:
        data = bytes(sock.readAll())
        if RAISE_COMMAND.strip() not in data:
            return
        sock.write(_ACK)
        sock.flush()
        if self._on_raise is not None:
            try:
                self._on_raise()
            except Exception:  # noqa: BLE001 — a raise failure must not kill the server
                logger.exception("Instance guard: raise callback failed")


def notify_running_instance(name: str, timeout_ms: int = 1000) -> bool:
    """Ask the instance listening on ``name`` to raise itself. False when nobody listens.

    The write is asynchronous on Windows named pipes: destroying the socket
    right after ``write()`` cancels the pending I/O and the bytes never
    land. So the socket stays alive until the listener acknowledges (or
    the timeout elapses), waiting on a bounded event loop rather than a
    blocking ``waitFor*`` so a listener in the same process can answer.
    """
    sock = QLocalSocket()
    sock.connectToServer(name)
    if not sock.waitForConnected(timeout_ms):
        return False

    loop = QEventLoop()
    # The timer is owned by the socket and stopped before the loop dies, so
    # a late timeout can never call quit() on a destroyed QEventLoop.
    timer = QTimer(sock)
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    sock.readyRead.connect(loop.quit)
    sock.disconnected.connect(loop.quit)
    sock.errorOccurred.connect(loop.quit)
    timer.start(timeout_ms)
    sock.write(RAISE_COMMAND)
    loop.exec()
    timer.stop()
    for signal in (timer.timeout, sock.readyRead, sock.disconnected, sock.errorOccurred):
        try:
            signal.disconnect(loop.quit)
        except (RuntimeError, TypeError):
            pass

    sock.disconnectFromServer()
    if sock.state() != QLocalSocket.LocalSocketState.UnconnectedState:
        sock.waitForDisconnected(timeout_ms)
    sock.close()
    return True
