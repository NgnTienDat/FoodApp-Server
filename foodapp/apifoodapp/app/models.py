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
    ALLDAY = 'Cả ngày'

    def __str__(self):
        return self.value


class OrderStatus(models.TextChoices):
    PENDING = 'Chờ xác nhận'
    ACCEPT = 'Đã xác nhận'
    DELIVERING = 'Đang giao hàng'
    DELIVERED = 'Đã giao'
    CANCEL = 'Hủy'


class PaymentMethod(models.TextChoices):
    COD = 'Thanh toán tiền mặt'
    MOMO = 'Momo'


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
    name = models.CharField(max_length=100, null=False)

    active = models.BooleanField(default=True)
    restaurant = models.ForeignKey('Restaurant', on_delete=models.CASCADE, related_name="restaurant_categories")

    def __str__(self):
        return self.name


class RestaurantAddress(models.Model):
    address = models.CharField(max_length=100)
    district = models.CharField(max_length=50, null=True)
    city = models.CharField(max_length=50, null=True)
    latitude = models.FloatField()  # Vĩ độ
    longitude = models.FloatField()  # Kinh độ

    def __str__(self):
        return f"{self.address}, {self.district}, {self.city}"


class Restaurant(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    address = models.CharField(max_length=100, null=True)
    latitude = models.FloatField(null=True)  # Vĩ độ
    longitude = models.FloatField(null=True)  # Kinh độ
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="restaurants")
    star_rate = models.FloatField(null=True)
    active = models.BooleanField(default=True)
    image = CloudinaryField('image', null=True)
    followers = models.ManyToManyField(User, related_name='following_restaurants')
    shipping_fee = models.FloatField(max_length=100, null=True)

    def __str__(self):
        return self.name


class Food(models.Model):
    name = models.CharField(max_length=100, null=False)
    price = models.FloatField(null=False)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(RestaurantCategory, on_delete=models.SET_NULL, null=True)
    image = CloudinaryField('image', null=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='foods')
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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='my_cart')
    items_number = models.IntegerField(default=0)


class SubCart(models.Model):
    cart = models.ForeignKey(Cart, related_name='sub_carts', on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='sub_carts')
    total_price = models.FloatField(default=0)
    total_quantity = models.IntegerField(default=0)


class SubCartItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='sub_cart_items')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, null=False, related_name='sub_cart_items')
    sub_cart = models.ForeignKey(SubCart, on_delete=models.CASCADE, related_name='sub_cart_items')
    quantity = models.IntegerField(default=1)
    price = models.FloatField(default=0, null=False)  # tự động tính quantity * food.price
    note = models.TextField()


class MyAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_addresses')
    receiver_name = models.CharField(max_length=100, blank=False, null=True)
    phone_number = models.CharField(max_length=10, blank=True, null=True)

    address = models.TextField(null=False, blank=False)
    latitude = models.FloatField(null=True, blank=False)
    longitude = models.FloatField(null=True, blank=False)

    def __str__(self):
        return f'{self.address}'


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_orders')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, related_name='restaurant_orders')
    shipping_address = models.ForeignKey(MyAddress, on_delete=models.SET_NULL, null=True, related_name='orders')
    shipping_fee = models.FloatField(default=0)
    total = models.FloatField(default=0)
    delivery_status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    order_date = models.DateTimeField(auto_now_add=True, null=True)


class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment_detail')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_payments')
    created_date = models.DateTimeField(auto_now_add=True)
    amount = models.FloatField(default=0)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    is_successful = models.BooleanField(default=False)


class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_details')
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='food_details')
    quantity = models.IntegerField(default=1)
    sub_total = models.FloatField(default=0)

    # def save(self, *args, **kwargs):
    #     self.sub_total = self.food.price * self.quantity
    #     super(OrderDetail, self).save(*args, **kwargs)


class Menu(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, related_name='menus')
    food = models.ManyToManyField(Food, related_name='menu_food')
    name = models.CharField(max_length=100, null=False)
    description = models.TextField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True, null=True)
    updated_date = models.DateTimeField(auto_now=True, null=True)
    active = models.BooleanField(default=True)
    serve_period = models.CharField(max_length=20, choices=ServicePeriod.choices, null=True, blank=True)

    def __str__(self):
        return f'{self.name}'
