
from django.urls import path
from .views import *

urlpatterns = [
    path("login/", login),
    path("register/", register_view),
    path("state/", check_authentication)
]