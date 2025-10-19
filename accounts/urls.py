from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.get_profile),
    path('profile/update/', views.update_profile),
    path('roles/', views.get_user_roles),
    path('roles/assign/', views.assign_role),
    path('activity/', views.get_login_activity),
    path('verify/request/', views.request_verification),
    path('verify/confirm/', views.verify_account),
]
