from django.urls import path

from chats.views import BookingMessageListCreateView, ConversationListView, MessageMarkReadView, UnreadMessageCountView

urlpatterns = [
    path("unread/", UnreadMessageCountView.as_view(), name="chat-unread-count"),
    path("threads/", ConversationListView.as_view(), name="chat-thread-list"),
    path("bookings/<int:booking_id>/messages/", BookingMessageListCreateView.as_view(), name="chat-booking-messages"),
    path("bookings/<int:booking_id>/messages/read/", MessageMarkReadView.as_view(), name="chat-booking-messages-read"),
]
