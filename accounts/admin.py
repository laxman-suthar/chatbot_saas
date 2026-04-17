from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import TenantUser


@admin.register(TenantUser)
class TenantUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'company_name', 'plan', 'is_staff', 'created_at']
    list_filter = ['plan', 'is_staff', 'is_active']
    search_fields = ['email', 'username', 'company_name']
    ordering = ['-created_at']

    fieldsets = UserAdmin.fieldsets + (
        ('Tenant Info', {
            'fields': ('company_name', 'plan')
        }),
    )