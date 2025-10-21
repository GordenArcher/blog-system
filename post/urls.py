from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_posts),
    path("create/", views.create_post, name="create_post"),
    path("slug/<slug:slug>/", views.get_post_by_slug, ),
    path("update/<slug:slug>/", views.update_post),
    path("delete/<slug:slug>/", views.delete_post),
    path("my-posts/", views.get_user_posts),
]
