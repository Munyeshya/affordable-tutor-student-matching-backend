from django.contrib import admin
from .models import Booking, BookingEvent, Dispute, DisputeDecision

admin.site.register(Booking)
admin.site.register(BookingEvent)
admin.site.register(Dispute)
admin.site.register(DisputeDecision)
