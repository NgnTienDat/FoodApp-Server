from django.urls import path, include
from . import views
from .admin import admin_site
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('restaurants', views.RestaurantViewSet)
router.register('main_categories', views.MainCategoryViewSet)
router.register('users', views.UserViewSet)
router.register('foods', views.FoodViewSet)
router.register('restaurant_categories', views.RestaurantCategoryViewSet)
router.register('carts', views.CartViewSet)
router.register('sub-cart', views.SubCartViewSet)
router.register('sub-cart-item', views.SubCartItemViewSet)
router.register('my-address', views.MyAddressViewSet)
router.register('order', views.OrderViewSet)
router.register('menus', views.MenuViewSet)
router.register('order-detail', views.OrderDetailViewSet)
router.register('restaurant-address', views.AddressRestaurantViewSet)
router.register('comments', views.CommentViewSet)
router.register('reviews', views.ReviewViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', admin_site.urls),
    path('api/add-to-cart', views.AddItemToCart.as_view()),
    path('search-food/', views.SearchFoodView.as_view()),
    path('restaurant-foods/<int:restaurant_id>/foods/', views.RestaurantFoodsView.as_view(), name='restaurant-foods'),
    path('update-sub-cart-item/', views.UpdateItemToSubCart.as_view(), name='update-sub-cart-item'),
    path('follow-restaurant/<int:restaurant_id>/', views.FollowRestaurantAPIView.as_view(), name='follow-restaurant'),
    path('followed-restaurant/', views.FollowedRestaurantsAPIView.as_view(), name='followed-restaurants'),

]
