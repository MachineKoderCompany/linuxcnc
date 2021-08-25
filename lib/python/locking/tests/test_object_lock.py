# -*- coding: utf-8 -*-
import time

from threading import Thread
from six.moves.queue import Queue

from locking import InterProcessLock
from locking.object_lock import ObjectLock

LOCK_SLEEP_TIME = 0.05


class FunctionDoer(object):
    def __init__(self, funct):
        self.funct = funct

    def do(self, arg1):
        self.funct(arg1)


def test_execution_of_function_is_locked():
    queue = Queue()

    def proc1(q):
        lock2 = InterProcessLock(name='mongos')
        q.put(1)
        with lock2:
            time.sleep(LOCK_SLEEP_TIME)
            q.put(2)

    def proc2(q):
        obj = FunctionDoer(lambda x: q.put(x))
        locked_object = ObjectLock(obj, 'mongos', timeout=LOCK_SLEEP_TIME * 5)

        locked_object.do(3)

    thread1 = Thread(target=proc1, args=(queue,))
    thread1.start()
    time.sleep(LOCK_SLEEP_TIME/2)
    thread2 = Thread(target=proc2, args=(queue,))
    thread2.start()

    while thread1.is_alive() or thread2.is_alive():
        time.sleep(LOCK_SLEEP_TIME / 2)

    assert queue.qsize() == 3
    assert queue.get() == 1
    assert queue.get() == 2
    assert queue.get() == 3
