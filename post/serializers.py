from rest_framework import serializers
from .models import Post, Tag, Category
from accounts.models import UserProfile
from accounts.serializers import UserProfileSerializer


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'full_name', 'profile_image', 'bio', 'is_premium', 'custom_domain']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class PostSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    total_likes = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'slug', 'title', 'content', 'content_markdown',
            'excerpt', 'cover_image', 'tags', 'category', 'author',
            'views', 'total_likes',
            'is_published', 'created_at', 'updated_at',
            'seo_title', 'seo_description', 'canonical_url'
        ]

    def get_total_likes(self, obj):
        return obj.total_likes()
