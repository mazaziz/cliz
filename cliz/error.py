
class UserError(Exception):
    pass

class InvalidOption(UserError):
    def __init__(self, option: str):
        self.option = option

class UnknownOption(UserError):
    def __init__(self, option: str):
        self.option = option

class MissingOptionValue(UserError):
    def __init__(self, option: str):
        self.option = option
