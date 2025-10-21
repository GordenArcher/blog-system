
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework import status
from django.db import IntegrityError
from .models import Post, UserProfile, Category, Tag
from blogsystem.handler.responses.error import error_response
from blogsystem.handler.responses.success import success_response
from .serializers import PostSerializer
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
import bleach
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, F, FloatField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_all_posts(request):

    try:
        posts = Post.objects.all().order_by("-created_at")

        serializer = PostSerializer(posts, many=True)

        return success_response("Posts fetched successfully", serializer.data)
    except Exception as e:
        return error_response(str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_post(request):
    """
    Create a new blog post with comprehensive validation and error handling.
    
    Required fields: title, content
    Optional fields: category_id, excerpt, cover_image, tags, is_published, 
                    seo_title, seo_description, canonical_url, content_markdown
    """
    try:
        data = request.data
        
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        
        if not title:
            return error_response("Title is required", status.HTTP_400_BAD_REQUEST)
        
        if not content:
            return error_response("Content is required", status.HTTP_400_BAD_REQUEST)
        
        if len(title) < 5:
            return error_response("Title must be at least 5 characters long", status.HTTP_400_BAD_REQUEST)
        
        if len(title) > 200:
            return error_response("Title cannot exceed 200 characters", status.HTTP_400_BAD_REQUEST)
        
        if len(content) < 50:
            return error_response("Content must be at least 50 characters long", status.HTTP_400_BAD_REQUEST)
        
       
        try:
            author = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return error_response("User profile not found. Please complete your profile.", status.HTTP_404_NOT_FOUND)
        
        category = None
        category_id = data.get("category_id")
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return error_response(f"Category with id {category_id} not found", status.HTTP_404_NOT_FOUND)
        
        cover_image = data.get("cover_image", "").strip()
        if cover_image:
            url_validator = URLValidator()
            try:
                url_validator(cover_image)
            except ValidationError:
                return error_response("Invalid cover image URL", status.HTTP_400_BAD_REQUEST)
        
        canonical_url = data.get("canonical_url", "").strip()
        if canonical_url:
            url_validator = URLValidator()
            try:
                url_validator(canonical_url)
            except ValidationError:
                return error_response("Invalid canonical URL", status.HTTP_400_BAD_REQUEST)
        
        content_markdown = data.get("content_markdown", True)
        if not content_markdown:
            allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                          'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'code', 'pre']
            allowed_attributes = {'a': ['href', 'title'], 'img': ['src', 'alt']}
            content = bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)
        
        # Generate excerpt if not provided
        excerpt = data.get("excerpt", "").strip()
        if not excerpt:
            # Remove HTML tags for excerpt if content is HTML
            clean_content = bleach.clean(content, tags=[], strip=True)
            excerpt = clean_content[:200] + "..." if len(clean_content) > 200 else clean_content
        elif len(excerpt) > 500:
            return error_response("Excerpt cannot exceed 500 characters", status.HTTP_400_BAD_REQUEST)
        
        seo_title = data.get("seo_title", "").strip() or title
        seo_description = data.get("seo_description", "").strip() or excerpt
        
        if len(seo_title) > 255:
            return error_response("SEO title cannot exceed 255 characters", status.HTTP_400_BAD_REQUEST)
        
        if len(seo_description) > 500:
            return error_response("SEO description cannot exceed 500 characters", status.HTTP_400_BAD_REQUEST)
        
        tags_data = data.get("tags", [])
        if not isinstance(tags_data, list):
            return error_response("Tags must be an array", status.HTTP_400_BAD_REQUEST)
        
        if len(tags_data) > 10:
            return error_response("Maximum 10 tags allowed per post", status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            post = Post.objects.create(
                author=author,
                category=category,
                title=title,
                content=content,
                content_markdown=content_markdown,
                excerpt=excerpt,
                cover_image=cover_image or None,
                is_published=data.get("is_published", False),
                seo_title=seo_title,
                seo_description=seo_description,
                canonical_url=canonical_url or None,
            )
            
            tag_objects = []
            for tag_name in tags_data:
                tag_name = tag_name.strip().lower()
                if not tag_name:
                    continue
                if len(tag_name) > 50:
                    return error_response(f"Tag '{tag_name}' exceeds 50 characters", status.HTTP_400_BAD_REQUEST)
                
                tag, created = Tag.objects.get_or_create(name=tag_name)
                tag_objects.append(tag)
            
            if tag_objects:
                post.tags.set(tag_objects)
        
        response_data = {
            "id": str(post.id),
            "slug": post.slug,
            "title": post.title,
        }
        
        return success_response(
            "Post created successfully" if post.is_published else "Post saved as draft",
            response_data,
            status.HTTP_201_CREATED
        )
    
    except IntegrityError as e:
        return error_response(
            "A post with this title already exists. Please choose a different title.",
            status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating post: {str(e)}", exc_info=True)
        
        return error_response(
            "An unexpected error occurred while creating the post. Please try again.",
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_post(request, post_id):
    """
    Update an existing blog post. Only the author can update their post.
    """
    try:
        # Get the post
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return error_response("Post not found", status.HTTP_404_NOT_FOUND)
        
        author = UserProfile.objects.get(user=request.user)
        if post.author != author:
            return error_response("You don't have permission to edit this post", status.HTTP_403_FORBIDDEN)
        
        data = request.data
        
        if "title" in data:
            title = data["title"].strip()
            if not title:
                return error_response("Title cannot be empty", status.HTTP_400_BAD_REQUEST)
            if len(title) < 5 or len(title) > 200:
                return error_response("Title must be between 5 and 200 characters", status.HTTP_400_BAD_REQUEST)
            post.title = title
            
        
        if "content" in data:
            content = data["content"].strip()
            if not content or len(content) < 50:
                return error_response("Content must be at least 50 characters", status.HTTP_400_BAD_REQUEST)
            post.content = content
        
        if "excerpt" in data:
            excerpt = data["excerpt"].strip()
            if len(excerpt) > 500:
                return error_response("Excerpt cannot exceed 500 characters", status.HTTP_400_BAD_REQUEST)
            post.excerpt = excerpt
        
        if "category_id" in data:
            if data["category_id"]:
                try:
                    category = Category.objects.get(id=data["category_id"])
                    post.category = category
                except Category.DoesNotExist:
                    return error_response("Category not found", status.HTTP_404_NOT_FOUND)
            else:
                post.category = None
        
        if "cover_image" in data:
            cover_image = data["cover_image"].strip()
            if cover_image:
                url_validator = URLValidator()
                try:
                    url_validator(cover_image)
                    post.cover_image = cover_image
                except ValidationError:
                    return error_response("Invalid cover image URL", status.HTTP_400_BAD_REQUEST)
            else:
                post.cover_image = None
        
        if "is_published" in data:
            post.is_published = bool(data["is_published"])
        
        if "seo_title" in data:
            post.seo_title = data["seo_title"].strip()
        
        if "seo_description" in data:
            post.seo_description = data["seo_description"].strip()
        
        if "canonical_url" in data:
            canonical_url = data["canonical_url"].strip()
            if canonical_url:
                url_validator = URLValidator()
                try:
                    url_validator(canonical_url)
                    post.canonical_url = canonical_url
                except ValidationError:
                    return error_response("Invalid canonical URL", status.HTTP_400_BAD_REQUEST)
            else:
                post.canonical_url = None
        
        if "tags" in data:
            tags_data = data["tags"]
            if not isinstance(tags_data, list):
                return error_response("Tags must be an array", status.HTTP_400_BAD_REQUEST)
            if len(tags_data) > 10:
                return error_response("Maximum 10 tags allowed", status.HTTP_400_BAD_REQUEST)
            
            tag_objects = []
            for tag_name in tags_data:
                tag_name = tag_name.strip().lower()
                if not tag_name:
                    continue
                if len(tag_name) > 50:
                    return error_response(f"Tag '{tag_name}' exceeds 50 characters", status.HTTP_400_BAD_REQUEST)
                tag, created = Tag.objects.get_or_create(name=tag_name)
                tag_objects.append(tag)
            
            post.tags.set(tag_objects)
        
        post.save()
        
        response_data = {
            "id": str(post.id),
            "slug": post.slug,
            "title": post.title,
            "excerpt": post.excerpt,
            "is_published": post.is_published,
            "updated_at": post.updated_at.isoformat(),
        }
        
        return success_response("Post updated successfully", response_data, status.HTTP_200_OK)
    
    except UserProfile.DoesNotExist:
        return error_response("User profile not found", status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating post: {str(e)}", exc_info=True)
        return error_response("An error occurred while updating the post", status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_post(request, post_id):
    """
        Delete a blog post. Only the author can delete their post.
    """
    try:
        post = Post.objects.get(id=post_id)
        author = UserProfile.objects.get(user=request.user)
        
        if post.author != author:
            return error_response("You don't have permission to delete this post", {}, status.HTTP_403_FORBIDDEN)
        
        post.delete()
        return success_response("Post deleted successfully", None, status.HTTP_200_OK)
    
    except Post.DoesNotExist:
        return error_response("Post not found", status.HTTP_404_NOT_FOUND)
    except UserProfile.DoesNotExist:
        return error_response("User profile not found", status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting post: {str(e)}", exc_info=True)
        return error_response("An error occurred while deleting the post", status.HTTP_500_INTERNAL_SERVER_ERROR)
    


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_post_by_slug(request, slug):
    """
        Get a single post by slug. Increments view count.
        Returns full post details including author, category, tags, and comments count.
    """
    try: 
        post = Post.objects.select_related('author', 'author__user', 'category').prefetch_related('tags', 'likes').get(slug=slug)
        
        if not post.is_published:
            if not request.user.is_authenticated:
                return error_response("Post not found", status.HTTP_404_NOT_FOUND)
            
            author = UserProfile.objects.get(user=request.user)
            if post.author != author:
                return error_response("Post not found", status.HTTP_404_NOT_FOUND)
        
        # Increment view count (only once per session to avoid inflation)
        session_key = f"post_viewed_{post.id}"
        if not request.session.get(session_key):
            post.views += 1
            post.save(update_fields=['views'])
            request.session[session_key] = True
        
        is_liked = False
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                is_liked = post.likes.filter(id=user_profile.id).exists()
            except UserProfile.DoesNotExist:
                pass
        
        response_data = {
            "id": str(post.id),
            "slug": post.slug,
            "title": post.title,
            "content": post.content,
            "content_markdown": post.content_markdown,
            "excerpt": post.excerpt,
            "cover_image": post.cover_image,
            "author": {
                "id": str(post.author.id),
                "username": post.author.user.username,
                "full_name": post.author.user.get_full_name() or post.author.user.username,
                "email": post.author.user.email,
                "bio": getattr(post.author, 'bio', ''),
                "avatar": getattr(post.author, 'avatar', None),
            },
            "category": {
                "id": post.category.id,
                "name": post.category.name,
                "slug": post.category.slug
            } if post.category else None,
            "tags": [{"id": tag.id, "name": tag.name, "slug": tag.slug} for tag in post.tags.all()],
            "views": post.views,
            "likes_count": post.total_likes(),
            "is_liked": is_liked,
            "is_published": post.is_published,
            "created_at": post.created_at.isoformat(),
            "updated_at": post.updated_at.isoformat(),
            "seo": {
                "title": post.seo_title or post.title,
                "description": post.seo_description or post.excerpt,
                "canonical_url": post.canonical_url,
            }
        }
        
        return success_response("Post retrieved successfully", response_data, status.HTTP_200_OK)
    
    except Post.DoesNotExist:
        return error_response("Post not found", status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving post: {str(e)}", exc_info=True)
        return error_response("An error occurred while retrieving the post", status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_post_by_id(request, post_id):
    """
    Get a single post by ID. Similar to get_by_slug but uses UUID.
    """
    try:
        post = Post.objects.select_related('author', 'author__user', 'category').prefetch_related('tags', 'likes').get(id=post_id)
        
        # Only show published posts to non-authors
        if not post.is_published:
            if not request.user.is_authenticated:
                return error_response("Post not found", status.HTTP_404_NOT_FOUND)
            
            author = UserProfile.objects.get(user=request.user)
            if post.author != author:
                return error_response("Post not found", status.HTTP_404_NOT_FOUND)
        
        # Increment view count
        session_key = f"post_viewed_{post.id}"
        if not request.session.get(session_key):
            post.views += 1
            post.save(update_fields=['views'])
            request.session[session_key] = True
        
        # Check if current user liked the post
        is_liked = False
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                is_liked = post.likes.filter(id=user_profile.id).exists()
            except UserProfile.DoesNotExist:
                pass
        
        response_data = {
            "id": str(post.id),
            "slug": post.slug,
            "title": post.title,
            "content": post.content,
            "content_markdown": post.content_markdown,
            "excerpt": post.excerpt,
            "cover_image": post.cover_image,
            "author": {
                "id": str(post.author.id),
                "username": post.author.user.username,
                "full_name": post.author.user.get_full_name() or post.author.user.username,
                "email": post.author.user.email,
                "bio": getattr(post.author, 'bio', ''),
                "avatar": getattr(post.author, 'avatar', None),
            },
            "category": {
                "id": post.category.id,
                "name": post.category.name,
                "slug": post.category.slug
            } if post.category else None,
            "tags": [{"id": tag.id, "name": tag.name, "slug": tag.slug} for tag in post.tags.all()],
            "views": post.views,
            "likes_count": post.total_likes(),
            "is_liked": is_liked,
            "is_published": post.is_published,
            "created_at": post.created_at.isoformat(),
            "updated_at": post.updated_at.isoformat(),
            "seo": {
                "title": post.seo_title or post.title,
                "description": post.seo_description or post.excerpt,
                "canonical_url": post.canonical_url,
            }
        }
        
        return success_response("Post retrieved successfully", response_data, status.HTTP_200_OK)
    
    except Post.DoesNotExist:
        return error_response("Post not found", status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving post: {str(e)}", exc_info=True)
        return error_response("An error occurred while retrieving the post", status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def list_posts(request):
    """
        List all published posts with filtering, search, and pagination.
        
        Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 12, max: 50)
        - category: Filter by category slug
        - tag: Filter by tag slug
        - author: Filter by author username
        - search: Search in title and content
        - sort: Sort by (latest, popular, trending) default: latest
        - published: Filter by published status (admin only)
    """
    try:
        # Get query parameters
        page = request.GET.get('page', 1)
        page_size = min(int(request.GET.get('page_size', 12)), 50)
        category_slug = request.GET.get('category')
        tag_slug = request.GET.get('tag')
        author_username = request.GET.get('author')
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', 'latest')
        published_filter = request.GET.get('published')
        
        if request.user.is_authenticated and published_filter is not None:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                posts = Post.objects.filter(
                    Q(is_published=True) | Q(author=user_profile)
                )
            except UserProfile.DoesNotExist:
                posts = Post.objects.filter(is_published=True)
        else:
            posts = Post.objects.filter(is_published=True)
        
        if category_slug:
            posts = posts.filter(category__slug=category_slug)
        
        if tag_slug:
            posts = posts.filter(tags__slug=tag_slug)
        
        if author_username:
            posts = posts.filter(author__user__username=author_username)
        
        if search_query:
            posts = posts.filter(
                Q(title__icontains=search_query) | 
                Q(content__icontains=search_query) |
                Q(excerpt__icontains=search_query) |
                Q(tags__name__icontains=search_query)
            ).distinct()
        
        if sort_by == 'popular':
            posts = posts.annotate(
                likes_count=Count('post_likes', distinct=True)
            ).order_by('-likes_count', '-views', '-created_at')

        elif sort_by == 'trending':
            one_week_ago = timezone.now() - timedelta(days=7)
            posts = posts.annotate(
                likes_count=Count('post_likes', distinct=True),
                trending_score=ExpressionWrapper(
                    (F('likes_count') * 2) + (F('views') * 0.5),
                    output_field=FloatField()
                )
            ).filter(created_at__gte=one_week_ago).order_by('-trending_score', '-created_at')

        else: 
            posts = posts.order_by('-created_at')
        
        posts = posts.select_related('author', 'author__user', 'category').prefetch_related('tags', 'post_likes')
        
        paginator = Paginator(posts, page_size)
        
        try:
            posts_page = paginator.page(page)
        except PageNotAnInteger:
            posts_page = paginator.page(1)
        except EmptyPage:
            posts_page = paginator.page(paginator.num_pages)
        
        posts_data = []
        for post in posts_page:
            is_liked = False
            if request.user.is_authenticated:
                try:
                    user_profile = UserProfile.objects.get(user=request.user)
                    is_liked = post.likes.filter(id=user_profile.id).exists()
                except UserProfile.DoesNotExist:
                    pass
            
            posts_data.append({
                "id": str(post.id),
                "slug": post.slug,
                "title": post.title,
                "excerpt": post.excerpt,
                "cover_image": post.cover_image,
                "author": {
                    "id": str(post.author.id),
                    "username": post.author.user.username,
                    "full_name": post.author.user.get_full_name() or post.author.user.username,
                    "avatar": getattr(post.author.user, 'profile_image', None),
                },
                "category": {
                    "id": post.category.id,
                    "name": post.category.name,
                    "slug": post.category.slug
                } if post.category else None,
                "tags": [{"id": tag.id, "name": tag.name, "slug": tag.slug} for tag in post.tags.all()[:5]],
                "views": post.views,
                "likes_count": post.total_likes(),
                "is_liked": is_liked,
                "created_at": post.created_at.isoformat(),
                "read_time": f"{max(1, len(post.content.split()) // 200)} min read"
            })
        
        response_data = {
            "posts": posts_data,
            "pagination": {
                "current_page": posts_page.number,
                "total_pages": paginator.num_pages,
                "total_posts": paginator.count,
                "page_size": page_size,
                "has_next": posts_page.has_next(),
                "has_previous": posts_page.has_previous(),
            },
            "filters_applied": {
                "category": category_slug,
                "tag": tag_slug,
                "author": author_username,
                "search": search_query,
                "sort": sort_by
            }
        }
        
        return success_response("Posts retrieved successfully", response_data, status.HTTP_200_OK)
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error listing posts: {str(e)}", exc_info=True)
        return error_response("An error occurred while retrieving posts", {"details": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user_posts(request):
    """
        Get all posts by the authenticated user (including drafts).
        Supports pagination and filtering by published status.
    """
    try:
        author = UserProfile.objects.get(user=request.user)
        
        page = request.GET.get('page', 1)
        page_size = min(int(request.GET.get('page_size', 10)), 50)
        published_filter = request.GET.get('published')
        
        posts = Post.objects.filter(author=author)
        
        if published_filter is not None:
            is_published = published_filter.lower() in ['true', '1', 'yes']
            posts = posts.filter(is_published=is_published)
        
        posts = posts.select_related('category').prefetch_related('tags', 'likes').order_by('-created_at')
        
        paginator = Paginator(posts, page_size)
        
        try:
            posts_page = paginator.page(page)
        except PageNotAnInteger:
            posts_page = paginator.page(1)
        except EmptyPage:
            posts_page = paginator.page(paginator.num_pages)
        
        posts_data = []
        for post in posts_page:
            posts_data.append({
                "id": str(post.id),
                "slug": post.slug,
                "title": post.title,
                "excerpt": post.excerpt,
                "cover_image": post.cover_image,
                "category": {
                    "id": post.category.id,
                    "name": post.category.name,
                    "slug": post.category.slug
                } if post.category else None,
                "tags": [{"name": tag.name} for tag in post.tags.all()[:5]],
                "views": post.views,
                "likes_count": post.total_likes(),
                "is_published": post.is_published,
                "created_at": post.created_at.isoformat(),
                "updated_at": post.updated_at.isoformat(),
            })
        
        response_data = {
            "posts": posts_data,
            "pagination": {
                "current_page": posts_page.number,
                "total_pages": paginator.num_pages,
                "total_posts": paginator.count,
                "page_size": page_size,
                "has_next": posts_page.has_next(),
                "has_previous": posts_page.has_previous(),
            }
        }
        
        return success_response("User posts retrieved successfully", response_data, status.HTTP_200_OK)
    
    except UserProfile.DoesNotExist:
        return error_response("User profile not found", status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving user posts: {str(e)}", exc_info=True)
        return error_response("An error occurred while retrieving posts", {"details": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)