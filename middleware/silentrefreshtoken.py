import jwt
from datetime import datetime, timezone
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import RefreshToken, TokenError, AccessToken

class SilentRefreshJwtMiddleware(MiddlewareMixin):
    """
    Automatically refreshes expired or about-to-expire access tokens using refresh tokens from cookies.
    """

    REFRESH_THRESHOLD = 60  # seconds before expiry
    ACCESS_COOKIE_NAME = "access"
    REFRESH_COOKIE_NAME = "refresh"

    def process_request(self, request):
        access_token = request.COOKIES.get(self.ACCESS_COOKIE_NAME)
        refresh_token = request.COOKIES.get(self.REFRESH_COOKIE_NAME)

        if not refresh_token:
            return None

        if not access_token:
            return self._try_refresh(request, refresh_token)

        try:
            token = AccessToken(access_token)
            exp = token["exp"]
            now = datetime.now(timezone.utc)

            # Check if it will expire soon
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            if (exp_dt - now).total_seconds() < self.REFRESH_THRESHOLD:
                self._try_refresh(request, refresh_token)

        except TokenError:
            self._try_refresh(request, refresh_token)
        except Exception as e:
            print("Silent refresh error:", e)

        return None

    def _try_refresh(self, request, refresh_token_str):
        try:
            refresh = RefreshToken(refresh_token_str)
            new_access = str(refresh.access_token)
            request._new_access_token = new_access

            request.META["HTTP_AUTHORIZATION"] = f"Bearer {new_access}"

            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", False):
                new_refresh = str(refresh)
                request._new_refresh_token = new_refresh

            print("[SilentRefresh] Access token refreshed successfully")

        except TokenError as e:
            print("[SilentRefresh] Refresh failed:", e)

    def process_response(self, request, response):
        new_access = getattr(request, "_new_access_token", None)
        new_refresh = getattr(request, "_new_refresh_token", None)

        if new_access:
            response.set_cookie(
                key=self.ACCESS_COOKIE_NAME,
                value=new_access,
                httponly=True,
                secure=True,
                samesite="None",
                max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
            )

        if new_refresh:
            response.set_cookie(
                key=self.REFRESH_COOKIE_NAME,
                value=new_refresh,
                httponly=True,
                secure=True,
                samesite="None",
                max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
            )

        return response




ALLOWED_ORIGINS = ["http://localhost:5173"] 
class IsFromAllowedOrigin: 
    def __init__(self, get_response): 
        self.get_response = get_response 

        def __call__(self, request): 
            origin = request.META.get("HTTP_ORIGIN") 
            referer = request.META.get("HTTP_REFERER") 
            if not origin and not referer: 
                return JsonResponse({"detail": "Access denied"}, status=403) 
            if not self._is_allowed(origin, referer): 
                return JsonResponse({"detail": "Access denied"}, status=403) 
            return self.get_response(request) 
        
    def _is_allowed(self, origin, referer): 
        for allowed in ALLOWED_ORIGINS: 
            if (origin and origin.startswith(allowed)) or (referer and referer.startswith(allowed)): 
                return True 
            return False