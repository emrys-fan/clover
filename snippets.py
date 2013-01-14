from flask import jsonify as _jsonify

def jsonify(*args, **kwargs):
    """
    Extends flask.jsonify by allowing to set a custom HTTP status code.
    """
    status_code = kwargs.get('status_code', None)
    if status_code is not None:
        del kwargs['status_code']
    response = _jsonify(*args, **kwargs)
    response.status_code = status_code if status_code else 200
    return response
