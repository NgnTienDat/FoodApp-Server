from datetime import datetime, timedelta

from django.core.mail import send_mail
from django.db.models import Q

from django.contrib import admin
from django.db.models import Sum, Count
from django.shortcuts import render
from django.urls import path
from django.utils import timezone

# Register your models here


from django.contrib import admin
from django.utils.html import mark_safe
from .models import RestaurantCategory, Cart, Food, Restaurant, User, MainCategory, SubCart, SubCartItem, Menu, Order, \
    OrderDetail


class FoodAppAdminSite(admin.AdminSite):
    site_header = 'Hệ Thống Quản Lý FoodApp'
    index_title = 'Trang chủ'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('reports/', self.admin_view(self.reports_view), name="admin_reports"),
        ]
        return custom_urls + urls

    def reports_view(self, request):
        today = datetime.today()
        report_type = request.GET.get('report_type', 'month')
        selected_month = request.GET.get('month', today.strftime('%Y-%m'))
        selected_quarter = request.GET.get('quarter')
        selected_year = request.GET.get('year', today.year)

        if report_type == 'month':
            start_date_naive = datetime.strptime(selected_month + '-01', '%Y-%m-%d')
            # Chuyển thành datetime có thông tin múi giờ (sử dụng múi giờ hiện tại)
            start_date = timezone.make_aware(start_date_naive, timezone.get_current_timezone())

            # Tính toán end_date dựa trên start_date_naive (có thể chuyển thành aware sau)
            end_date_naive = (
                    start_date_naive.replace(month=start_date_naive.month % 12 + 1, day=1) - timedelta(days=1))
            end_date = timezone.make_aware(end_date_naive, timezone.get_current_timezone())

            print('date start: ', start_date)
            print('date end: ', end_date)
        elif report_type == 'quarter' and selected_quarter:
            start_month = (int(selected_quarter) - 1) * 3 + 1
            start_date = datetime(int(selected_year), start_month, 1)
            end_month = start_month + 2
            end_date = datetime(int(selected_year), end_month, 1).replace(day=1) + timedelta(days=32)
            end_date = end_date.replace(day=1) - timedelta(days=1)  # Cuối quý
        elif report_type == 'year':
            start_date = datetime(int(selected_year), 1, 1)
            end_date = datetime(int(selected_year), 12, 31)
        else:
            start_date = today.replace(day=1)
            end_date = today


        date_filter = Q(restaurant_orders__order_date__gte=start_date) & Q(
            restaurant_orders__order_date__lte=end_date)
        restaurant_stats = Restaurant.objects.annotate(
            sales=Sum('restaurant_orders__total', filter=date_filter, distinct=True),
            total_orders=Count('restaurant_orders', filter= date_filter, distinct=True),
            food_count=Count('foods', distinct=True)
        )

        for restaurant in restaurant_stats:
            print(f"ID: {restaurant.id}")
            print(f"Nhà hàng: {restaurant.name}")
            print(f"Các đơn hàng: {restaurant.restaurant_orders}")
            print(f"Tổng doanh thu (sales): {restaurant.sales}")
            print(f"Tổng số đơn hàng (total_orders): {restaurant.total_orders}")
            print(f"Số lượng món ăn (food_count): {restaurant.food_count}")
            print("-" * 50)


        context = {
            'restaurant_stats': restaurant_stats,
            'report_type': report_type,
            'selected_month': selected_month,
            'selected_quarter': selected_quarter,
            'selected_year': selected_year,
            'current_year': today.year,
            'quarters': [1, 2, 3, 4],
        }
        return render(request, "admin/reports.html", context)


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

        for r in queryset:
            email = r.owner.email
            if email:  # Kiểm tra xem owner có email không
                send_mail(
                    subject="Thông báo phê duyệt nhà hàng của bạn",
                    message=f"""
    Xin chào {r.owner},

    Nhà hàng "{r.name}" của bạn đã được xác thực thành công! 🎉
    Hãy đăng nhập bằng tài khoản và mật khẩu bạn đã đăng ký với chúng tôi.

    Cảm ơn bạn đã tham gia nền tảng của chúng tôi!

    Trân trọng,
    Đội ngũ quản trị.
    """,
                    from_email="lequoctrunggg@gmail.com",
                    recipient_list=[email],
                    fail_silently=False,
                )

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
admin_site.register(Food, FoodAdmin)
admin_site.register(RestaurantCategory, RestaurantCategoryAdmin)
admin_site.register(MainCategory, MainCategoryAdmin)
admin_site.register(User, UserAdmin)
admin_site.register(Restaurant, RestaurantAdmin)
admin_site.register(Cart, CartAdmin)
admin_site.register(SubCart, SubCartAdmin)
admin_site.register(SubCartItem, SubCartItemAdmin)
admin_site.register(Menu, MenuAdmin)
admin_site.register(Order, admin.ModelAdmin)
admin_site.register(OrderDetail, admin.ModelAdmin)
