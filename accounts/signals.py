# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, LoginActivity

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

@receiver(post_delete, sender=User)
def delete_user_related(sender, instance, **kwargs):
    # Automatically delete related UserProfile
    try:
        instance.profile.delete()
    except UserProfile.DoesNotExist:
        pass
