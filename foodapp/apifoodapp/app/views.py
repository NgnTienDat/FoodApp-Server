from datetime import datetime
import uuid
import hmac
import hashlib
import requests

from django.db import transaction
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from rest_framework import viewsets, permissions, status, generics
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q, Prefetch
from django.core.mail import send_mail
from rest_framework.decorators import action

from .models import Restaurant, MainCategory, User, Food, Cart, SubCart, SubCartItem, RestaurantCategory, ServicePeriod, \
    Menu, Order, OrderDetail, RestaurantAddress, MyAddress, Payment, OrderStatus, PaymentMethod, Comment, Review

from .serializers import RestaurantSerializer, MainCategorySerializer, UserSerializer, FoodSerializers, \
    RestaurantCategorySerializer, CartSerializer, SubCartItemSerializer, SubCartSerializer, FoodCreateSerializer, \
    CategoryCreateSerializer, MenuSerializer, OrderSerializer, OrderDetailSerializer, RestaurantAddressSerializer, \
    MyAddressSerializer, RestaurantFollowers, CommentSerializer, ReviewSerializer

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
    queryset = Restaurant.objects.all()
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
            r.active = not r.active
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
        foods = self.get_object().foods.select_related('category')
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

    @action(methods=['get'], url_path='menus', detail=True)
    def get_menus(self, request, pk):
        menus = self.get_object().menus.filter(active=True)
        q = request.query_params.get("q")
        if q:
            menus = menus.filter(name__icontains=q)
        return Response(MenuSerializer(menus, many=True).data)

    @action(methods=['get'], url_path='orders', detail=True)
    def get_order(self, request, pk):
        restaurant = self.get_object()
        orders = Order.objects.filter(restaurant=restaurant).prefetch_related(
            'order_details__food'
        ).select_related(
            'user', 'restaurant'
        )
        return Response(OrderSerializer(orders, many=True).data)

    @action(methods=['get'], url_path='food_report', detail=True)
    def get_food_report(self, request, pk):
        restaurant = self.get_object()
        food_report = OrderDetail.objects.filter(order__restaurant=restaurant).values('food__name').annotate(
            total_sale=Sum('sub_total'), total_order=Count('food'), order_date=TruncDate('order__order_date'))
        return Response(food_report)

    @action(methods=['get'], url_path='category_report', detail=True)
    def get_category_report(self, request, pk):
        restaurant = self.get_object()
        category_report = OrderDetail.objects.filter(order__restaurant=restaurant).values(
            'food__category__name').annotate(
            total_sale=Sum('sub_total'), total_order=Count('food'), order_date=TruncDate('order__order_date'))
        return Response(category_report)

    def get_serializer_class(self):
        if self.action == 'create_food':
            return FoodCreateSerializer
        if self.action == 'create_category':
            return CategoryCreateSerializer
        if self.action == 'create_menu':
            return MenuSerializer
        return RestaurantSerializer  # Do trong viewset của restaurant nên mặc định là c này

    # gửi mail cho flower khi thêm món ăn
    def send_email(self, restaurant, food):
        followers = restaurant.followers.all()
        emails = [f.email for f in followers if f.email]
        if emails:
            send_mail(
                subject=f"Nhà hàng {restaurant.name} có món ăn mới",
                message=f"""\
                Xin chào,
                Nhà hàng {restaurant.name} vừa thêm món {food.name} vào thực đơn!
                Nhanh tay đặt hàng để thưởng thức món ngon mới nhất!
                Cảm ơn quý khách!
                """,
                from_email='lequoctrunggg@gmail.com',
                recipient_list=emails,
                fail_silently=False,
            )

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
            self.send_email(restaurant, food)
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

    @action(methods=['post'], detail=True, url_path='create_menu')
    def create_menu(self, request, pk=None):
        restaurant = self.get_object()  # lấy NH từ pk để tạo menu nên khi tạo không cần gửi nhà hàng len

        serializer = self.get_serializer(
            data=request.data,
            context={'restaurant': restaurant, 'request': request}
        )
        if serializer.is_valid():
            menu = serializer.save(restaurant=restaurant)
            return Response(MenuSerializer(menu, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FoodViewSet(viewsets.ModelViewSet):
    queryset = Food.objects.all()
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

    @action(methods=['post'], detail=True)
    def set_status_food(self, request, pk):
        try:
            f = Food.objects.get(pk=pk)
            f.is_available = not f.is_available
            f.save()
        except Food.DoesNotExit:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        return Response(data=FoodSerializers(f, context={'request': request}).data,
                        status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True)
    def get_review(self, request, pk):
        reviews = self.get_object().reviews.all()
        return Response(ReviewSerializer(reviews, many=True).data)



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

        print('food name: ', food.name)
        print('quantity: ', quantity)

        cart, created = Cart.objects.get_or_create(user=user)

        sub_cart, created = SubCart.objects.get_or_create(cart=cart, restaurant=restaurant)
        # them hoac cap nhat
        sub_cart_item, created = SubCartItem.objects.get_or_create(
            food=food, sub_cart=sub_cart,
            defaults={'restaurant': restaurant,
                      'quantity': quantity,
                      'price': price * quantity,
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


class MenuViewSet(viewsets.ModelViewSet):
    queryset = Menu.objects.filter(active=True)
    serializer_class = MenuSerializer


class OrderRestaurantViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related(
        'order_details__food'  # Lấy tất cả các `food` liên kết với `order_details`
    ).select_related(
        'user',  # Lấy thông tin `user` trong một truy vấn JOIN
        'restaurant'  # Lấy thông tin `restaurant` trong một truy vấn JOIN
    )
    serializer_class = OrderSerializer


class OrderDetailViewSet(viewsets.ModelViewSet):
    queryset = OrderDetail.objects.select_related(
        'food'
    )
    serializer_class = OrderDetailSerializer


class AddressRestaurantViewSet(viewsets.ModelViewSet):
    queryset = RestaurantAddress.objects.all()
    serializer_class = RestaurantAddressSerializer


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


class MomoPayment(APIView):
    def post(self, request):
        try:

            # Các tham số cơ bản của MoMo
            endpoint = "https://test-payment.momo.vn/v2/gateway/api/create"
            partnerCode = "MOMO"
            accessKey = "F8BBA842ECF85"
            secretKey = "K951B6PE1waDMi640xX08PD3vg6EkVlz"
            redirectUrl = "https://webhook.site/b3088a6a-2d17-4f8d-a383-71389a6c600b"
            ipnUrl = "https://webhook.site/b3088a6a-2d17-4f8d-a383-71389a6c600b"

            # Tham số từ người dùng
            amount = str(request.data.get('amount', '50000'))  # Số tiền
            orderInfo = request.data.get('orderInfo', 'pay with MoMo')
            orderId = str(uuid.uuid4())
            requestId = str(uuid.uuid4())
            requestType = "captureWallet"
            extraData = ""  # pass empty value or Encode base64 JsonString

            # Tạo raw signature
            raw_signature = f"accessKey={accessKey}&amount={amount}&extraData={extraData}&ipnUrl={ipnUrl}" \
                            f"&orderId={orderId}&orderInfo={orderInfo}&partnerCode={partnerCode}" \
                            f"&redirectUrl={redirectUrl}&requestId={requestId}&requestType={requestType}"

            # Ký HMAC SHA256
            h = hmac.new(bytes(secretKey, 'utf-8'), bytes(raw_signature, 'utf-8'), hashlib.sha256)
            signature = h.hexdigest()

            # Dữ liệu gửi tới Momo
            data = {
                'partnerCode': partnerCode,
                'partnerName': "Test",
                'storeId': "MomoTestStore",
                'requestId': requestId,
                'amount': amount,
                'orderId': orderId,
                'orderInfo': orderInfo,
                'redirectUrl': redirectUrl,
                'ipnUrl': ipnUrl,
                'lang': "vi",
                'extraData': extraData,
                'requestType': requestType,
                'signature': signature
            }

            # Gửi yêu cầu tới API Momo
            response = requests.post(endpoint, json=data, headers={'Content-Type': 'application/json'})
            # if response.status_code == 200:
            #     momo_response = response.json()
            #     pay_url = momo_response.get('payUrl')  # URL để thanh toán qua Web
            #     return Response({'payUrl': pay_url}, status=200)
            # else:
            #     return Response(response.json(), status=response.status_code)
            return Response(response.json(), status=response.status_code)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        user = request.user
        delivery_status = request.query_params.get('status')
        orders = Order.objects.filter(user=user)
        filters = Q()

        if delivery_status:
            filters = Q(delivery_status=delivery_status)

        orders = orders.filter(filters).order_by("-id")

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
                if cart.items_number == 0:
                    cart.delete()

                return Response({"message": "Đặt hàng thành công."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class OrderViewSet(viewsets.ModelViewSet):
#     queryset = Order.objects.all()
#     serializer_class = OrderSerializer
#     permission_classes = [permissions.IsAuthenticated]
#
#     def create(self, request, *args, **kwargs):
#         user = request.user
#         sub_cart_id = int(request.data.get('sub_cart_id'))
#         address_id = int(request.data.get('address_id'))
#         shipping_fee = float(request.data.get('shipping_fee'))
#         total = float(request.data.get('total_price'))  # Tổng tiền đã bao gồm phí ship
#         payment_method = request.data.get('payment')
#         is_successful = False
#         momo_response = None
#
#         shipping_address = get_object_or_404(MyAddress, id=address_id)
#         sub_cart = get_object_or_404(SubCart, id=sub_cart_id)
#
#         cart = sub_cart.cart
#
#         # Xử lý thanh toán với MoMo
#         if payment_method == 'momo':
#             endpoint = "https://test-payment.momo.vn/v2/gateway/api/create"
#             partnerCode = "MOMO"
#             accessKey = "F8BBA842ECF85"
#             secretKey = "K951B6PE1waDMi640xX08PD3vg6EkVlz"
#             redirectUrl = "https://webhook.site/b3088a6a-2d17-4f8d-a383-71389a6c600b"
#             ipnUrl = "https://webhook.site/b3088a6a-2d17-4f8d-a383-71389a6c600b"
#
#             # Tạo các tham số cho MoMo
#             orderId = str(uuid.uuid4())
#             requestId = str(uuid.uuid4())
#             orderInfo = "Thanh toán đơn hàng"
#             requestType = "captureWallet"
#             extraData = ""
#
#             raw_signature = f"accessKey={accessKey}&amount={total}&extraData={extraData}&ipnUrl={ipnUrl}" \
#                             f"&orderId={orderId}&orderInfo={orderInfo}&partnerCode={partnerCode}" \
#                             f"&redirectUrl={redirectUrl}&requestId={requestId}&requestType={requestType}"
#
#             # Tạo chữ ký
#             h = hmac.new(bytes(secretKey, 'utf-8'), bytes(raw_signature, 'utf-8'), hashlib.sha256)
#             signature = h.hexdigest()
#
#             # Gửi yêu cầu đến MoMo
#             momo_data = {
#                 'partnerCode': partnerCode,
#                 'partnerName': "Test",
#                 'storeId': "MomoTestStore",
#                 'requestId': requestId,
#                 'amount': str(total),
#                 'orderId': orderId,
#                 'orderInfo': orderInfo,
#                 'redirectUrl': redirectUrl,
#                 'ipnUrl': ipnUrl,
#                 'lang': "vi",
#                 'extraData': extraData,
#                 'requestType': requestType,
#                 'signature': signature
#             }
#
#             try:
#                 momo_response = requests.post(endpoint, json=momo_data, headers={'Content-Type': 'application/json'})
#                 momo_response = momo_response.json()
#
#                 # Kiểm tra trạng thái từ MoMo
#                 if momo_response.get("resultCode") != 0:
#                     return Response({"error": "Thanh toán MoMo thất bại."}, status=status.HTTP_400_BAD_REQUEST)
#
#                 # Nếu thành công, cập nhật trạng thái thanh toán
#                 is_successful = True
#
#             except Exception as e:
#                 return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#         elif payment_method == 'cash':
#             payment_method = PaymentMethod.COD
#         else:
#             return Response({"error": "Phương thức thanh toán không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
#
#         # Tạo đơn hàng
#         try:
#             with transaction.atomic():
#                 order = Order.objects.create(user=user, restaurant=sub_cart.restaurant,
#                                              shipping_address=shipping_address,
#                                              shipping_fee=shipping_fee,
#                                              total=total,
#                                              delivery_status=OrderStatus.PENDING)
#
#                 Payment.objects.create(user=user, order=order,
#                                        created_date=datetime.now,
#                                        amount=total, payment_method=payment_method,
#                                        is_successful=is_successful)
#
#                 for s in sub_cart.sub_cart_items.all():
#                     OrderDetail.objects.create(food=s.food, order=order,
#                                                quantity=s.quantity,
#                                                sub_total=s.price)
#
#                 sub_cart.delete()
#                 cart.items_number -= 1
#
#                 cart.save()
#                 if cart.items_number == 0:
#                     cart.delete()
#
#                 # Nếu thanh toán MoMo, trả về URL redirect cho người dùng
#                 if momo_response:
#                     return Response({
#                         "message": "Đặt hàng thành công.",
#                         "payUrl": momo_response.get("payUrl")  # URL người dùng sẽ chuyển hướng để thanh toán
#                     }, status=status.HTTP_200_OK)
#
#                 return Response({"message": "Đặt hàng thành công."}, status=status.HTTP_200_OK)
#
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FollowRestaurantAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        user = request.user

        if restaurant.followers.filter(id=user.id).exists():
            restaurant.followers.remove(user)
            return Response({"message": "Hủy theo dõi thành công", "following": False}, status=status.HTTP_200_OK)
        else:
            # Nếu chưa theo dõi, thêm vào danh sách
            restaurant.followers.add(user)
            print('fol', restaurant.followers)
            return Response({"message": "Theo dõi thành công", "following": True}, status=status.HTTP_200_OK)

    def get(self, request, restaurant_id):
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        # Sử dụng serializer
        serializer = RestaurantFollowers(restaurant, context={'request': request})

        # Trả về thông tin đã serialize
        return Response(serializer.data)


class FollowedRestaurantsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RestaurantPagination

    def get(self, request):
        user = request.user

        # Lấy danh sách các nhà hàng mà người dùng đang theo dõi
        followed_restaurants = Restaurant.objects.filter(followers=user)

        # Sử dụng serializer để chuyển đổi dữ liệu
        serializer = RestaurantFollowers(followed_restaurants, many=True, context={'request': request})

        # Trả về danh sách nhà hàng đã theo dõi
        return Response(serializer.data, status=status.HTTP_200_OK)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    pagination_class = RestaurantPagination

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        user = request.user
        restaurant_id = request.query_params.get('restaurantId', 0)
        food_id = request.query_params.get('foodId', 0)
        filters = Q()


        if restaurant_id:
            restaurant = get_object_or_404(Restaurant, id=int(restaurant_id))
            filters &= Q(restaurant=restaurant)

        if food_id:
            food = get_object_or_404(Food, id=int(food_id))
            filters &= Q(food=food)

        reviews = queryset.filter(filters).order_by("-id")

        paginated_reviews = self.paginate_queryset(reviews)
        if paginated_reviews is not None:
            serializer = self.get_serializer(paginated_reviews, many=True)
            return self.get_paginated_response(serializer.data)


        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        user = request.user
        customer_comment = request.data.get('customer_comment')
        stars = request.data.get('rate')
        order_detail_id = request.data.get('order_detail_id')

        order_detail = get_object_or_404(OrderDetail, id=order_detail_id)
        food = order_detail.food
        restaurant = food.restaurant

        review = Review.objects.create(user=user, stars=stars, food=food, restaurant=restaurant,
                                       customer_comment=customer_comment)
        order_detail.evaluated = True
        order_detail.save()
        serializer = self.get_serializer(review)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        user = request.user
        restaurant_reply = request.data.get('restaurant_reply')

        if not restaurant_reply:
            return Response({"error": "Phản hồi không được để trống"}, status=status.HTTP_400_BAD_REQUEST)

        restaurant_comment = Comment.objects.create(user=user, content=restaurant_reply)
        review = self.get_object()
        review.restaurant_comment = restaurant_comment
        review.save()

        print(review)
        serializer = self.get_serializer(review, partial=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


def index(request):
    return HttpResponse("e-food app")
