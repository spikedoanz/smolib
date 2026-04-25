"""Retry acquiring a file lock that another process may hold."""
import os, tempfile, threading
from smolib import retry, Attempt, Ok, Pending, Exhausted, Err, Wait

LOCK = os.path.join(tempfile.gettempdir(), "smolib_example.lock")

def acquire_lock() -> Attempt[str, str, str]:
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, b"locked")
        os.close(fd)
        return Ok(LOCK)
    except FileExistsError:
        return Pending("lock held")

# simulate contention: create the lock, remove it after 3s
open(LOCK, "w").close()
threading.Timer(3, lambda: os.remove(LOCK)).start()

result, attempts = retry(acquire_lock, n=10, wait=Wait.const(1))
match result:
    case Ok(value=path):
        print(f"acquired {path} after {attempts.k} attempts ({attempts.elapsed:.1f}s)")
        os.remove(path)
    case Exhausted():
        print(f"gave up after {attempts.k} tries: {attempts.reasons}")
    case Err(error=e):
        print(f"error: {e}")
