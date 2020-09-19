import copy
import json
import typing
import collections.abc
from importlib import import_module


class SettingsAttr:
    def __init__(self, value, priority):
        self.value = value
        self.priority = priority

    def set(self, value, priority):
        if 0 <= priority >= self.priority:
            self.value = value
            self.priority = priority

    def __str__(self):
        return f"<SettingsAttribute value={self.value!r} priority={self.priority}>"

    __repr__ = __str__

    def __deepcopy__(self, memodict=None):
        if self.priority < 0:
            return self
        else:
            return type(self)(copy.deepcopy(self.value), copy.deepcopy(self.priority))


class Settings(collections.abc.MutableMapping):
    def __init__(self, attrs=None, priority=0, key=lambda x: x):
        self.attrs: typing.Dict[typing.Any, SettingsAttr] = {}
        self.key = key
        self.update(attrs, priority)

    def update(self, attrs: typing.Union[str, dict], priority=0):
        if isinstance(attrs, str):
            attrs = json.loads(attrs)
        if isinstance(attrs, collections.abc.MutableMapping):
            for k, v in attrs.items():
                self.set(k, v, priority)

    def setmodule(self, module, priority=0):
        if isinstance(module, str):
            module = import_module(module)
        for key in dir(module):
            if key.isupper():
                self.set(key, getattr(module, key), priority)

    def __setitem__(self, k, v) -> None:
        self.set(k, v)

    def set(self, k, v, priority=0):
        priority = self.key(priority)
        if k not in self:
            if isinstance(v, SettingsAttr):
                self.attrs[k] = v
            else:
                self.attrs[k] = SettingsAttr(v, priority)
        else:
            self.attrs[k].set(v, priority)

    def copy(self):
        return copy.deepcopy(self)

    def __contains__(self, item):
        return item in self.attrs

    def __delitem__(self, v) -> None:
        del self.attrs[v]

    def __getitem__(self, k):
        return self.attrs[k].value

    def __len__(self) -> int:
        return len(self.attrs)

    def __iter__(self):
        return iter(self.attrs)

    def __str__(self):
        return self.attrs.__str__()
