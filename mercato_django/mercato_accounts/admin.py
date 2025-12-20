from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Profile


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Admin configuration for CustomUser
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_verified', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'is_active', 'created_at')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'date_of_birth', 'is_verified', 'verification_token')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('verification_token',)
        return self.readonly_fields


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for Profile
    """
    list_display = ('user', 'city', 'country', 'is_active', 'created_at')
    list_filter = ('is_active', 'country', 'created_at')
    search_fields = ('user__username', 'user__email', 'city', 'country')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Profile Information', {
            'fields': ('profile_image', 'bio', 'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )