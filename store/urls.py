from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.home, name='home'),
    path('menu/', views.menu, name='menu'),
    path('menu/<slug:slug>/', views.food_detail, name='food_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<slug:slug>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
    path('order/success/<str:order_number>/', views.order_success, name='order_success'),
    path('order/track/<str:order_number>/', views.order_tracking, name='order_tracking'),
    path('order/detail/<str:order_number>/', views.order_tracking, name='order_detail'),
    path('orders/', views.order_history, name='order_history'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('newsletter/', views.newsletter_signup, name='newsletter_signup'),
]