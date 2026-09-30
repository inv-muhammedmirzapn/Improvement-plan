from django.contrib import admin

from .models import Booking, BookingSeat, Event, OutboxEvent, Payment, ProcessedMessage, Seat

for m in (Event, Seat, Booking, BookingSeat, Payment, OutboxEvent, ProcessedMessage):
    admin.site.register(m)