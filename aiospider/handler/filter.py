import hashlib
from . import SpiderHandler


class FilterHandler(SpiderHandler):
    def __init__(self, *args, **kwargs):
        super(FilterHandler, self).__init__(*args, **kwargs)
        self.filters = set()

    async def process_request(self, request):
        if request.count >= 5:
            return None
        if request.filter:
            url = request.url
            if not isinstance(url, str):
                url = str(url)
            md5 = hashlib.md5(bytes(url, 'utf-8'))
            md5.update(bytes(f'{request!s}', 'utf-8'))
            hx = md5.hexdigest()
            if hx in self.filters:
                return None
            self.filters.add(hx)
        return request
