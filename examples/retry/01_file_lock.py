"""Retry acquiring a file lock that another process may hold."""
import os, tempfile, threading
from smolib import retry, t

LOCK = os.path.join(tempfile.gettempdir(), "smolib_example.lock")

def acquire_lock() -> t.Attempt[str, str, str]:
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, b"locked")
        os.close(fd)
        return t.Ok(LOCK)
    except FileExistsError:
        return t.Pending("lock held")

# simulate contention: create the lock, remove it after 3s
open(LOCK, "w").close()
threading.Timer(3, lambda: os.remove(LOCK)).start()

result, attempts = retry(acquire_lock, n=10, wait=t.Wait.const(1))
match result:
    case t.Ok(value=path):
        print(f"acquired {path} after {attempts.k} attempts ({attempts.elapsed:.1f}s)")
        os.remove(path)
    case t.Exhausted():
        print(f"gave up after {attempts.k} tries: {attempts.reasons}")
    case t.Err(error=e):
        print(f"error: {e}")
