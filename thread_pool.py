import threading
from queue import Queue


class ThreadPool:
    class Worker(threading.Thread):
        def __init__(self, tasks):
            super().__init__()
            self.tasks = tasks
            self.daemon = True
            self.start()

        def run(self):
            while True:
                func, args, kargs = self.tasks.get()
                func(*args, **kargs)
                self.tasks.task_done()

    def __init__(self, num_threads):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            self.Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        self.tasks.put((func, args, kargs))

    def wait_completion(self):
        self.tasks.join()
