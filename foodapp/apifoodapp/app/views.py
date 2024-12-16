from django.http import HttpResponse
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response

from .models import Restaurant, MainCategory, User, Food
from .serializers import RestaurantSerializer, MainCategorySerializer, UserSerializer, FoodSerializers, \
    RestaurantCategorySerializer
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

    #
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


def index(request):
    return HttpResponse("e-food app")
