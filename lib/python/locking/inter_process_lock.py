import base64
import fcntl
import os
import time

CHECK_INTERVAL = 0.01

TMP_PATH = '/tmp'


class AccessError(Exception):
    pass


class InterProcessLock(object):
    """
    This class provides inter process locking on Linux.
    """

    def __init__(self, name, timeout=0.0):
        self._name = base64.b64encode(name.encode()).replace(b'=', b'').decode()
        self._lock_file_path = os.path.join(TMP_PATH, self._name + '.lock')
        self.timeout = timeout
        assert os.path.isdir(TMP_PATH)

    def __enter__(self):
        self._lock(timeout=self.timeout)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._unlock()

    def _do_lock(self):
        self._lock_file = open(self._lock_file_path, 'w')
        try:
            fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            self._lock_file.close()
            self._lock_file = None
            raise AccessError

    def _lock(self, timeout=0.0):
        start_time = time.time()
        while True:
            try:
                self._do_lock()
                return
            except AccessError as e:
                if timeout:
                    current_time = time.time()
                    diff = current_time - start_time
                    if diff >= timeout:
                        raise e
                else:
                    raise e
            time.sleep(CHECK_INTERVAL)

    def _unlock(self):
        if not self._lock_file:
            return
        try:
            os.unlink(self._lock_file_path)
            self._lock_file.close()
        except OSError:
            pass  # in rare cases the file might unlinked by the other process
        self._lock_file = None
