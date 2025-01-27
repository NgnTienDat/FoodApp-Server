from rest_framework import pagination


class RestaurantPagination(pagination.PageNumberPagination):
    page_size = 8

class MySubCartPagination(pagination.PageNumberPagination):
    page_size = 10

