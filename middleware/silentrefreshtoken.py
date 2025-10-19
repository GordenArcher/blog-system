from django.http import JsonResponse
import jwt
from datetime import datetime, timezone, timedelta
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.tokens import RefreshToken, TokenError


class SilentRefreshJwtMiddleware(MiddlewareMixin):
    """
    - Reads access & refresh tokens from cookies.
    - If access is expired or about to expire (< refresh_threshold seconds),
      tries to refresh using refresh token.
    - If refresh succeeds: inject new access token into request.META['HTTP_AUTHORIZATION']
      so DRF's authentication will run on the new token.
    - On response, if a new access token was created, set it as an HttpOnly cookie.
    """

    REFRESH_THRESHOLD = 60

    ACCESS_COOKIE_NAME = "access"
    REFRESH_COOKIE_NAME = "refresh"

    def __init__(self, get_response=None):
        super().__init__(get_response)

    def process_request(self, request):
        access_token = request.COOKIES.get(self.ACCESS_COOKIE_NAME)
        refresh_token = request.COOKIES.get(self.REFRESH_COOKIE_NAME)
        
        """
            nothing to do if no tokens (authenticate flow will handle it)
        """
        if not access_token or not refresh_token:
            return None

        """
            Decode without verifying exp to inspect `exp` safely
        """
        try:
            decoded = jwt.decode(
                access_token,
                settings.SIMPLE_JWT.get("SIGNING_KEY", settings.SECRET_KEY),
                algorithms=[settings.SIMPLE_JWT.get("ALGORITHM", "HS256")],
                options={"verify_exp": False}
            )
            exp_ts = decoded.get("exp")
            if exp_ts is None:
                return None

            exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            now = datetime.now(timezone.utc)

            if exp_dt <= now or (exp_dt - now).total_seconds() < self.REFRESH_THRESHOLD:
                self._try_refresh(request, refresh_token)

        except jwt.InvalidTokenError:
            return None
        return None

    def _try_refresh(self, request, refresh_token_str):
        """
        Attempt to get a new access token using the provided refresh token string.
        On success, attach new access token to the request so authentication runs on it.
        """
        try:
            refresh = RefreshToken(refresh_token_str)
            new_access = str(refresh.access_token)

            request._new_access_token = new_access

            request.META["HTTP_AUTHORIZATION"] = f"Bearer {new_access}"

            if getattr(settings, "SIMPLE_JWT", {}).get("ROTATE_REFRESH_TOKENS", False):
                new_refresh = str(refresh)
                request._new_refresh_token = new_refresh
        except TokenError:
            return

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


ALLOWED_ORIGINS = [
    "http://localhost:5173",
]

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