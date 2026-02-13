from django.contrib import admin
from .models import Payment, TutorWalletLedger, Payout

admin.site.register(Payment)
admin.site.register(TutorWalletLedger)
admin.site.register(Payout)
