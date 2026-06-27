from django.contrib import admin
from .models import ParentProfile, ParentStudentLink, StudentProfile

admin.site.register(StudentProfile)
admin.site.register(ParentProfile)
admin.site.register(ParentStudentLink)
