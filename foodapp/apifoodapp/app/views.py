from django.http import HttpResponse
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from unicodedata import category

from .models import Restaurant, MainCategory, User, Food, Cart, SubCart, SubCartItem
from .serializers import RestaurantSerializer, MainCategorySerializer, UserSerializer, FoodSerializers, \
    RestaurantCategorySerializer, CartSerializer, SubCartItemSerializer, SubCartSerializer
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from .paginators import RestaurantPagination


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView,
                  generics.UpdateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [MultiPartParser, ]

    # def get_permissions(self):
    #     if self.action in ['get_current_user']:
    #         return [permissions.IsAuthenticated()]
    #     return [permissions.AllowAny()]

    @action(methods=['get'], url_path='current-user', detail=False)
    def get_current_user(self, request):
        return Response(UserSerializer(request.user).data)


    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class MainCategoryViewSet(viewsets.ModelViewSet):
    queryset = MainCategory.objects.filter(active=True)
    serializer_class = MainCategorySerializer

    @action(methods=['post'], detail=True, url_path='inactive-main-category', url_name='inactive-main-category')
    def inactive(self, request, pk):
        try:
            c = MainCategory.objects.get(pk=pk)
            c.active = False
            c.save()
        except MainCategory.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(data=MainCategorySerializer(c, context={'request': request}).data,
                        status=status.HTTP_200_OK)


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.filter(active=True)
    serializer_class = RestaurantSerializer
    pagination_class = RestaurantPagination

    # permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        params = self.request.query_params

        name = params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset


    @action(methods=['post'], detail=True, url_path='inactive-restaurant', url_name='inactive-restaurant')
    # /restaurants/{pk}/inactive-restaurant <- url_path
    def inactive(self, request, pk):
        try:
            r = Restaurant.objects.get(pk=pk)
            r.active = False
            r.save()
        except Restaurant.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(data=RestaurantSerializer(r, context={'request': request}).data,
                        status=status.HTTP_200_OK)

    # def get_permissions(self):
    #     if self.action == 'list':
    #         return [permissions.AllowAny()]
    #     return [permissions.IsAuthenticated()]


class FoodViewSet(viewsets.ModelViewSet):
    queryset = Food.objects.filter(is_available=True)
    serializer_class = FoodSerializers

    def get_queryset(self):
        queryset = self.queryset
        params = self.request.query_params

        name =params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)

        min_price = params.get('min_price')
        max_price = params.get('max_price')
        if min_price and max_price:
            queryset = queryset.filter(price__gte=min_price, price__lte=max_price)

        main_category = params.get('main_category') # send the name of main category: string
        if main_category:
            queryset = queryset.filter(name__icontains=main_category)

        restaurant = params.get('restaurant') # send restaurant_name
        if restaurant:
            queryset = queryset.filter(restaurant__name__icontains=restaurant)

        return queryset


class CartViewSet(viewsets.ViewSet, generics.RetrieveAPIView):
    serializer_class = CartSerializer
    queryset = Cart.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    @action(methods=['get'], url_path='my-cart', detail=False)
    def get_my_cart(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"error": "Giỏ hàng không tồn tại."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(CartSerializer(cart).data)



    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    # def retrieve(self, request, **kwargs):
    #     try:
    #         # Lấy giỏ hàng dựa trên user hiện tại
    #         cart = Cart.objects.get(user=request.user)
    #     except Cart.DoesNotExist:
    #         return Response(
    #             {"error": "Giỏ hàng không tồn tại."},
    #             status=status.HTTP_404_NOT_FOUND
    #         )
    #     return Response(CartSerializer(cart).data)


class SubCartViewSet(viewsets.ModelViewSet):
    serializer_class = SubCartSerializer
    queryset = SubCart.objects.all()


class SubCartItemViewSet(viewsets.ModelViewSet):
    serializer_class = SubCartItemSerializer
    queryset = SubCartItem.objects.all()


def index(request):
    return HttpResponse("e-food app")
