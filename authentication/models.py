from django.db import models
import uuid
from django.utils import timezone
from accounts.models import UserProfile


class SessionResumeToken(models.Model):
    """
    Stores a temporary token that allows a user to 'continue session'
    after logging out, without full re-authentication.
    """
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="resume_tokens")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    def is_expired(self):
        """Check if the token has expired."""
        return timezone.now() > self.expires_at

    def mark_used(self):
        """Invalidate this token after it’s used."""
        self.is_used = True
        self.save(update_fields=["is_used"])

    def __str__(self):
        return f"ResumeToken for {self.user.user.username}"
