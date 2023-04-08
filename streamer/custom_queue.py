
class Queue:
    def __init__(self, queue_size):
        self.queue_size = queue_size
        self.queue = list()

    def __repr__(self):
        return self.queue

    @property
    def item(self):
        return self.get()

    def put(self, item):
        if len(self.queue) >= self.queue_size:
            self.queue.pop(0)
        self.queue.append(item)

    def get(self, index=None):
        if index is None:
            try:
                return self.queue.pop(0)
            except:
                return None
        try:
            return self.queue[index]
        except IndexError:
            return None

    def size(self):
        return len(self.queue)

    def is_empty(self):
        if len(self.queue) == 0:
            return True
        return False

    def is_full(self):
        if len(self.queue) == self.queue_size:
            return True
        return False


if __name__ == '__main__':
    q = Queue(5)
    for i in range(8):
        q.put(i)

    print(q.queue)
    print(q.get(0))
    print(q.is_empty())
    print(q.is_full())
    print(q.size())
