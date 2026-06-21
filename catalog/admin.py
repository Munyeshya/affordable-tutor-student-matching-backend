from django.contrib import admin
from .models import Course, Lesson, Subject, TutorSubject

admin.site.register(Subject)
admin.site.register(TutorSubject)
admin.site.register(Course)
admin.site.register(Lesson)
