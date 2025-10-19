from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.utils import timezone
from .models import UserProfile, Role, UserRole, AccountVerification
from rest_framework_simplejwt.authentication import JWTAuthentication
from datetime import timedelta
import uuid
from django.conf import settings
from .serializers import *
from blogsystem.handler.responses.error import error_response
from blogsystem.handler.responses.success import success_response
from handlers.services.email_service import send_templated_email
from handlers.services.sms_service import send_sms


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_profile(request):
    profile = request.user.profile

    data = UserProfileSerializer(profile)

    return success_response("ok", data)



@api_view(['PUT'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_profile(request):
    profile = request.user.profile
    data = request.data

    profile.bio = data.get('bio', profile.bio)
    profile.phone_number = data.get('phone_number', profile.phone_number)
    profile.address = data.get('address', profile.address)
    profile.website = data.get('website', profile.website)
    profile.date_of_birth = data.get('date_of_birth', profile.date_of_birth)
    profile.twitter = data.get('twitter', profile.twitter)
    profile.facebook = data.get('facebook', profile.facebook)
    profile.instagram = data.get('instagram', profile.instagram)
    profile.linkedin = data.get('linkedin', profile.linkedin)

    # handle images if sent via multipart/form-data
    if 'profile_image' in request.FILES:
        profile.profile_image = request.FILES['profile_image']
    if 'profile_cover_image' in request.FILES:
        profile.profile_cover_image = request.FILES['profile_cover_image']

    profile.save()
    return success_response('Profile updated successfully', None, status=status.HTTP_200_OK)



@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_user_roles(request):
    profile = request.user.profile
    roles = profile.roles.select_related('role').all()
    data = [{'name': r.role.name, 'description': r.role.description} for r in roles]
    return success_response("", {'roles': data})



@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def assign_role(request):
    if not request.user.is_staff:
        return error_response("Request denied \n You can't assign roles", {'details': 'Only admins can assign roles'}, status=status.HTTP_403_FORBIDDEN)

    username = request.data.get('username')
    role_name = request.data.get('role')

    try:
        user = User.objects.get(username=username)
        profile = user.profile
        role = Role.objects.get(name=role_name)
    except (User.DoesNotExist, Role.DoesNotExist):
        return Response({'error': 'User or Role not found'}, status=status.HTTP_404_NOT_FOUND)


    UserRole.objects.get_or_create(user=profile, role=role)
    return success_response("role", {'message': f'Role "{role_name}" assigned to {username}'})



@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_login_activity(request):
    profile = request.user.profile
    activities = profile.login_activities.all().order_by('-logged_in_at')[:10]  # latest 10
    data = [
        {
            "ip": a.ip_address,
            "user_agent": a.user_agent,
            "location": a.location,
            "logged_in_at": a.logged_in_at,
            "logged_out_at": a.logged_out_at,
        } for a in activities
    ]
    return Response({'login_history': data})


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def request_verification(request):
    """
        Send a verification code via email or SMS.
    """
    method = request.data.get("method", "email").lower()
    profile = request.user.profile


    if method not in ["email", "phone"]:
        return error_response("Invalid method.", {"method": "Use 'email' or 'phone'."})

    if method == "phone" and not profile.phone_number:
        return error_response("Phone number not found on profile.", {"phone_number": "Required for phone verification."})

    existing = (AccountVerification.objects.filter(user=profile, method=method, status="pending").order_by("-created_at").first())

    if existing and not existing.is_expired():
        return error_response(f"An active {method} verification already exists.", {"expires_at": existing.expires_at})

    code = str(uuid.uuid4().int)[:6]
    token = uuid.uuid4()
    expires_at = timezone.now() + timedelta(minutes=15)

    verification = AccountVerification.objects.create(
        user=profile,
        method=method,
        expires_at=expires_at,
        token=token,
        code=code
    )

    try:
        frontend_url = f"{settings.FRONTEND_URL}/auth/account/verify?token={token}&code={code}"

        if method == "email":
            send_templated_email(
                to_email=profile.user.email,
                subject="Verify Your Account",
                template_name="accounts/email_verification",
                context={
                    "user": profile.user,
                    "code": code,
                    "expires_at": expires_at,
                    "app_name": getattr(settings, "APP_NAME", "JournIQ")
                }
            )
        else:
            message = (
                f"Hi {request.user.username or 'there'}! 👋\n\n"
                f"Your JournIQ verification details:\n"
                f"• Code: {code}\n"
                f"• Token: {token}\n\n"
                f"This code and token expire in 15 minutes.\n\n"
                f"Verify your account here 👉 {frontend_url}\n\n"
                f"If you didn’t request this, please ignore this message."
            )

            send_sms(profile.phone_number, message)

    except Exception as e:
        verification.delete()
        return error_response("Failed to send verification message.", {"details": str(e)})


    return success_response(f"{method.capitalize()} verification sent successfully.", {"expires_at": expires_at, "method": method })


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def verify_account(request):
    """
        Verify user using the token and code sent.
    """

    token = request.data.get('token')
    code = request.data.get('code')
    profile = request.user.profile

    if not all([code, token]):
        return error_response("Code and token are required.", {"fields": ["code", "token"]})

    try:
        verification = AccountVerification.objects.get(user=profile, token=token)
    except AccountVerification.DoesNotExist:
        return error_response("Invalid verification token.", {"token": "Token not found."})

    if verification.is_expired():
        verification.status = 'expired'
        verification.save()
        return error_response("Verification token has expired.", {"token": "Expired token."})

    if verification.code != code:
        return error_response("Invalid verification code.", {"code": "Code mismatch."})

    verification.mark_verified()
    profile.is_verified = True
    profile.save(update_fields=['is_verified'])

    return success_response(f"{verification.method.capitalize()} verified successfully.")



@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_account(request):
    user = request.user
    user.delete()
    return Response({'message': 'Account deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
