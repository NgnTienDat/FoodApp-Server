from datetime import datetime
from pickle import FALSE

from django.db import transaction
from django.http import HttpResponse
from oauthlib.uri_validate import query
from rest_framework import viewsets, permissions, status, generics
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Prefetch
from sqlalchemy import True_

from .models import Restaurant, MainCategory, User, Food, Cart, SubCart, SubCartItem, RestaurantCategory, ServicePeriod, \
    MyAddress, Order, Payment, OrderStatus, PaymentMethod, OrderDetail

from .serializers import RestaurantSerializer, MainCategorySerializer, UserSerializer, FoodSerializers, \
    RestaurantCategorySerializer, CartSerializer, SubCartItemSerializer, SubCartSerializer, FoodCreateSerializer, \
    CategoryCreateSerializer, MyAddressSerializer, OrderSerializer

from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from .paginators import RestaurantPagination, MySubCartPagination


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
        return RestaurantSerializer  # Do trong viewset của restaurant nên mặc định là c này

    # Chú ý: lúc tạo món ăn avf danh mục thì lấy 2 serializer khác
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
        restaurant = self.get_object()  # lấy NH từ pk

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
    print(ServicePeriod.choices)

    def get_queryset(self):
        queryset = self.queryset
        params = self.request.query_params

        name = params.get('name', '').strip()
        min_price = params.get('min_price')
        max_price = params.get('max_price')
        main_category = params.get('main_category', '').strip()  # send the name of main category: string
        restaurant = params.get('restaurant', '').strip()  # send restaurant_name
        # Sử dụng Q object to combine query conditions
        filters = Q()

        if name:
            # queryset = queryset.filter(name__icontains=name)     .filter() is a query,
            filters &= Q(name__icontains=name)  # instead òf that, use Q() to filter conditions
            # After all, we are only using 1 query for all conditions

        if min_price and max_price:
            filters &= Q(price__gte=min_price, price__lte=max_price)

        if main_category:
            filters &= Q(name__icontains=main_category)

        if restaurant:
            filters &= Q(restaurant__name__icontains=restaurant)

        queryset = queryset.filter(filters)  # 1 query:))
        return queryset

    def perform_create(self, serializer):
        print("Received data:", self.request.data)  # Thêm dòng này
        print("serve_period value:", self.request.data.get('serve_period'))
        super().perform_create(serializer)

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


class CartViewSet(viewsets.ViewSet, generics.DestroyAPIView):
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

    @action(methods=['get'], url_path='sub-carts', detail=False)
    def get_my_sub_cart(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"error": "Giỏ hàng không tồn tại."},
                status=status.HTTP_404_NOT_FOUND
            )

        sub_carts = SubCart.objects.filter(cart=cart)
        paginator = MySubCartPagination()
        paginated_subcarts = paginator.paginate_queryset(sub_carts, request)
        serializer = SubCartSerializer(paginated_subcarts, many=True)

        return paginator.get_paginated_response(serializer.data)

    def get_permissions(self):
        if self.action in ['get_my_cart']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class SubCartViewSet(viewsets.ModelViewSet):
    serializer_class = SubCartSerializer
    queryset = SubCart.objects.all()

    @action(methods=['get'], url_path='restaurant-sub-cart', detail=False)
    def get_sub_cart(self, request):
        restaurant_id = request.query_params.get('restaurantId')
        user_id = request.query_params.get('userId')

        cart = get_object_or_404(Cart, user__id=user_id)
        sub_cart = SubCart.objects.filter(cart__id=cart.id, restaurant__id=restaurant_id).first()

        if not sub_cart:
            return Response({"detail": "Không tìm thấy giỏ hàng"}, status=404)

        return Response(SubCartSerializer(sub_cart).data)

    @action(methods=['post'], url_path='delete-sub-carts', detail=False)
    def delete_multiple(self, request):
        cart_id = request.data.get('cartId')
        items_number = request.data.get('itemsNumber')
        ids = request.data.get('ids', [])

        print(request.data)
        print(cart_id)
        print(items_number)
        print(ids)

        cart = get_object_or_404(Cart, pk=cart_id)

        if ids:
            ids = [int(id) for id in ids]
            SubCart.objects.filter(id__in=ids).delete()

        cart.items_number -= items_number
        cart.save()

        if cart.items_number == 0:
            cart.delete()

        return Response({"message": "Xóa sub cart thành công!"}, status=status.HTTP_200_OK)


