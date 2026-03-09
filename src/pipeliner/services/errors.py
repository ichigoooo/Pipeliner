class PipelinerError(Exception):
    pass


class NotFoundError(PipelinerError):
    pass


class ConflictError(PipelinerError):
    pass


class InvalidStateError(PipelinerError):
    pass


class ValidationError(PipelinerError):
    pass
