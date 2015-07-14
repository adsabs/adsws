"""
Contains useful functions and utilities that are not neccessarily only useful
for this module. But are also used in differing modules insidide the same
project, and so do not belong to anything specific.
"""

def err(error_dictionary):
    """
    Formats the error response as wanted by the Flask app
    :param error_dictionary: name of the error dictionary

    :return: tuple of error message and error number
    """
    return {'error': error_dictionary['body']}, error_dictionary['number']