from tkinter.constants import CASCADE

from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField


class Role(models.TextChoices):
    ADMIN = 'admin'
    CUSTOMER = 'customer'
    RES_USER = 'restaurant-user'


class ServicePeriod(models.TextChoices):
    MORNING = 'Sáng'
    NOON = 'Trưa'
    AFTERNOON = 'Chiều'
    EVENING = 'Tối'


class BaseModel(models.Model):
    name = models.CharField(max_length=100, null=False, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    avatar = CloudinaryField('avatar', null=True)
    is_restaurant_user = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.username}'


class MainCategory(models.Model):
    name = models.CharField(max_length=100, null=False, unique=True)
    image = CloudinaryField('danh mục chính', null=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class RestaurantCategory(models.Model):
    name = models.CharField(max_length=100, null=False, unique=True)
    image = CloudinaryField('image', null=True)
    active = models.BooleanField(default=True)
    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE, related_name="restaurant_categories")

    def __str__(self):
        return self.name


class Restaurant(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    address = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="restaurants")
    star_rate = models.FloatField(null=True)
    active = models.BooleanField(default=True)
    image = CloudinaryField('image', null=True)
    followers = models.ManyToManyField(User, related_name='following_restaurants')

    def __str__(self):
        return self.name


class Food(models.Model):
    name = models.CharField(max_length=100, null=False)
    price = models.FloatField(null=False)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(RestaurantCategory, on_delete=models.SET_NULL, null=True)
    image = CloudinaryField('image', null=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="foods")
    is_available = models.BooleanField(default=True)
    serve_period = models.CharField(max_length=20, choices=ServicePeriod.choices, null=True, blank=True)
    available_start = models.TimeField(null=True, blank=True)
    available_end = models.TimeField(null=True, blank=True)
    star_rate = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name


class Review(models.Model):
    comment = models.TextField(null=True, blank=True)
    stars = models.IntegerField(default=5)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_review')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, null=False, related_name='food_reviews')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=False, related_name='restaurant_reviews')
    created_date = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f'{self.user}: {self.comment}'



class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_cart')
    items_number = models.IntegerField(default=0)


class SubCart(models.Model):
    cart = models.ForeignKey(Cart, related_name='sub_carts', on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='sub_carts')
    total_price = models.FloatField(default=0)


class SubCartItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='sub_cart_items')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, null=False, related_name='sub_cart_items')
    sub_cart = models.ForeignKey(SubCart, on_delete=models.CASCADE, related_name='sub_cart_items')
    quantity = models.IntegerField(default=1)
    price = models.FloatField(default=0, null=False) # tự động tính quantity * food.price
    note = models.TextField()




