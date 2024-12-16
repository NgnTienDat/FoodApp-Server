from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer

from .models import Restaurant, User, MainCategory, RestaurantCategory, Food


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


class MainCategorySerializer(ModelSerializer):
    image = serializers.ImageField(required=False)

    class Meta:
        model = MainCategory
        fields = ['id', 'name', 'image']


class RestaurantCategorySerializer(BaseSerializer):
    restaurant = RestaurantSerializer()
    image = serializers.ImageField(required=False)
    class Meta:
        model = RestaurantCategory
        fields = ['id', 'name', 'image', 'restaurant']


class FoodSerializers(BaseSerializer):
    restaurant = RestaurantSerializer()
    category = RestaurantCategorySerializer()
    image = serializers.ImageField(required=False)
    class Meta:
        model = Food
        fields = ["id", "name", "price", "description", "image", "category", "restaurant", "is_available"]
