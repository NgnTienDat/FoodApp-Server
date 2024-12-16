from django.contrib import admin
from django.utils.html import mark_safe
from .models import RestaurantCategory, Food, Restaurant, User, MainCategory


# Register your models here
class FoodAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "price", "category"]
    search_fields = ["name", "price", "category__name"]
    readonly_fields = ['image_food']

    def image_food(self, food):
        return mark_safe(f"<img src='/static/{food.image.name}' width='200' />")


class RestaurantCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


class MainCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


class FoodAppAdminSite(admin.AdminSite):
    site_header = 'FOOD APP'


class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'is_active', 'role']
    search_fields = ['first_name', 'last_name']


class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'phone_number', 'star_rate', 'owner']
    search_fields = ["name"]


admin_site = FoodAppAdminSite('myfoodapp')
admin_site.register(Food, FoodAdmin)
admin_site.register(RestaurantCategory, RestaurantCategoryAdmin)
admin_site.register(MainCategory, MainCategoryAdmin)
admin_site.register(User, UserAdmin)
admin_site.register(Restaurant, RestaurantAdmin)
