from django.contrib import admin
from django.utils.html import mark_safe
from .models import RestaurantCategory, Cart, Food, Restaurant, User, MainCategory, SubCart, SubCartItem, Menu, Order, \
    OrderDetail


# Register your models here
class FoodAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "price", "category", "restaurant"]
    search_fields = ["name", "price", "category__name"]
    # readonly_fields = ['image_food']

    # def image_food(self, food):
    #     return mark_safe(f"<img src='/static/{food.image.name}' width='200' />")


class RestaurantCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "restaurant"]
    search_fields = ["name"]


class MainCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


class FoodAppAdminSite(admin.AdminSite):
    site_header = 'FOOD APP'


class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'id', 'email', 'is_active', 'role']
    search_fields = ['first_name', 'last_name']


class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'phone_number', 'star_rate', 'owner', 'confirmation_status']
    search_fields = ["name"]
    list_filter = ['confirmation_status']
    actions = ['approve_restaurants']

    def approve_restaurants(self, request, queryset):
        queryset.update(confirmation_status=True)
        self.message_user(request, "Nhà hàng đã được phê duyệt!")

    approve_restaurants.short_description = "Phê duyệt nhà hàng đã chọn"


class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'items_number']


class SubCartAdmin(admin.ModelAdmin):
    list_display = ['id', 'restaurant', 'cart', 'total_price']


class SubCartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'restaurant', 'food', 'sub_cart', 'quantity', 'price', 'note']


class MenuAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'restaurant', "serve_period"]


admin_site = FoodAppAdminSite('myfoodapp')
# admin_site.register(Food, FoodAdmin)
# admin_site.register(RestaurantCategory, RestaurantCategoryAdmin)
# admin_site.register(MainCategory, MainCategoryAdmin)
admin_site.register(User, UserAdmin)
admin_site.register(Restaurant, RestaurantAdmin)
# admin_site.register(Cart, CartAdmin)
# admin_site.register(SubCart, SubCartAdmin)
# admin_site.register(SubCartItem, SubCartItemAdmin)
# admin_site.register(Menu, MenuAdmin)
# admin_site.register(Order, admin.ModelAdmin)
# admin_site.register(OrderDetail, admin.ModelAdmin)
