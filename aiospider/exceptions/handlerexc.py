class HandlerError(Exception):
    pass


class HandlerFilterError(HandlerError):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        super(HandlerFilterError, self).__init__(f'Filter {name!s} {value!s}')
