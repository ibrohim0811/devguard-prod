from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.db import transaction



from rest_framework.generics import (
    CreateAPIView,
    RetrieveAPIView, RetrieveUpdateAPIView,
    ListCreateAPIView
)

from .serializers import( 
RegisterSerializer, ProfileSerializer, 
WebApplicationsSerializer, TransactionSerializer,

)


from .models import Users, WebApplications, TransactionHistory



@extend_schema(tags=['Register'])
class RegisterCreateAPIView(CreateAPIView):
    queryset = Users.objects.all()
    serializer_class = RegisterSerializer



@extend_schema(tags=['user/Profile'])
class ProfileRetrieveAPIView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    


@extend_schema(tags=['user/webapps'])
class WebApplicationsListCreateView(ListCreateAPIView):
    serializer_class = WebApplicationsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WebApplications.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



@extend_schema(tags=['user/webapps'])
class WebApplicationsDetailView(RetrieveAPIView):
    serializer_class = WebApplicationsSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"

    def get_queryset(self):
        return WebApplications.objects.filter(user=self.request.user)
    


@extend_schema(tags=["user/payment"])
class TransactionListCreateAPIView(ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    
@extend_schema(tags=["user/payment"])
class TransactionDetailAPIView(RetrieveAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "payment_id" 
    lookup_url_kwarg = "payment_id"

    def get_queryset(self):
        return TransactionHistory.objects.filter(user=self.request.user)
