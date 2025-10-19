from django.db import models
import uuid
from django.utils import timezone
from accounts.models import UserProfile


class LoginActivity(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="login_activities")
    device_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)  # optional human-readable
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    success = models.BooleanField(default=True)
    logged_out = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.user.username} - {self.device_name or 'Unknown Device'}"


class SessionResumeToken(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="resume_tokens")
    device = models.ForeignKey(LoginActivity, on_delete=models.CASCADE, related_name="resume_tokens", null=True, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=["is_used"])

    def __str__(self):
        return f"ResumeToken for {self.user.user.username} on {self.device.device_name if self.device else 'Unknown Device'}"
