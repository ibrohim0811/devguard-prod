from django.urls import path

from rest_framework_simplejwt.views import ( 
TokenObtainPairView, TokenRefreshView, TokenBlacklistView
)

from .views import ( 
WebApplicationsListCreateView, WebApplicationsDetailView, 
RegisterCreateAPIView, ProfileRetrieveAPIView,
TransactionListCreateAPIView, TransactionDetailAPIView
)


urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name="refresh_token"),
    path('api/user/logout', TokenBlacklistView.as_view(), name="logout"),
    path('me/webapp/<slug:slug>', WebApplicationsDetailView.as_view(), name="webapp"),
    path('me/webapps/', WebApplicationsListCreateView.as_view(), name="webapps"),
    path('register/', RegisterCreateAPIView.as_view(), name="register"),
    path('me/', ProfileRetrieveAPIView.as_view(), name="me"),
    #payment
    path('transaction-histories/', TransactionListCreateAPIView.as_view(), name="payment"),
    path('transaction-history/<slug:payment_id>', TransactionDetailAPIView.as_view(), name="payment"),
]