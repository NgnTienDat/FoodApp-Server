from venv import create

from django.http import HttpResponse
from rest_framework import viewsets, permissions, status, generics
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from unicodedata import category

from .models import Restaurant, MainCategory, User, Food, Cart, SubCart, SubCartItem, RestaurantCategory

from .serializers import RestaurantSerializer, MainCategorySerializer, UserSerializer, FoodSerializers, \
    RestaurantCategorySerializer, CartSerializer, SubCartItemSerializer, SubCartSerializer, FoodCreateSerializer, \
    CategoryCreateSerializer

from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from .paginators import RestaurantPagination


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView,
                  generics.UpdateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [MultiPartParser, ]

    def get_permissions(self):
        if self.action in ['get_current_user']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(methods=['get'], url_path='current-user', detail=False)
    def get_current_user(self, request):
        return Response(UserSerializer(request.user).data)

    # def get_permissions(self):
    #     if self.action == 'retrieve':
    #         return [permissions.IsAuthenticated()]
    #     return [permissions.AllowAny()]


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

    # 2API lấy danh sách các món ăn và các danh mục món ăn của nhà hàng
    @action(methods=['get'], url_path='foods', detail=True)
    def get_foods(self, request, pk):
        foods = self.get_object().food_set.select_related('category').filter(is_available=True)
        q = request.query_params.get("q")
        if q:
            foods = foods.filter(name__icontains=q)

        page = self.paginate_queryset(foods)
        if page is not None:
            serializer = FoodSerializers(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        return Response(FoodSerializers(foods, many=True, context={'request': request}).data)

    @action(methods=['get'], url_path='categories', detail=True)
    def get_categories(self, request, pk):
        categories = self.get_object().restaurant_categories.filter(active=True)
        q = request.query_params.get("q")
        if q:
            categories = categories.filter(name__icontains=q)
        page = self.paginate_queryset(categories)
        if page is not None:
            s = RestaurantCategorySerializer(page, many=True)
            return self.get_paginated_response(s.data)

        return Response(RestaurantCategorySerializer(categories, many=True).data)

    def get_serializer_class(self):
        if self.action == 'create_food':
            return FoodCreateSerializer
        if self.action == 'create_category':
            return CategoryCreateSerializer
        return RestaurantSerializer  #Do trong viewset của restaurant nên mặc định là c này

    @action(methods=['post'], detail=True, url_path='create_food')
    def create_food(self, request, pk=None):
        restaurant = self.get_object()

        serializer = self.get_serializer(
            data=request.data,
            context={'restaurant': restaurant, 'request': request}
        )

        if serializer.is_valid():
            food = serializer.save(restaurant=restaurant)
            return Response(FoodSerializers(food, context={'request': request}).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=True, url_path='create_category')
    def create_category(self, request, pk=None):
        restaurant = self.get_object() #lấy NH từ pk

        serializer = self.get_serializer(
            data=request.data,
            context={'restaurant': restaurant, 'request': request}
        )

        if serializer.is_valid():
            food = serializer.save(restaurant=restaurant)
            return Response(RestaurantCategorySerializer(food, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FoodViewSet(viewsets.ModelViewSet):
    queryset = Food.objects.filter(is_available=True)
    serializer_class = FoodSerializers
    pagination_class = RestaurantPagination

    def get_queryset(self):
        query = self.queryset

        q = self.request.query_params.get("q")
        if q:
            query = query.filter(name__icontains=q)

        return query

    @action(methods=['post'], detail=True)
    def hide_food(self, request, pk):
        try:
            f = Food.objects.get(pk=pk)
            f.is_available = False
            f.save()
        except Food.DoesNotExits:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(data=FoodSerializers(f, context={'request': request}).data,
                        status=status.HTTP_200_OK)


class RestaurantCategoryViewSet(viewsets.ModelViewSet):
    queryset = RestaurantCategory.objects.filter(active=True)
    serializer_class = RestaurantCategorySerializer
    pagination_class = RestaurantPagination

    @action(methods=['get'], url_path='foods', detail=True)
    def get_foods(self, request, pk):
        foods = self.get_object().food_set.filter(is_available=True)

        return Response(FoodSerializers(foods, many=True).data)

        queryset = self.queryset
        params = self.request.query_params

        name = params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)

        min_price = params.get('min_price')
        max_price = params.get('max_price')
        if min_price and max_price:
            queryset = queryset.filter(price__gte=min_price, price__lte=max_price)

        main_category = params.get('main_category')  # send the name of main category: string
        if main_category:
            queryset = queryset.filter(name__icontains=main_category)

        restaurant = params.get('restaurant')  # send restaurant_name
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
        if self.action in ['get_my_cart']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class SubCartViewSet(viewsets.ModelViewSet):
    serializer_class = SubCartSerializer
    queryset = SubCart.objects.all()


class SubCartItemViewSet(viewsets.ModelViewSet):
    serializer_class = SubCartItemSerializer
    queryset = SubCartItem.objects.all()


class AddItemToCart(APIView):

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        food_id = int(request.data.get('food_id'))
        quantity = int(request.data.get('quantity', 1))
        note = request.data.get('note', '')

        food = get_object_or_404(Food, id=food_id)
        restaurant = food.restaurant
        price = food.price

        cart, created = Cart.objects.get_or_create(user=user)

        sub_cart, created = SubCart.objects.get_or_create(cart=cart, restaurant=restaurant)
        # them hoac cap nhat
        sub_cart_item, created = SubCartItem.objects.get_or_create(
            food=food, sub_cart=sub_cart,
            defaults={'restaurant': restaurant,
                      'quantity': quantity,
                      'price': price,
                      'note': note}
        )
        if not created:
            sub_cart_item.quantity += quantity
            sub_cart_item.price = sub_cart_item.quantity * price
            sub_cart_item.save()

        total_price = sum(item.price for item in sub_cart.sub_cart_items.all())
        sub_cart.total_price += total_price
        sub_cart.save()

        items_number = cart.sub_carts.all().count()
        cart.items_number = items_number
        cart.save()

        return Response({'message':'Thêm thành công!', 'cart': CartSerializer(cart).data}
                        , status = status.HTTP_200_OK)

def index(request):
    return HttpResponse("e-food app")
