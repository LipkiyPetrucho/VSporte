from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from location.recommender import Recommender
from .cart import Cart
from .forms import CartAddProductForm
from location.models import Place
from coupons.forms import CouponApplyForm


@require_POST
def cart_add(request, place_id):
    cart = Cart(request)
    place = get_object_or_404(Place, id=place_id)
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(place=place, quantity=cd["quantity"], override_quantity=cd["override"])
    return redirect("cart:cart_detail")


@require_POST
def cart_remove(request, place_id):
    cart = Cart(request)
    place = get_object_or_404(Place, id=place_id)
    cart.remove(place)
    return redirect("cart:cart_detail")


def cart_detail(request):
    cart = Cart(request)
    for item in cart:
        item["update_quantity_form"] = CartAddProductForm(
            initial={"quantity": item["quantity"], "override": True}
        )
    coupon_apply_form = CouponApplyForm()

    r = Recommender()
    cart_places = [item["place"] for item in cart]
    if cart_places:
        recommended_places = r.suggest_places_for(cart_places, max_results=4)
    else:
        recommended_places = []
    return render(
        request,
        "cart/detail.html",
        {
            "cart": cart,
            "coupon_apply_form": coupon_apply_form,
            "recommended_places": recommended_places,
        },
    )
