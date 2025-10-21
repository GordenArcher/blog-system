from django.db import models
from django.utils.text import slugify
from accounts.models import UserProfile
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Post(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="posts")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()
    content_markdown = models.BooleanField(default=True)
    excerpt = models.TextField(blank=True)
    cover_image = models.URLField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, related_name="posts", blank=True)

    views = models.PositiveIntegerField(default=0)

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    seo_title = models.CharField(max_length=255, blank=True)
    seo_description = models.TextField(blank=True)
    canonical_url = models.URLField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        if not self.excerpt:
            self.excerpt = self.content[:200] 
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def total_likes(self):
        return self.post_likes.count()


class Like(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="post_likes")
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="user_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user.username} liked {self.post.title}"


# class PostStat(models.Model):
#     """Tracks post-level analytics."""
#     post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name="stats")
#     views = models.PositiveIntegerField(default=0)
#     likes = models.PositiveIntegerField(default=0)
#     comments_count = models.PositiveIntegerField(default=0)
#     shares = models.PositiveIntegerField(default=0)

#     def __str__(self):
#         return f"Stats for {self.post.title}"





# {
#   "id": 123,
#   "slug": "how-to-balance-love-and-career",
#   "title": "How to Balance Love and Career",
#   "content": "Love and career are like two wings of the same bird...",
#   "content_markdown": true,
#   "excerpt": "Finding balance between your personal life and ambitions can be tricky...",
#   "cover_image": "https://cdn.gordenwrites.com/uploads/post123-cover.webp",
#   "reading_time": 5,
#   "tags": ["relationships", "self-growth", "career"],
#   "category": {
#     "id": 7,
#     "name": "Lifestyle"
#   },
#   "author": {
#     "id": 45,
#     "username": "jon",
#     "full_name": "Jonathan Mensah",
#     "profile_image": "https://cdn.gordenwrites.com/avatars/jon.webp",
#     "bio": "Writer & designer passionate about the human experience.",
#     "custom_domain": "jon.gordenwrites.com",
#     "is_premium": true
#   },
#   "stats": {
#     "views": 4829,
#     "likes": 377,
#     "comments_count": 52,
#     "shares": 89
#   },
#   "is_liked": false,
#   "comments": [
#     {
#       "id": 201,
#       "user": {
#         "id": 501,
#         "username": "mary",
#         "profile_image": "https://cdn.gordenwrites.com/avatars/mary.webp"
#       },
#       "content": "This hit deep! ❤️ I really needed this reminder.",
#       "created_at": "2025-10-19T14:23:45Z",
#       "likes": 12,
#       "is_liked": true,
#       "replies": [
#         {
#           "id": 202,
#           "user": {
#             "id": 45,
#             "username": "jon"
#           },
#           "content": "Glad it did, Mary. Wishing you balance and peace 🙏",
#           "created_at": "2025-10-19T15:01:22Z",
#           "likes": 4,
#           "is_liked": false
#         }
#       ]
#     }
#   ],
#   "seo": {
#     "title": "How to Balance Love and Career | GordenWrites",
#     "description": "Learn how to navigate love and work in a demanding world.",
#     "canonical_url": "https://gordenwrites.com/blog/how-to-balance-love-and-career"
#   },
#   "meta": {
#     "created_at": "2025-09-15T08:14:11Z",
#     "updated_at": "2025-09-17T10:45:32Z",
#     "is_published": true,
#     "status": "public",
#     "request_id": "req_8ad3bf49f2a4",
#     "api_version": "v1.4"
#   }
# }
