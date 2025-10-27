from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import UserProfile

@receiver([post_save, post_delete], sender=UserProfile)
def clear_user_profile_cache(sender, instance, **kwargs):
    cache.delete(f"user_profile:{instance.user.id}")
