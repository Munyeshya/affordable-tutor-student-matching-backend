from django.urls import path

from notifications.views import NotificationListView, NotificationMarkAllReadView, NotificationMarkReadView, NotificationUnreadCountView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread/", NotificationUnreadCountView.as_view(), name="notification-unread-count"),
    path("read-all/", NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
]
