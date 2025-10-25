from django.contrib import admin
from .models import LoginActivity

@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = (
        "user_display",
        "device_name",
        "ip_address",
        "user_agent_short",
        "timestamp",
        "last_active",
        "success",
        "logged_out",
    )
    list_filter = ("success", "logged_out", "timestamp")
    search_fields = (
        "user__user__username",
        "device_name",
        "ip_address",
        "user_agent",
    )
    readonly_fields = (
        "user",
        "device_id",
        "timestamp",
        "last_active",
        "logged_in_at",
        "logged_out_at",
    )
    ordering = ("-timestamp",)
    date_hierarchy = "timestamp"

    def user_display(self, obj):
        return obj.user.user.username if obj.user and obj.user.user else "—"
    user_display.short_description = "User"

    def user_agent_short(self, obj):
        if obj.user_agent:
            return (obj.user_agent[:50] + "...") if len(obj.user_agent) > 50 else obj.user_agent
        return "—"
    user_agent_short.short_description = "User Agent"
