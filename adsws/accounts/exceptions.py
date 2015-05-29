class ValidationError(Exception):
    """
    Exception raised when some user data are invalid
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class NoClientError(Exception):
    """
    Exception raised when no oauth2client is found, but was expected
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class NoTokenError(Exception):
    """
    Exception raised when no oauth2token is found, but was expected
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)