class MyAddressViewSet(viewsets.ModelViewSet):
    serializer_class = MyAddressSerializer
    queryset = MyAddress.objects.all()

    @action(methods=['get'], url_path='my-addresses', detail=False)
    def get_my_address(self, request):
        try:
            addresses = MyAddress.objects.filter(user=request.user)
        except MyAddress.DoesNotExist:
            return Response(
                {"error": "Địa chỉ không tồn tại."},
                status=status.HTTP_404_NOT_FOUND
            )

    def create(self, request, *args, **kwargs):
        user = request.user
        address = request.data.get('address')
        latitude = float(request.data.get('latitude'))
        longitude = float(request.data.get('longitude'))
        receiver_name = request.data.get('receiver_name')
        phone_number = request.data.get('phone_number')

        try:
            my_address = MyAddress.objects.create(user=user, address=address, latitude=latitude,
                                                  longitude=longitude, receiver_name=receiver_name,
                                                  phone_number=phone_number)

            return Response({"message": "Thêm địa chỉ thành công!"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubCartItemViewSet(viewsets.ModelViewSet):
    serializer_class = SubCartItemSerializer
    queryset = SubCartItem.objects.all()

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Xác thực và cập nhật dữ liệu
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)


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
            print('sub cart item quantity: ', sub_cart_item.quantity)
            sub_cart_item.price = sub_cart_item.quantity * price
            print('sub cart item price: ', sub_cart_item.price)
            sub_cart_item.save()

        total_price = sum(item.price for item in sub_cart.sub_cart_items.all())
        total_quantity = sum(item.quantity for item in sub_cart.sub_cart_items.all())
        sub_cart.total_price = total_price
        sub_cart.total_quantity = total_quantity
        sub_cart.save()

        items_number = cart.sub_carts.all().count()
        cart.items_number = items_number
        cart.save()

        return Response({'message': 'Thêm thành công!', 'cart': CartSerializer(cart).data}
                        , status=status.HTTP_200_OK)


class UpdateItemToSubCart(APIView):

    def patch(self, request, *args, **kwargs):
        sub_cart_item_id = int(request.data.get('sub_cart_item_id'))
        quantity = int(request.data.get('quantity'))

        sub_cart_item = get_object_or_404(SubCartItem, id=sub_cart_item_id)

        food = sub_cart_item.food
        price = food.price
        sub_cart = sub_cart_item.sub_cart

        sub_cart_item.quantity += quantity
        sub_cart_item.price += quantity * price

        sub_cart.total_quantity += quantity
        sub_cart.total_price += quantity * price

        sub_cart_item.save()
        sub_cart.save()

        return Response({"message": "Cập nhật thành công."}, status=status.HTTP_200_OK)


class SearchFoodView(APIView):
    def get(self, request):

        params = request.query_params

        name = params.get('name', '').strip()
        min_price = params.get('min_price')
        max_price = params.get('max_price')
        main_categories = params.getlist('main_category')  # send the name of main category: string
        restaurant = params.get('restaurant', '').strip()  # send restaurant_name

        food_query = Food.objects.filter(is_available=True)

        filters = Q()

        if name:
            # filters &= Q(name__icontains=name, restaurant__name__icontains=name)
            filters |= Q(name__icontains=name) | Q(restaurant__name__icontains=name)
        if min_price and max_price:
            filters &= Q(price__gte=min_price, price__lte=max_price)

        if main_categories:
            # Duyệt qua từng giá trị trong mảng main_categories
            category_filters = Q()
            for c in main_categories:
                category_filters |= Q(name__icontains=c)  # Hoặc field phù hợp
            filters &= category_filters

        if restaurant:
            filters &= Q(restaurant__name__icontains=restaurant)
            filters |= Q(name__icontains=name) | Q(restaurant__name__icontains=restaurant)

        food_query = food_query.filter(filters)

        # Lấy ra danh sách các nhà hàng có food chứa keyword, mỗi nhà hàng chỉ lấy 2 bản ghi food chứa keyword
        # sử dụng prefetch_related để tối ưu hiệu suất truy vấn, tránh vấn đề queries N+1, lucs này chỉ cần 2 câu query
        restaurants = Restaurant.objects.prefetch_related(
            Prefetch(
                'foods',
                queryset=food_query[:2],
                to_attr='filtered_foods'
            )
        ).filter(foods__in=food_query).distinct()

        response_data = [
            {
                'id': restaurant.id,
                'restaurant': restaurant.name,
                'image': restaurant.image.url if restaurant.image else None,
                'items': [
                    {
                        'id': food.id,
                        'name': food.name,
                        'price': f'{food.price:,.0f}đ',
                        'image': food.image.url if food.image else None,
                    }
                    for food in restaurant.filtered_foods
                ],
            }
            for restaurant in restaurants
        ]
        return Response(response_data, status=status.HTTP_200_OK)


class RestaurantFoodsView(APIView):
    def get(self, request, restaurant_id):
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
            foods = restaurant.foods.filter(is_available=True).all()
            serializer = FoodSerializers(foods, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Restaurant.DoesNotExist:
            return Response({"error": "Restaurant not found"}, status=status.HTTP_404_NOT_FOUND)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        user = request.user
        orders = self.queryset.filter(user=user)

        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        user = request.user
        sub_cart_id = int(request.data.get('sub_cart_id'))
        address_id = int(request.data.get('address_id'))
        # shipping_address = request.data.get('address')
        shipping_fee = float(request.data.get('shipping_fee'))
        total = float(request.data.get('total_price'))  # da bao gom phi ship
        payment_method = request.data.get('payment')
        is_successful = False


        if payment_method == 'cash':
            payment_method = PaymentMethod.COD
        else:
            payment_method = PaymentMethod.MOMO
            is_successful = True

        shipping_address = get_object_or_404(MyAddress, id=address_id)
        sub_cart = get_object_or_404(SubCart, id=sub_cart_id)

        cart = sub_cart.cart

        try:
            with transaction.atomic():
                order = Order.objects.create(user=user, restaurant=sub_cart.restaurant,
                                             shipping_address=shipping_address,
                                             shipping_fee=shipping_fee,
                                             total=total,
                                             delivery_status=OrderStatus.PENDING)

                Payment.objects.create(user=user, order=order,
                                       created_date=datetime.now,
                                       amount=total, payment_method=payment_method,
                                       is_successful=is_successful)

                for s in sub_cart.sub_cart_items.all():
                    OrderDetail.objects.create(food=s.food, order=order,
                                               quantity=s.quantity,
                                               sub_total=s.price)

                sub_cart.delete()
                cart.items_number -= 1

                cart.save()

                return Response({"message": "Đặt hàng thành công."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def index(request):
    return HttpResponse("e-food app")
