# Route Access Guide

## Public routes

- `/api/auth/register/`
- `/api/auth/login/`
- `/api/auth/refresh/`
- `/api/tutors/`
- `/api/tutors/<id>/public/`
- `/api/catalog/courses/`
- `/api/catalog/courses/<id>/public/`
- Public tutor search supports affordability filters like `min_rate`, `max_rate`, and `sort`
- Public course search supports affordability filters like `min_price`, `max_price`, and `sort`

## Authenticated user routes

- `/api/auth/me/`

## Authenticated student routes

- Bookings creation and booking payments
- Course purchases
- Lesson progress
- Reviews
- Notifications
- Notification mark-all-read
- Booking dispute creation and dispute history
- Chat threads and booking messages

## Authenticated parent routes

- `/api/parents/me/`
- `/api/parents/students/`
- `/api/parents/dashboard/`
- Parent booking creation on `/api/bookings/create/` using `student_id`
- Parent booking list on `/api/bookings/`
- Parent dispute creation and dispute history

## Tutor setup routes

- `/api/tutors/me/`
- `/api/tutors/me/completion/`
- `/api/tutors/dashboard/`
- `/api/tutors/setup/checklist/`
- `/api/tutors/documents/`
- `/api/tutors/agreement/`
- `/api/tutors/agreement/download/`
- `/api/catalog/tutor-subjects/`
- `/api/availability/`

## Marketplace-ready tutor routes

- `/api/catalog/courses/<id>/submit/`
- `/api/payments/payouts/request/`
- `/api/payments/earnings/`
- booking accept/reject/complete actions

## Tutor draft management routes

- `/api/catalog/my-courses/`
- `/api/catalog/courses/create/`
- `/api/catalog/courses/<id>/`
- `/api/catalog/courses/<course_id>/lessons/`
- `/api/catalog/lessons/<id>/`
- Multipart upload supported for course thumbnails and lesson videos

## Admin routes

- tutor verification decisions
- tutor verification decision history
- course moderation decisions
- course moderation
- payout decisions
- payout decision history
- dispute decisions
- learning impact summary
- analytics
- `/api/analytics/dashboard/`
- `/api/analytics/report/`
- `/api/analytics/my-report/`
