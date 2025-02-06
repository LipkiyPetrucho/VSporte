from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _

from payment import webhooks

urlpatterns = i18n_patterns(
    path("admin/", admin.site.urls),
    path(_("account/"), include("account.urls")),
    path("social-auth/", include("social_django.urls", namespace="social")),
    path(_("games/"), include("games.urls", namespace="games")),
    path("__debug__/", include("debug_toolbar.urls")),
    path(_("cart/"), include("cart.urls", namespace="cart")),
    path(_("orders/"), include("orders.urls", namespace="orders")),
    path(_("location/"), include("location.urls", namespace="location")),
    path(_("payment/"), include("payment.urls", namespace="payment")),
    path(_("coupons/"), include("coupons.urls", namespace="coupons")),
    path("rosetta/", include("rosetta.urls")),
    prefix_default_language=False,
)

urlpatterns += [
    path("payment/webhook/", webhooks.stripe_webhook, name="stripe_webhook"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
