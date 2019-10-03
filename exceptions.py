class DrakeException(Exception):
    pass

class DrakeSyntaxError(DrakeException):
    def __init__(self, error, value, linenum, column):
        super().__init__(f'{error}: {value} @ {linenum}:{column}')
        self.error = error
        self.value = value
        self.linenum = linenum
        self.column = column

class DrakeParserError(DrakeException):
    def __init__(self, error, token):
        super().__init__(error)
        self.error = error
        self.token = token