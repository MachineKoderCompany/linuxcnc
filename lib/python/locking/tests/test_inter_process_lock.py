# -*- coding: utf-8 -*-
import pytest

import time
from threading import Thread
from six.moves.queue import Queue

from locking import InterProcessLock, AccessError

LOCK_SLEEP_TIME = 0.05


def test_locking_lock_twice_after_each_other_works():
    lock1 = InterProcessLock(name='foliated')

    with lock1:
        assert True

    with lock1:
        assert True


def test_locking_two_locks_after_each_other_works():
    lock1 = InterProcessLock(name='anchors')
    lock2 = InterProcessLock(name='anchors')

    with lock1:
        assert True

    with lock2:
        assert True


def test_locking_twice_throws_access_error():
    lock1 = InterProcessLock(name='tideward')
    lock2 = InterProcessLock(name='tideward')

    with lock1:
        with pytest.raises(AccessError):
            with lock2:
                pass


def test_locking_from_multiple_processes_waits_for_lock_to_be_released():
    queue = Queue()

    def proc1(q):
        lock1 = InterProcessLock(name='fusspot')
        with lock1:
            q.put(1)
            time.sleep(LOCK_SLEEP_TIME)

    def proc2(q):
        lock2 = InterProcessLock(name='fusspot', timeout=LOCK_SLEEP_TIME * 5)
        with lock2:
            q.put(2)

    thread1 = Thread(target=proc1, args=(queue,))
    thread1.start()
    time.sleep(LOCK_SLEEP_TIME/2)
    thread2 = Thread(target=proc2, args=(queue,))
    thread2.start()

    while thread1.is_alive() or thread2.is_alive():
        time.sleep(LOCK_SLEEP_TIME / 2)

    assert queue.qsize() == 2
    assert queue.get() == 1
    assert queue.get() == 2
