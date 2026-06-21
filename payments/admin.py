from django.contrib import admin
from .models import CoursePurchase, LessonProgress, Payment, Payout, TutorWalletLedger

admin.site.register(Payment)
admin.site.register(TutorWalletLedger)
admin.site.register(Payout)
admin.site.register(CoursePurchase)
admin.site.register(LessonProgress)
