from oauthlib.uri_validate import query
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from .models import Restaurant, User, MainCategory, RestaurantCategory, Food, Cart, SubCart, SubCartItem


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

    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'username', 'password', 'avatar', 'role']
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }


class RestaurantSerializer(ModelSerializer):
    owner = UserSerializer()
    image = serializers.ImageField(required=False)

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'address', 'phone_number', 'owner', 'star_rate', 'image']


class RestaurantSP(ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name']


class MainCategorySerializer(ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = MainCategory
        fields = ['id', 'name', 'image']


class RestaurantCategorySerializer(BaseSerializer):
    restaurant = RestaurantSP()

    class Meta:
        model = RestaurantCategory
        fields = ['id', 'name', 'restaurant']


class FoodSerializers(BaseSerializer):
    # restaurant = RestaurantSerializer()
    # category = RestaurantCategorySerializer()
    image = serializers.ImageField(required=False)
    class Meta:
        model = Food
        fields = ["id", "name", "price", "description", "image", "category", "restaurant", "is_available"]


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
        fields = ['id', 'cart', 'restaurant', 'total_price','sub_cart_items']




class CartSerializer(ModelSerializer):
    user = UserSerializer()
    sub_carts = SubCartSerializer(many=True)
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items_number', 'sub_carts']




