# models.py
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """
        Extends the default Django User model with additional fields.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_image = models.FileField(upload_to="profiles/profile", blank=True, null=True)
    profile_cover_image = models.FileField(upload_to="profiles/covers", blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    last_active = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.username


class Role(models.Model):
    """
        Defines roles for users (Admin, Author, Reader, etc.)
    """

    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """
        Many-to-many mapping between users and roles.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="users")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user.user.username} → {self.role.name}"


# class LoginActivity(models.Model):
#     """
#         Tracks login history and device info for users.
#     """
    
#     user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="login_activities")
#     ip_address = models.GenericIPAddressField(blank=True, null=True)
#     user_agent = models.CharField(max_length=255, blank=True, null=True)
#     location = models.CharField(max_length=255, blank=True, null=True)
#     logged_in_at = models.DateTimeField(auto_now_add=True)
#     logged_out_at = models.DateTimeField(blank=True, null=True)

#     def __str__(self):
#         return f"Login by {self.user.user.username} at {self.logged_in_at}"


class AccountVerification(models.Model):
    METHOD_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey("UserProfile",on_delete=models.CASCADE,related_name="verifications")
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='email')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=6, blank=True, null=True) 
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(blank=True, null=True)

    def is_expired(self):
        """Check if the verification token has expired"""
        return timezone.now() > self.expires_at

    def mark_verified(self):
        """Mark this verification as completed"""
        self.status = 'verified'
        self.verified_at = timezone.now()
        self.save(update_fields=['status', 'verified_at'])

    def __str__(self):
        return f"{self.user.user.username} - {self.method} ({self.status})"


class AccountVerificationToken(models.Model):
    """
        For email/phone verification and password reset.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="verification_tokens")
    token = models.CharField(max_length=100, unique=True)
    purpose = models.CharField(
        max_length=20,
        choices=[
            ("email_verification", "Email Verification"),
            ("password_reset", "Password Reset"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Token for {self.user.user.username} ({self.purpose})"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Password reset token for {self.user.user.username}"