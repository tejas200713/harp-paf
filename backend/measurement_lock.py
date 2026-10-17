"""Machine-wide lock so only one measurement runs at a time.

Calibration, CLI experiments and server jobs all pin work to the same SMT
core; two of them running together would corrupt each other's timings. The
lock is an OS file lock on artifacts/.measurement.lock, released
automatically if the process exits or crashes.
"""

from contextlib import contextmanager
import os

from backend import config

if os.name == "nt":
    import msvcrt
else:
    import fcntl


LOCK_OFFSET = 4096   # locked byte on Windows, past the readable holder text


class MeasurementBusy(RuntimeError):
    pass


@contextmanager
def measurement_lock(purpose):
    config.MEASUREMENT_LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = open(config.MEASUREMENT_LOCK, "a+")

    try:
        try:
            if os.name == "nt":
                handle.seek(LOCK_OFFSET)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.seek(0)
            holder = handle.read().strip() or "another process"
            raise MeasurementBusy(
                f"Another measurement is running ({holder}); wait for it to finish"
            ) from None

        handle.seek(0)
        handle.truncate()
        handle.write(f"{purpose}, pid {os.getpid()}")
        handle.flush()
        yield

    finally:
        try:
            if os.name == "nt":
                handle.seek(LOCK_OFFSET)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        handle.close()
