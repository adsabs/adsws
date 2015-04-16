class ValidationError(Exception):
    """
    Exception raised when some user data are invalid
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
