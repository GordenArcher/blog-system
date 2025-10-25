from django.contrib import admin
from .models import (
    UserProfile,
    Role,
    UserRole,
    AccountVerification,
    AccountVerificationToken,
    PasswordResetToken,
)

# ===============================
# UserProfile Admin
# ===============================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "is_verified",
        "phone_number",
        "website",
        "last_active",
        "created_at",
    )
    list_filter = ("is_verified", "created_at", "last_active")
    search_fields = ("user__username", "phone_number", "email", "address")
    readonly_fields = ("created_at", "updated_at", "last_active")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

# ===============================
# Role Admin
# ===============================
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)
    ordering = ("name",)

# ===============================
# UserRole Admin
# ===============================
@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user_display", "role", "assigned_at")
    list_filter = ("role", "assigned_at")
    search_fields = ("user__user__username", "role__name")
    readonly_fields = ("assigned_at",)
    ordering = ("-assigned_at",)

    def user_display(self, obj):
        return obj.user.user.username
    user_display.short_description = "User"

# ===============================
# AccountVerification Admin
# ===============================
@admin.register(AccountVerification)
class AccountVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user_display",
        "method",
        "status",
        "code",
        "created_at",
        "expires_at",
        "verified_at",
    )
    list_filter = ("status", "method", "created_at")
    search_fields = ("user__user__username", "code", "method", "status")
    readonly_fields = ("created_at", "verified_at")
    ordering = ("-created_at",)

    def user_display(self, obj):
        return obj.user.user.username
    user_display.short_description = "User"

# ===============================
# AccountVerificationToken Admin
# ===============================
@admin.register(AccountVerificationToken)
class AccountVerificationTokenAdmin(admin.ModelAdmin):
    list_display = (
        "user_display",
        "purpose",
        "is_used",
        "created_at",
        "expires_at",
    )
    list_filter = ("purpose", "is_used", "created_at")
    search_fields = ("user__user__username", "token")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def user_display(self, obj):
        return obj.user.user.username
    user_display.short_description = "User"

# ===============================
# PasswordResetToken Admin
# ===============================
@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = (
        "user_display",
        "token",
        "is_used",
        "created_at",
        "expires_at",
    )
    list_filter = ("is_used", "created_at")
    search_fields = ("user__user__username", "token")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def user_display(self, obj):
        return obj.user.user.username
    user_display.short_description = "User"
