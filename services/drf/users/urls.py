from django.urls import path

from rest_framework_simplejwt.views import ( 
TokenObtainPairView, TokenRefreshView, TokenBlacklistView
)

from .views import ( 
WebApplicationsListCreateView, WebApplicationsDetailView, 
RegisterCreateAPIView, ProfileRetrieveAPIView,
TransactionListCreateAPIView, TransactionDetailAPIView,
checkwebtoken, VerifyOTPAPIView, ResendOTPAPIView,
WebApplicationDeleteBySlugAPIView, CheckWebappPayment,
# StartScanView
)


urlpatterns = [
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name="refresh_token"),
    path('api/user/logout', TokenBlacklistView.as_view(), name="logout"),
    path('me/webapp/<slug:slug>', WebApplicationsDetailView.as_view(), name="webapp"),
    path('me/webapps/', WebApplicationsListCreateView.as_view(), name="webapps"),
    path('register/', RegisterCreateAPIView.as_view(), name="register"),
    path('me/', ProfileRetrieveAPIView.as_view(), name="me"),
    path('me/webapp-delete/<slug:slug>', WebApplicationDeleteBySlugAPIView.as_view(), name="webapp_delete"),
    #payment
    path('transaction-histories/', TransactionListCreateAPIView.as_view(), name="payment"),
    path('transaction-history/<slug:payment_id>', TransactionDetailAPIView.as_view(), name="payment"),
    #webcheck
    path('checkweb/<slug:slug>', checkwebtoken, name="checkwebtoken"),
    #otp
    path('verify-otp/', VerifyOTPAPIView.as_view(), name="verify_otp"),
    path('resend-otp/', ResendOTPAPIView.as_view(), name="resend_otp"),

    #payment
    path('check-payment/', CheckWebappPayment.as_view(), name="check_payment"),

    #scan
    # path('webapp-scan/', StartScanView.as_view(), name="scan")

]