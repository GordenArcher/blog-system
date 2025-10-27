
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import Post, Category


@receiver([post_save, post_delete], sender=Post)
def clear_post_cache(sender, instance, **kwargs):
    """
        Clears all post-related caches when a post is created, updated, or deleted.
    """
    keys = [
        "post_list",          # cache key for all posts
        "trending_posts",     # cache key for trending posts
    ]
    for key in keys:
        cache.delete(key)

    # Clear user-specific cached posts
    user_id = instance.author.id
    cache.delete_pattern(f"user_posts:{user_id}:*")


@receiver([post_save, post_delete], sender=Category)
def clear_category_cache(sender, **kwargs):
    """
        Clears cached categories when a category is created, updated, or deleted.
    """
    cache.delete("all_categories")
