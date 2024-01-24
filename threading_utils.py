import threading
import functools

def synchronized(wrapped):
    lock = threading.Lock() # semaphore
    
    @functools.wraps(wrapped)
    def _wrap(*args, **kwargs):
        with lock:
            return wrapped(*args, **kwargs)
        
    return _wrap