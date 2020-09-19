import typing

from aiohttp import ClientResponse
from yarl import URL


class Request:
    def __init__(self, url:typing.Union[str, URL], method:str='GET',
                 callback:typing.Callable[[ClientResponse,typing.Any],
                                          typing.Union[typing.AsyncIterable[typing.Union[None, typing.Any, Request]],
                                              typing.AsyncGenerator[typing.Union[None, typing.Any, Request]]
                                          ]]=None,
                 meta:typing.Any=None, on_filter:bool=True, **kwargs):
        self.filter = on_filter
        self.count:int = 0
        self.kwargs = kwargs
        self.url = url
        self.method = method
        self.callback = callback
        self.meta = meta
