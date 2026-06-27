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

## Tutor setup routes

- `/api/tutors/me/`
- `/api/tutors/documents/`
- `/api/tutors/agreement/`
- `/api/tutors/agreement/download/`
- `/api/catalog/tutor-subjects/`
- `/api/availability/`

## Marketplace-ready tutor routes

- `/api/catalog/my-courses/`
- `/api/catalog/courses/create/`
- `/api/catalog/courses/<id>/`
- `/api/catalog/courses/<id>/submit/`
- `/api/catalog/courses/<course_id>/lessons/`
- `/api/catalog/lessons/<id>/`
- `/api/payments/payouts/request/`
- booking accept/reject/complete actions

## Admin routes

- tutor verification decisions
- course moderation
- payout decisions
- analytics
