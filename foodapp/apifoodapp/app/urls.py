from django.urls import path, include
from . import views
from .admin import admin_site
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register('restaurants', views.RestaurantViewSet)
router.register('main_categories', views.MainCategoryViewSet)
router.register('users', views.UserViewSet)
router.register('foods', views.FoodViewSet)
router.register('carts', views.CartViewSet)
router.register('sub-cart', views.SubCartViewSet)
router.register('sub-cart-item', views.SubCartItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', admin_site.urls)
]
