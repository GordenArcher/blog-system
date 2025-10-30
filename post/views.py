import random
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework import status
from django.db import IntegrityError
from .models import Post, UserProfile, Category, Tag
from blogsystem.handler.responses.error import error_response
from blogsystem.handler.responses.success import success_response
from .serializers import PostSerializer, CategorySerializer
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
import bleach
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count, F, FloatField, ExpressionWrapper
from django.utils import timezone
from datetime import timedelta
from handlers.utils.cache_utils import get_or_set_cache, set_cached_data, get_cached_data
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_cookie


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_all_posts(request):
    try:
        cache_key = "all_posts"
        cached_data = get_cached_data(cache_key)

        if cached_data:
            return success_response("Posts fetched successfully (cached)", cached_data)

        posts = Post.objects.filter(is_published=True).order_by("-created_at")
        serializer = PostSerializer(posts, many=True, context={"request": request})
        data = serializer.data

        set_cached_data(cache_key, data, 60 * 60 * 24 * 30)

        return success_response("Posts fetched successfully", data)
    
    except Exception as e:
        return error_response("An error occurred", str(e), status.HTTP_500_INTERNAL_SERVER_ERROR)



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
            return error_response("Title is required", None, status.HTTP_400_BAD_REQUEST)
        
        if not content:
            return error_response("Content is required", None, status.HTTP_400_BAD_REQUEST)
        
        if len(title) < 5:
            return error_response("Title must be at least 5 characters long", None, status.HTTP_400_BAD_REQUEST)
        
        if len(title) > 200:
            return error_response("Title cannot exceed 200 characters", None, status.HTTP_400_BAD_REQUEST)
        
        if len(content) < 50:
            return error_response("Content must be at least 50 characters long", None, status.HTTP_400_BAD_REQUEST)
        
       
        try:
            author = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return error_response("User profile not found. Please complete your profile.", None, status.HTTP_404_NOT_FOUND)
        
        category = None
        category_id = data.get("category_id")
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                return error_response(f"Category with id {category_id} not found", None, status.HTTP_404_NOT_FOUND)
        
        canonical_url = data.get("canonical_url", "").strip()
        if canonical_url:
            url_validator = URLValidator()
            try:
                url_validator(canonical_url)
            except ValidationError:
                return error_response("Invalid canonical URL", None, status.HTTP_400_BAD_REQUEST)
        
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
            return error_response("Excerpt cannot exceed 500 characters", None, status.HTTP_400_BAD_REQUEST)
        
        seo_title = data.get("seo_title", "").strip() or title
        seo_description = data.get("seo_description", "").strip() or excerpt
        
        if len(seo_title) > 255:
            return error_response("SEO title cannot exceed 255 characters", None, status.HTTP_400_BAD_REQUEST)
        
        if len(seo_description) > 500:
            return error_response("SEO description cannot exceed 500 characters", None, status.HTTP_400_BAD_REQUEST)
        
        tags_data = data.get("tags", [])
        if not isinstance(tags_data, list):
            return error_response("Tags must be an array", None, status.HTTP_400_BAD_REQUEST)
        
        if len(tags_data) > 10:
            return error_response("Maximum 10 tags allowed per post", None, status.HTTP_400_BAD_REQUEST)
        
        cover_image = request.FILES.get("cover_image")

        if not cover_image:
            return error_response("No cover Image", {"details":"Cover image not in request"}, status.HTTP_404_NOT_FOUND)
        
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
                    return error_response(f"Tag '{tag_name}' exceeds 50 characters", None, status.HTTP_400_BAD_REQUEST)
                
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
            {"details": str(e)},
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
        
        cover_image = data.FILES.get("cover_image")
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
    Get a single post by slug using PostSerializer,
    with additional dynamic fields like is_liked and views.
    """

    cache_key = f"post:{slug}"
    cached_post = get_cached_data(cache_key)

    # Only use cached data for unauthenticated users (public data)
    if cached_post and not request.user.is_authenticated:
        return success_response("Post retrieved successfully (cached)", cached_post)
    
    try:
        post = (
            Post.objects
            .select_related("author", "author__user", "category")
            .prefetch_related("tags", "post_likes")
            .get(slug=slug)
        )

        if not post.is_published:
            if not request.user.is_authenticated:
                return error_response("Post not found", status.HTTP_404_NOT_FOUND)
            
            author = UserProfile.objects.get(user=request.user)
            if post.author != author:
                return error_response("Post not found", status.HTTP_404_NOT_FOUND)
            

        session_key = f"post_viewed_{post.id}"
        if not request.session.get(session_key):
            post.views += 1
            post.save(update_fields=["views"])
            request.session[session_key] = True

        is_liked = False
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                is_liked = post.post_likes.filter(user=user_profile).exists()
            except UserProfile.DoesNotExist:
                pass

        serializer = PostSerializer(post, context={"request": request})
        data = serializer.data

        data.update({
            "is_liked": is_liked,
            "likes_count": post.total_likes(),
            "views": post.views,
        })

        if post.is_published and not request.user.is_authenticated:
            set_cached_data(cache_key, data, timeout=60 * 60 * 24 * 7)

        return success_response("Post retrieved successfully", data, status.HTTP_200_OK)

    except Post.DoesNotExist:
        return error_response("Post not found", status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving post: {str(e)}", exc_info=True)
        return error_response(
            "An error occurred while retrieving the post",
            {"details": str(e)},
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_post_by_id(request, post_id):
    """
    Get a single post by ID. Similar to get_by_slug but uses UUID.
    """

    cache_key = f"post:{post_id}"
    cached_post = get_cached_data(cache_key)

    # Only use cached data for unauthenticated users (public data)
    if cached_post and not request.user.is_authenticated:
        return success_response("Post retrieved successfully (cached)", cached_post)
    
    try:
        post = Post.objects.select_related('author', 'author__user', 'category').prefetch_related('tags', 'post_likes').get(id=post_id)
        
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
            post.save(update_fields=["views"])
            request.session[session_key] = True

        is_liked = False
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                is_liked = post.post_likes.filter(user=user_profile).exists()
            except UserProfile.DoesNotExist:
                pass

        serializer = PostSerializer(post, context={"request": request})
        data = serializer.data

        data.update({
            "is_liked": is_liked,
            "likes_count": post.total_likes(),
            "views": post.views,
        })

        if post.is_published and not request.user.is_authenticated:
            set_cached_data(cache_key, data, timeout=60 * 60 * 24 * 7)
        
        return success_response("Post retrieved successfully", data, status.HTTP_200_OK)
    
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
        page = request.GET.get('page', 1)
        page_size = min(int(request.GET.get('page_size', 12)), 50)
        category_slug = request.GET.get('category')
        tag_slug = request.GET.get('tag')
        author_username = request.GET.get('author')
        search_query = request.GET.get('search', '').strip()
        sort_by = request.GET.get('sort', 'latest')
        published_filter = request.GET.get('published')

        # Base queryset
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

        # Filtering
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

        # Sorting
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

        # Pagination
        paginator = Paginator(posts, page_size)
        try:
            posts_page = paginator.page(page)
        except PageNotAnInteger:
            posts_page = paginator.page(1)
        except EmptyPage:
            posts_page = paginator.page(paginator.num_pages)

        # Serialize
        serializer = PostSerializer(posts_page, many=True, context={"request": request})
        posts_data = serializer.data

        # Add custom computed fields like 'is_liked' and 'read_time'
        user_profile = None
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
            except UserProfile.DoesNotExist:
                pass

        for post_dict, post_obj in zip(posts_data, posts_page):
            if user_profile:
                post_dict["is_liked"] = post_obj.post_likes.filter(id=user_profile.id).exists()
            else:
                post_dict["is_liked"] = False

            post_dict["read_time"] = f"{max(1, len(post_obj.content.split()) // 200)} min read"

        # Response
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
    Cached per user, page, and filter for 10 minutes.
    """

    try:
        author = UserProfile.objects.get(user=request.user)
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 10)), 50)
        published_filter = request.GET.get('published')

        cache_key = f"user_posts:{author.id}:page:{page}:size:{page_size}:published:{published_filter or 'all'}"
        cached_data = get_cached_data(cache_key)

        if cached_data:
            return success_response("User posts retrieved successfully", cached_data, status.HTTP_200_OK)

        posts = Post.objects.filter(author=author)
        if published_filter is not None:
            is_published = published_filter.lower() in ['true', '1', 'yes']
            posts = posts.filter(is_published=is_published)

        posts = posts.select_related('category').prefetch_related('tags', 'post_likes').order_by('-created_at')

        paginator = Paginator(posts, page_size)
        try:
            posts_page = paginator.page(page)
        except PageNotAnInteger:
            posts_page = paginator.page(1)
        except EmptyPage:
            posts_page = paginator.page(paginator.num_pages)

        serializer = PostSerializer(posts_page, many=True)

        response_data = {
            "posts": serializer.data,
            "pagination": {
                "current_page": posts_page.number,
                "total_pages": paginator.num_pages,
                "total_posts": paginator.count,
                "page_size": page_size,
                "has_next": posts_page.has_next(),
                "has_previous": posts_page.has_previous(),
            }
        }

        set_cached_data(cache_key, response_data, timeout=60 * 10)

        return success_response("User posts retrieved successfully", response_data, status.HTTP_200_OK)

    except UserProfile.DoesNotExist:
        return error_response("User profile not found", status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving user posts: {str(e)}", exc_info=True)
        return error_response("An error occurred while retrieving posts", {"details": str(e)}, status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_categories(request):
    try:

        def fetch_categories():
            category = Category.objects.all()
            serializer = CategorySerializer(category, many=True)
            return serializer.data

        data = get_or_set_cache("all_categories", fetch_categories, timeout=60 * 60 * 24 * 30)  # 30 days

        return success_response("ok", data)

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving categories: {str(e)}", exc_info=True)
        return error_response(
            "An error occurred while retrieving categories",
            {"details": str(e)},
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


        return success_response("ok", data)

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving categories: {str(e)}", exc_info=True)
        return error_response(
            "An error occurred while retrieving categories",
            {"details": str(e)},
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def featured_post(request):
    """
        Returns a random featured post, updated every 5 hours.
    """

    cache_key = "featured_post"
    cached_data = get_cached_data(cache_key)

    # If cached post exists and is still valid
    if cached_data:
        return success_response("ok", cached_data)

    # Otherwise, pick a new featured post
    posts = Post.objects.filter(is_published=True)
    if not posts.exists():
        return error_response("No posts available", None, status.HTTP_404_NOT_FOUND)

    post = random.choice(posts)
    serializer = PostSerializer(post)
    data = serializer.data

    # Cache it for 5 hours (18000 seconds)
    set_cached_data(cache_key, data, timeout=60 * 60 * 5)

    return success_response("ok", data)

# https://www.figma.com/community/file/1225308519419319279/jobpilot-job-portal-figma-ui-template-community
