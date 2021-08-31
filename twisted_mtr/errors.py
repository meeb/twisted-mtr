class MTRError(Exception):
    '''
        Raised when an error occurs issuing or handling MTR requests.
    '''
    pass


class SocketError(Exception):
    '''
        Raised when low level socket operations fail or encounter errors.
    '''
    pass


class StateError(Exception):
    '''
        Raised when some important state is violated.
    '''
    pass
