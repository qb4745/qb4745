from django.urls import path
from .views import (HomeView,
                    CheckoutView,
                    ItemDetailView,
                    OrderSummaryView,
                    ProductListView,
                    add_to_cart,
                    remove_from_cart,
                    remove_single_item_from_cart,
                    AddCouponView,
                    PaymentView,
                    Nosotrosview,
                    CategoryItemListView,
                    ProfileView)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='core-home'),
    path('nosotros/', Nosotrosview.as_view(), name='core-nosotros'),
    path('checkout/', CheckoutView.as_view(), name='core-checkout'),
    path('products/', CategoryItemListView.as_view(), name='core-products-category'),
    path('profile/', ProfileView.as_view(), name='core-profile'),
    path('product/<slug>/', ItemDetailView.as_view(), name='core-product'),
    path('order-summary/', OrderSummaryView.as_view(), name='core-order-summary'),
    path('add-to-cart/<slug>/', add_to_cart, name='core-add-to-cart'),
    path('add-coupon/', AddCouponView.as_view(), name='core-add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='core-remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='core-remove-single-item-from-cart'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='core-payment'),
]