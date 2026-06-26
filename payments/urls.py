from django.urls import path

from payments.views import (
    BookingPaymentCreateView,
    CoursePurchaseCreateView,
    CoursePurchaseListView,
    PaymentListView,
    PayoutDecisionView,
    PayoutListView,
    PayoutRequestView,
    StudentLessonProgressListView,
    StudentLessonProgressUpdateView,
)

urlpatterns = [
    path("bookings/pay/", BookingPaymentCreateView.as_view(), name="booking-payment-create"),
    path("bookings/", PaymentListView.as_view(), name="payment-list"),
    path("course-purchases/", CoursePurchaseListView.as_view(), name="course-purchase-list"),
    path("course-purchases/create/", CoursePurchaseCreateView.as_view(), name="course-purchase-create"),
    path("lesson-progress/", StudentLessonProgressListView.as_view(), name="lesson-progress-list"),
    path("lesson-progress/update/", StudentLessonProgressUpdateView.as_view(), name="lesson-progress-update"),
    path("payouts/", PayoutListView.as_view(), name="payout-list"),
    path("payouts/request/", PayoutRequestView.as_view(), name="payout-request"),
    path("payouts/<int:pk>/decide/", PayoutDecisionView.as_view(), name="payout-decision"),
]
