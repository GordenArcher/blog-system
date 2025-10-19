from rest_framework.response import Response
from rest_framework import status


def error_response(message="Request failed", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({
        "status": "error",
        "message": message,
        "errors": errors or {}
    }, status=status_code)
