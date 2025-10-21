from django.contrib.auth import authenticate, get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, authentication_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
from .models import LoginActivity
from accounts.models import UserProfile
from blogsystem.handler.responses.error import error_response
from blogsystem.handler.responses.success import success_response
from .handler.cookies.cookies import set_jwt_cookies
from .utils.get_user_ip import get_client_ip
from handlers.services.email_service import send_templated_email
from rest_framework.throttling import ScopedRateThrottle
User = get_user_model()


@api_view(["POST"])
@authentication_classes([])
@permission_classes([])
@throttle_classes([ScopedRateThrottle])
def register_view(request):
    throttle_scope = "register"
    data = request.data

    username = data.get("username")
    email = data.get("email")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    phone_number = data.get("phone_number")
    password = data.get("password")
    password2 = data.get("confirm_password")

    if not all([username, email, first_name, last_name, password, password2]):
        return error_response("All fields are required", {"details": "Fields are empty"})
    
    if password != password2:
        return error_response("Password does not match", {"details": "Password mismatch"})

    if User.objects.filter(username=username).exists():
        return error_response("Username already taken", {"username": "taken"}, status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return error_response("Email already exists", {"email": "taken"}, status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, email=email, first_name=first_name, last_name=last_name, password=password)

    profile = UserProfile.objects.create(user=user)
    profile.phone_number = phone_number
    profile.save()
    
    return success_response("Registration successful.", {"username": username, "email": email})

register_view.throttle_scope = "register"

@api_view(["POST"])
@permission_classes([])
@authentication_classes([])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")

    try:

        if not all([username, password]):
            return error_response("both username and password are required", {"details": "Fields are missing"})

        user = authenticate(username=username, password=password)
        ip = get_client_ip(request)
        agent = request.META.get("HTTP_USER_AGENT", "")

        if not user:
            try:
                profile = UserProfile.objects.filter(user__username=username).first()
            except UserProfile.DoesNotExist:
                return error_response("profile not found", {"details":"user got no profile"})
            
            LoginActivity.objects.create(user=profile, ip_address=ip, user_agent=agent, success=False)
            return error_response("Invalid credentials", {"details": "wrong credentials"}, status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        LoginActivity.objects.create(user=user.profile, ip_address=ip, user_agent=agent, success=True)


        response = success_response("Login successful", {
            "access": str(access),
            "refresh": str(refresh),
        })

        return set_jwt_cookies(response, refresh, access)
    
    except Exception as e:
        return error_response("An error occured logging in", {"details": str(e)})



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_authentication(request):
    try:
         
        return success_response("authenticated", { "auth": True })

    except Exception as e:
        return error_response("An error occurred when fetching auth state", {
            "details": f":{str(e)}"
        }, status.HTTP_500_INTERNAL_SERVER_ERROR)  



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_device(request):

    try:
        device_id = request.data.get("device_id")
        session = LoginActivity.objects.filter(device_id=device_id, user=request.user.profile).first()

        if not session:
            return error_response("Device session not found", {"device_id": device_id}, status.HTTP_404_NOT_FOUND)

        session.logged_out = True
        session.save(update_fields=["logged_out"])

        return success_response("Device logged out successfully", {"device_id": device_id})
    
    except Exception as e:
        return error_response("An error occured logging out", {"details": str(e)})



# @api_view(["POST"])
# def resume_session(request):
#     """
#         Allows a user to resume a session using a previously issued token.
#         Only returns minimal info (profile, last login) and optionally issues new JWT if confirmed.
#     """
    

#     token = request.data.get("token")
#     resume_token = SessionResumeToken.objects.filter(token=token, is_used=False).first()

#     if not resume_token or resume_token.is_expired():
#         return error_response("Invalid or expired resume token", {"token": token}, status.HTTP_400_BAD_REQUEST)

#     profile = resume_token.user
#     last_login = profile.login_activities.filter(success=True).order_by('-timestamp').first()


#     data = {
#         "username": profile.user.username,
#         "profile_image": profile.profile_image.url if profile.profile_image else None,
#         "last_login_time": last_login.timestamp if last_login else None,
#         "last_login_device": last_login.device_name if last_login else None,
#         "device_id": last_login.device_id if last_login else None,
#     }

#     return success_response("Resume token valid. You can resume session.", data)


# @api_view(["POST"])
# def confirm_resume_session(request):
#     """
#         Confirm a resume token and create a new JWT session.
#     """

#     token = request.data.get("token")
#     device_name = request.data.get("device_name", "Unknown Device")
#     ip = get_client_ip(request)
#     agent = request.META.get("HTTP_USER_AGENT", "")

#     resume_token = SessionResumeToken.objects.filter(token=token, is_used=False).first()
#     if not resume_token or resume_token.is_expired():
#         return error_response("Invalid or expired resume token", {"token": token}, status.HTTP_400_BAD_REQUEST)

#     user = resume_token.user.user


#     session = LoginActivity.objects.create(
#         user=resume_token.user,
#         device_name=device_name,
#         ip_address=ip,
#         user_agent=agent,
#         success=True
#     )

#     refresh = RefreshToken.for_user(user)
#     access = refresh.access_token

#     resume_token.mark_used()

#     expires_at = timezone.now() + timedelta(hours=24)
#     resume_token = SessionResumeToken.objects.create(
#         user=resume_token.user,
#         device=session,
#         expires_at=expires_at,
#         ip_address=ip,
#         user_agent=agent
#     )

#     response = success_response("Session resumed successfully", {
#         "access": str(access),
#         "refresh": str(refresh),
#         "device_id": session.device_id,
#         "expires_at": expires_at
#     })

#     return set_jwt_cookies(response, refresh, access, resume_token.token)
