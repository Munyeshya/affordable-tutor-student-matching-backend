from django.contrib import admin
from .models import ParentProfile, StudentProfile

admin.site.register(StudentProfile)
admin.site.register(ParentProfile)
