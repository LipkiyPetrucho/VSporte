from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from payment import webhooks

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("account.urls")),
    path("social-auth/", include("social_django.urls", namespace="social")),
    path("games/", include("games.urls", namespace="games")),
    path("location/", include("location.urls", namespace="location")),
    path("cart/", include("cart.urls", namespace="cart")),
    path("orders/", include("orders.urls", namespace="orders")),
    path("payment/", include("payment.urls", namespace="payment")),
    path("coupons/", include("coupons.urls", namespace="coupons")),
    path("notifications/", include("notifications.urls", namespace="notifications")),
    path("__debug__/", include("debug_toolbar.urls")),
]

urlpatterns += [
    path("payment/webhook/", webhooks.stripe_webhook, name="stripe_webhook"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
