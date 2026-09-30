from django.urls import path

from . import views

urlpatterns = [
    path("events/<uuid:event_id>/book/", views.BookSeatsView.as_view()),
    path("bookings/<uuid:booking_id>/", views.BookingDetailView.as_view()),
    path("payments/webhook/", views.PaymentWebhookView.as_view()),
    path("payments/<str:reference>/", views.PaymentDetailView.as_view()),
]