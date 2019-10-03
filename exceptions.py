class DrakeException(Exception):
    pass

class SyntaxError(DrakeException):
    def __init__(self, error, value, linenum, column):
        super().__init__(f'{error}: {value} @ {linenum}:{column}')
        self.error = error
        self.value = value
        self.linenum = linenum
        self.column = column
