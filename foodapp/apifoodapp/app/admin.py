from datetime import datetime, timedelta
from django.db.models import Q

from django.contrib import admin
from django.db.models import Sum, Count
from django.shortcuts import render
from django.urls import path
from .models import Restaurant, User


# Register your models here


class FoodAppAdminSite(admin.AdminSite):
    site_header = 'Hệ Thống Quản Lý FoodApp'

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
            start_date = datetime.strptime(selected_month + '-01', '%Y-%m-%d')
            end_date = (start_date.replace(month=start_date.month % 12 + 1, day=1) - timedelta(days=1))
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

        restaurant_stats = Restaurant.objects.annotate(
            sales=Sum('restaurant_orders__total', filter=Q(restaurant_orders__order_date__gte=start_date) & Q(
                restaurant_orders__order_date__lte=end_date)),
            total_orders=Count('restaurant_orders', filter=Q(restaurant_orders__order_date__gte=start_date) & Q(
                restaurant_orders__order_date__lte=end_date)),
            food_count=Count('foods', distinct=True)
        )

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


admin_site = FoodAppAdminSite('myfoodapp')
admin_site.register(User, UserAdmin)
admin_site.register(Restaurant, RestaurantAdmin)
