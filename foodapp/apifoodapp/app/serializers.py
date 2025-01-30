from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from .models import Restaurant, User, MainCategory, RestaurantCategory, Food, Cart, SubCart, SubCartItem, ServicePeriod, \
    Menu, Order, OrderDetail, RestaurantAddress, MyAddress, Comment, Review


class BaseSerializer(ModelSerializer):
    image = SerializerMethodField(source='image')

    def get_image(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri('/static/%s' % obj.image)


class UserSerializer(ModelSerializer):
    def create(self, validated_data):
        data = validated_data.copy()

        u = User(**data)
        u.set_password(u.password)
        u.save()
        return u

    # def update(self, user, validated_data):
    #     password = validated_data.get('password', None)
    #     if password:
    #         user.set_password(password)
    #     user.save()
    #     return user

    avatar = serializers.ImageField(required=False)
    restaurant_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'username', 'password', 'avatar', 'role', 'restaurant_id']
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

    def get_restaurant_id(self, obj):
        try:
            if obj.restaurants:
                return obj.restaurants.id
        except ObjectDoesNotExist:
            return None


class RestaurantAddressSerializer(serializers.ModelSerializer):
    address_restaurant = serializers.SerializerMethodField()

    class Meta:
        model = RestaurantAddress
        fields = ['id', 'address', 'district', 'city', 'latitude', 'longitude', 'address_restaurant']

    def get_address_restaurant(self, obj):
        return str(obj)


class RestaurantSerializer(ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'address', 'address', 'latitude', 'longitude', 'phone_number', 'owner', 'star_rate',
                  'image', 'active']

    # def create(self, validated_data):
    #     owner_data = validated_data.pop('owner')
    #     u = User.objects.create_user(**owner_data)
    #     restaurant = Restaurant.objects.create(owner=u, **validated_data)
    #     return restaurant


class RestaurantSP(ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'image']


class RestaurantName(ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name']


class RestaurantFollowers(ModelSerializer):
    image = serializers.ImageField(required=False)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'address', 'image', 'is_following']

    def get_is_following(self, obj):
        user = self.context['request'].user
        return obj.followers.filter(id=user.id).exists()


class MainCategorySerializer(ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = MainCategory
        fields = ['id', 'name', 'image']


class RestaurantCategorySerializer(BaseSerializer):
    restaurant = RestaurantSP(read_only=True)

    class Meta:
        model = RestaurantCategory
        fields = ['id', 'name', 'restaurant']


class FoodSerializers(BaseSerializer):
    restaurant = RestaurantSP(read_only=True)
    # category = RestaurantCategorySerializer()
    image = serializers.ImageField(required=False)
    serve_period = serializers.ChoiceField(choices=ServicePeriod.choices)

    class Meta:
        model = Food
        fields = ["id", "name", "price", "description", "image", "category", "restaurant", "is_available",
                  'serve_period', 'star_rate']


class RestaurantSearchSP(ModelSerializer):
    foods = FoodSerializers(many=True)

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'foods']


class SubCartItemSerializer(ModelSerializer):
    food = FoodSerializers()

    class Meta:
        model = SubCartItem
        fields = ['id', 'food', 'sub_cart', 'quantity', 'price', 'note']


class SubCartSerializer(ModelSerializer):
    restaurant = RestaurantSP()
    sub_cart_items = SubCartItemSerializer(many=True)

    class Meta:
        model = SubCart
        fields = ['id', 'cart', 'restaurant', 'total_price', 'total_quantity', 'sub_cart_items']


class FoodODSerializers(BaseSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = Food
        fields = ["id", "name", "price", "image"]


class OrderDetailSerializer(BaseSerializer):
    food = FoodODSerializers()

    class Meta:
        model = OrderDetail
        fields = ['id', 'food', 'order', 'quantity', 'sub_total', 'evaluated']


class OrderSerializer(BaseSerializer):
    order_details = OrderDetailSerializer(many=True)
    restaurant = RestaurantName()

    # user = UserSerializer()

    class Meta:
        model = Order
        fields = ['id', 'user', 'restaurant', 'shipping_address', 'shipping_fee', 'total', 'delivery_status',
                  'order_date', 'order_details']


class PaymentSerializer(ModelSerializer):
    class Meta:
        model = Cart
        fields = ['id', 'user', 'order', 'created_date', 'amount', 'payment_method', 'is_successful']


class CartSerializer(ModelSerializer):
    user = UserSerializer()

    # sub_carts = SubCartSerializer(many=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items_number']


class FoodCreateSerializer(ModelSerializer):
    serve_period = serializers.ChoiceField(choices=ServicePeriod.choices)

    class Meta:
        model = Food
        fields = ["id", "name", "price", "description", "image", "category", "is_available", 'serve_period']

    def validate_category(self, category):
        restaurant = self.context.get('restaurant')
        if not restaurant:
            raise serializers.ValidationError("Restaurant context is required")

        if category.restaurant != restaurant:
            raise serializers.ValidationError("Danh mục này không thuộc về nhà hàng")
        return category


class CategoryCreateSerializer(BaseSerializer):
    class Meta:
        model = RestaurantCategory
        fields = ['id', 'name']


class MyAddressSerializer(BaseSerializer):
    class Meta:
        model = MyAddress
        fields = ['id', 'user', 'receiver_name', 'phone_number', 'address', 'latitude', 'longitude']


class FoodDB(ModelSerializer):
    class Meta:
        model = Food
        fields = ['id', 'name']


class MenuSerializer(ModelSerializer):
    serve_period = serializers.ChoiceField(choices=ServicePeriod.choices)
    restaurant = RestaurantSP(read_only=True)

    # food = FoodDB(many=True)

    class Meta:
        model = Menu
        fields = ['id', 'name', 'restaurant', 'description', 'food', 'serve_period', 'active']


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'content', 'created_date', 'user']


class ReviewSerializer(serializers.ModelSerializer):
    restaurant_comment = CommentSerializer(read_only=True)  # Chỉ đọc thông tin phản hồi của nhà hàng
    # restaurant_comment_id = serializers.PrimaryKeyRelatedField(
    #     queryset=Comment.objects.all(),
    #     source='restaurant_comment',
    #     write_only=True,
    #     required=False
    # )  # Để ghi nhận bình luận nhà hàng qua ID

    class Meta:
        model = Review
        fields = ['id', 'stars', 'user', 'food', 'restaurant', 'customer_comment',
                  'restaurant_comment', 'created_date']




#
# class OrderDetailSerializer(ModelSerializer):
#     food_name = serializers.CharField(source='food.name', read_only=True)
#     class Meta:
#         model = OrderDetail
#         fields = ['id', 'food', 'food_name', 'quantity', 'sub_total', 'order']
#
#
# class OrderSerializer(ModelSerializer):
#     order_details = OrderDetailSerializer(many=True, read_only=True)
#     user_name = serializers.CharField(source='user.username', read_only=True)
#
#     class Meta:
#         model = Order
#         fields = ['id', 'user', 'user_name', 'restaurant', 'order_date', 'shipping_address', 'shipping_fee', 'total',
#                   'delivery_status',
#                   'order_details']
