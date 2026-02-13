from django.contrib import admin
from .models import TutorProfile, TutorVerification, VerificationDocument

admin.site.register(TutorProfile)
admin.site.register(TutorVerification)
admin.site.register(VerificationDocument)
