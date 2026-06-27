# Route Access Guide

## Public routes

- `/api/auth/register/`
- `/api/auth/login/`
- `/api/auth/refresh/`
- `/api/tutors/`
- `/api/tutors/<id>/public/`
- `/api/catalog/courses/`
- `/api/catalog/courses/<id>/public/`

## Authenticated student routes

- Bookings creation and booking payments
- Course purchases
- Lesson progress
- Reviews
- Notifications
- Booking dispute creation and dispute history

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
