from rest_framework.response import Response
from rest_framework import status


def success_response(message="Request successful", data=None, status_code=status.HTTP_200_OK):
    return Response({
        "status": "success",
        "message": message,
        "data": data or {}
    }, status=status_code)