"""Shared pytest fixtures for the hardware-free (Layer 2) test suite.

These tests exercise the real command-building logic in ``devices.py``,
``routines.py`` and ``cli.py`` without any pump or valve attached. The only
place the code opens hardware is ``serial.Serial(...)`` inside
``SerialDevice.__init__`` (devices.py), so a single monkeypatch of that class
with :class:`FakeSerial` lets every layer run end to end.

``FakeSerial`` records everything written (as decoded strings) so tests can
assert on the exact V9 protocol frames (e.g. ``GO01``, ``/1EV6d180R``) and
returns canned protocol responses for reads.
"""

import sys
from pathlib import Path

import pytest

# Make the sidecar modules (devices, routines, cli) importable regardless of the
# directory pytest is invoked from.
SIDECAR_ROOT = Path(__file__).resolve().parent.parent
if str(SIDECAR_ROOT) not in sys.path:
    sys.path.insert(0, str(SIDECAR_ROOT))


class FakeSerial:
    """Drop-in stand-in for ``serial.Serial`` that touches no hardware.

    - ``write`` records the decoded string sent to the "device".
    - ``readline`` pops a queued response, or returns ``default_response``.
      The default (``/0`` + backtick) parses as an idle pump status so
      ``Pump.wait_until_ready`` returns immediately, and as a harmless valve
      reply.
    - Every constructed instance is appended to :attr:`instances`, so tests
      that drive code which builds its own devices (the CLI, routines) can
      still inspect what was sent.
    """

    instances: list["FakeSerial"] = []

    def __init__(self, port=None, **kwargs):
        self.port = port
        self.init_kwargs = kwargs
        self.is_open = True
        self.written: list[str] = []
        self._responses: list[bytes] = []
        self.default_response = b"/0`\r\n"
        FakeSerial.instances.append(self)

    def queue_response(self, data):
        """Queue a canned reply for a subsequent ``readline`` call."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        self._responses.append(data)

    def write(self, data):
        if isinstance(data, (bytes, bytearray)):
            data = bytes(data).decode("utf-8", errors="ignore")
        self.written.append(data)

    def readline(self):
        if self._responses:
            return self._responses.pop(0)
        return self.default_response

    def close(self):
        self.is_open = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


@pytest.fixture
def fake_serial(monkeypatch):
    """Patch the serial port and neutralise sleeps for the duration of a test.

    Returns the :class:`FakeSerial` class; use ``FakeSerial.instances`` to get
    the devices that were opened (in construction order).
    """
    FakeSerial.instances = []

    monkeypatch.setattr("devices.serial.Serial", FakeSerial)
    # V9 timing uses many time.sleep() calls; skip them so tests run instantly.
    monkeypatch.setattr("devices.time.sleep", lambda *a, **k: None)

    import routines  # noqa: WPS433 (import inside fixture keeps import optional)

    monkeypatch.setattr("routines.time.sleep", lambda *a, **k: None)

    return FakeSerial
