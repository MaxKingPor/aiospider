from yarl import URL


class Request:
    def __init__(self, url, method='GET', callback=None, meta=None, on_filter=True, **kwargs):
        self.count = 0
        self.meta = meta
        self.url = URL(url)
        self.method = method
        self.callback = callback
        self.filter = on_filter
        self.kwargs = kwargs

    def __str__(self):
        return f'<Request url={self.url!s} method={self.method} count={self.count}>'

    __repr__ = __str__
