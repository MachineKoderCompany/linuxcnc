from .inter_process_lock import InterProcessLock


class ObjectLock(object):
    """
    The object lock wraps any function call of the object with lock.
    Therefore, it enables synchronized access to shared resources.
    """

    def __init__(self, object_, name, timeout=0.0):
        self._object = object_
        self._lock = InterProcessLock(name, timeout)

    @property
    def timeout(self):
        return self._lock.timeout

    @timeout.setter
    def timeout(self, value):
        self._lock.timeout = value

    def __getattr__(self, item):
        attr = getattr(self._object, item)
        if callable(attr):

            def wrapped(*args, **kwargs):
                with self._lock:
                    attr(*args, **kwargs)

            return wrapped
        else:
            return attr
