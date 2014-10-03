class DavException(Exception):
    status = "500 Internal Server Error"


class NotFound(DavException):
    status = "404 Not Found"


class Forbidden(DavException):
    status = "403 Forbidden"


class AlreadyExists(DavException):
    status = "405 Method Not Allowed"


class Conflict(DavException):
    status = "409 Conflict"


class UnsupportedMediaType(DavException):
    status = "415 Unsupported Media Type"


class BadRequest(DavException):
    status = "400 Bad Request"


class BadGateway(DavException):
    status = "502 Bad Gateway"


class PreconditionFailed(DavException):
    status = "412 Precondition Failed"
