from django.conf import settings
import os.path


class FSStorage(object):

    def __init__(self, home=None):
        self.home = home
        if not self.home:
            self.home = settings.DAVVY_STORAGE_PATH

    def store(self, dav, request, resource, chunk_size=32768):
        directory = os.path.join(self.home, str(resource.user.pk))
        if not os.path.exists(directory):
            os.mkdir(directory)
        filename = os.path.join(directory, resource.uuid)
        f = open(filename, 'w')
        cl = long(resource.size)
        while cl > 0:
            chunk = request.read(min(cl, chunk_size))
            if len(chunk) == 0:
                break
            f.write(chunk)
            cl -= len(chunk)
        f.close()

    def retrieve(self, dav, request, resource, chunk_size=32768):
        class FSIterable(object):

            def __init__(self, path, size, chunk_size):
                self.file = open(path, 'r')
                self.size = size
                self.chunk_size = chunk_size

            def __iter__(self):
                return self

            def next(self):
                if self.size <= 0:
                    raise StopIteration
                chunk = self.file.read(min(self.size, self.chunk_size))
                self.size -= len(chunk)
                return chunk
            __next__ = next
        filename = os.path.join(
            self.home, str(resource.user.pk), resource.uuid)
        return FSIterable(filename, resource.size, chunk_size)
