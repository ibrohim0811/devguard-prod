from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema



from rest_framework.generics import (
    CreateAPIView,
    RetrieveAPIView, RetrieveUpdateAPIView,
    ListCreateAPIView
)

from .serializers import RegisterSerializer, ProfileSerializer, WebApplicationsSerializer



from .models import Users, WebApplications



@extend_schema(tags=['Register'])
class RegisterCreateAPIView(CreateAPIView):
    queryset = Users.objects.all()
    serializer_class = RegisterSerializer

    


@extend_schema(tags=['User/Profile'])
class ProfileRetrieveAPIView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    

@extend_schema(tags=['User/webapps'])
class WebApplicationsListCreateView(ListCreateAPIView):
    serializer_class = WebApplicationsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WebApplications.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=['User/webapps'])
class WebApplicationsDetailView(RetrieveAPIView):
    serializer_class = WebApplicationsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WebApplications.objects.filter(user=self.request.user)
    


