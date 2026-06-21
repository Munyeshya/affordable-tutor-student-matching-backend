# Affordable Tutor–Student Matching Platform

## Backend System Specification & Development Guide

---

# 1. Project Vision

The Affordable Tutor–Student Matching Platform is a digital educational marketplace designed to connect students with qualified tutors for both online and physical tutoring sessions.

The platform aims to solve two major challenges:

### Educational Challenge

Many students struggle to find affordable, trustworthy, and qualified tutors. Existing methods rely heavily on referrals, social media, or informal networks, making it difficult to compare tutors, verify qualifications, and schedule lessons efficiently.

### Employment Challenge

Many capable individuals remain unemployed or underemployed despite possessing valuable academic knowledge and teaching skills. These include:

* University students
* Recent graduates
* Retired teachers
* Subject specialists
* Skilled professionals

The platform creates a structured opportunity for these individuals to earn income by offering tutoring services and educational content.

---

# 2. Main Objectives

The platform should:

* Connect students with verified tutors
* Make tutoring affordable
* Improve access to educational support
* Create employment opportunities
* Enable online and physical learning
* Allow tutors to monetize educational content
* Measure learning impact
* Provide transparent reviews and ratings
* Support data-driven educational improvement

---

# 3. User Roles

## Student

Can:

* Register account
* Search tutors
* Book tutoring sessions
* Purchase courses
* Watch lessons
* Take assessments
* Confirm learning progress
* Chat with tutors
* Leave reviews

---

## Tutor

Can:

* Register account
* Create tutor profile
* Upload qualifications
* Add subjects
* Set prices
* Create availability schedules
* Accept bookings
* Create courses
* Upload video lessons
* Monitor student progress
* Earn income

---

## Parent

Can:

* Search tutors
* Book tutors for students
* Monitor progress
* Track learning outcomes

---

## Admin

Can:

* Manage all users
* Verify tutors
* Approve courses
* Resolve disputes
* Monitor platform analytics
* Generate reports
* Measure platform impact

---

# 4. Technology Stack

Backend:

* Python
* Django
* Django REST Framework

Authentication:

* JWT

Database:

* SQLite (Development)
* PostgreSQL (Production)

Storage:

* Local Storage (Development)
* Cloud Storage (Production)

---

# 5. Django App Structure

```bash
apps/
    accounts/
    students/
    tutors/
    subjects/
    bookings/
    payments/
    chats/
    reviews/
    disputes/
    courses/
    analytics/
```

---

# 6. Database Models

---

## User

Authentication model.

Fields:

```text
id
full_name
email
phone
password
role
is_active
is_staff
created_at
updated_at
```

Roles:

```text
student
tutor
parent
admin
```

---

## StudentProfile

```text
id
user_id
gender
academic_level
school_name
location
learning_goals
created_at
updated_at
```

---

## TutorProfile

```text
id
user_id
gender
education_level
qualification_document
bio
experience_years
hourly_rate
location
can_teach_online
can_teach_in_person
verification_status
availability_status
created_at
updated_at
```

Verification status:

```text
pending
approved
rejected
```

---

## Subject

```text
id
name
category
description
created_at
updated_at
```

Examples:

```text
Mathematics
Physics
Biology
Chemistry
English
French
ICT
Economics
```

---

## TutorSubject

```text
id
tutor_id
subject_id
level_taught
price_per_hour
created_at
updated_at
```

---

## TutorAvailability

```text
id
tutor_id
day_of_week
start_time
end_time
is_available
created_at
updated_at
```

---

## Booking

```text
id
student_id
tutor_id
subject_id
session_date
start_time
end_time
learning_mode
location
status
total_price
created_at
updated_at
```

Learning mode:

```text
online
in_person
```

Status:

```text
pending
accepted
rejected
completed
cancelled
```

---

## Payment

```text
id
booking_id
student_id
tutor_id
amount
payment_method
payment_status
transaction_reference
paid_at
created_at
```

Status:

```text
pending
paid
failed
refunded
```

---

## Message

```text
id
sender_id
receiver_id
booking_id
message
is_read
created_at
```

---

## Review

```text
id
booking_id
student_id
tutor_id
rating
comment
created_at
```

Rating:

```text
1 - 5
```

---

## TutorVerification

```text
id
tutor_id
admin_id
status
comment
verified_at
created_at
```

Status:

```text
pending
approved
rejected
```

---

## Dispute

```text
id
booking_id
reported_by
reported_against
reason
status
admin_comment
created_at
resolved_at
```

Status:

```text
open
under_review
resolved
rejected
```

---

# COURSE MARKETPLACE MODULE

---

## Course

```text
id
tutor_id
title
description
subject_id
academic_level
price
thumbnail
status
created_at
updated_at
```

Status:

```text
draft
pending_review
published
rejected
```

---

## Lesson

```text
id
course_id
title
description
video_file
video_url
duration
order_number
is_preview
created_at
updated_at
```

---

## CoursePurchase

```text
id
student_id
course_id
amount
payment_status
transaction_reference
purchased_at
```

---

## LessonProgress

```text
id
student_id
course_id
lesson_id
watched_duration
is_completed
completed_at
updated_at
```

---

# LEARNING IMPACT MODULE

The platform must measure actual educational improvement.

---

## LessonAssessment

Stores assessment questions.

```text
id
lesson_id
question
option_a
option_b
option_c
option_d
correct_answer
marks
created_at
```

---

## StudentAssessmentAttempt

Stores test attempts.

```text
id
student_id
lesson_id
attempt_type
score
total_marks
percentage
submitted_at
```

Attempt type:

```text
pre_test
post_test
```

---

## StudentAssessmentAnswer

```text
id
attempt_id
question_id
selected_answer
is_correct
marks_awarded
```

---

## AssessmentResultConfirmation

Protects against fake tutor claims.

```text
id
student_id
lesson_id
pre_test_attempt_id
post_test_attempt_id
pre_test_score
post_test_score
improvement_percentage
student_confirmation_status
student_comment
confirmed_at
created_at
```

Status:

```text
pending
confirmed
rejected
```

---

# Learning Impact Calculation

Example:

```text
Pre-Test Score = 45%

Post-Test Score = 80%

Improvement = 35%
```

Formula:

```text
Improvement =
Post-Test Percentage -
Pre-Test Percentage
```

---

# Important Rule

Tutors CANNOT:

* Edit assessment results
* Edit student scores
* Edit learning improvement

Students MUST:

* Confirm results

Only confirmed results count toward:

* Tutor performance
* Platform impact reports
* Educational statistics

---

# 7. Tutor Search & Matching

Students can search tutors using:

```text
Subject
Academic Level
Location
Price Range
Availability
Rating
Teaching Mode
Verification Status
```

Only approved tutors should appear publicly.

---

# 8. Booking Workflow

```text
Student Creates Booking
        ↓
Pending
        ↓
Tutor Accepts / Rejects
        ↓
Accepted
        ↓
Completed
        ↓
Review & Rating
```

Alternative:

```text
Pending
    ↓
Cancelled
```

---

# 9. Course Purchase Workflow

```text
Student
     ↓
Browse Courses
     ↓
Purchase Course
     ↓
Access Lessons
     ↓
Take Pre-Test
     ↓
Watch Lessons
     ↓
Take Post-Test
     ↓
Confirm Results
```

---

# 10. Admin Analytics Dashboard

The platform should provide advanced analytics.

---

## User Analytics

Display:

* Total Students
* Total Tutors
* Total Verified Tutors
* Total Parents
* Active Users
* New Registrations

---

## Tutoring Analytics

Display:

* Total Bookings
* Accepted Bookings
* Rejected Bookings
* Completed Sessions
* Cancelled Sessions

---

## Educational Impact Analytics

Display:

* Students Helped
* Average Improvement
* Highest Improvement
* Most Effective Tutors
* Most Effective Subjects
* Verified Learning Outcomes
* Confirmed Improvements
* Rejected Improvements

---

## Course Analytics

Display:

* Total Courses
* Published Courses
* Pending Courses
* Total Lesson Views
* Course Purchases
* Most Purchased Courses
* Most Viewed Lessons

---

## Revenue Analytics

Display:

* Platform Revenue
* Tutor Revenue
* Monthly Revenue
* Top Earning Tutors
* Revenue by Subject

---

## Employment Impact Analytics

This is a key project objective.

Display:

* Tutors Earning Income
* New Tutors Registered
* Verified Tutors
* Tutors Receiving Bookings
* Tutors Selling Courses
* Income Generated Through Platform
* Estimated Number of Unemployed Youth Supported

---

# 11. Permissions

## Student

Can:

* Search Tutors
* Book Tutors
* Purchase Courses
* Take Assessments
* Confirm Results
* Leave Reviews

Cannot:

* Verify Tutors
* Manage Courses
* Access Admin Analytics

---

## Tutor

Can:

* Manage Tutor Profile
* Manage Subjects
* Manage Availability
* Accept Bookings
* Create Courses
* Upload Lessons

Cannot:

* Verify Themselves
* Modify Assessment Results
* Access Platform Analytics

---

## Admin

Can:

* Manage Entire Platform
* Verify Tutors
* Approve Courses
* Resolve Disputes
* Access Analytics
* Generate Reports

---

# 12. Core Business Rules

1. Tutors must be verified before becoming visible.
2. Students can only review completed sessions.
3. One booking can have one review.
4. Tutors can teach multiple subjects.
5. Courses must be approved before publishing.
6. Students must purchase a course before accessing paid lessons.
7. Learning impact must be measured using pre-tests and post-tests.
8. Tutors cannot modify assessment results.
9. Students must confirm learning outcomes.
10. Only confirmed outcomes count in analytics.
11. Admin has full platform control.
12. The platform must continuously support educational access and employment creation.

---

# 13. Development Order

Phase 1

```text
Authentication
Users
Profiles
Subjects
Tutor Verification
```

Phase 2

```text
Availability
Bookings
Reviews
Messaging
```

Phase 3

```text
Course Marketplace
Lesson Upload
Course Purchases
```

Phase 4

```text
Assessments
Learning Impact Tracking
Result Confirmation
```

Phase 5

```text
Admin Analytics
Reports
Employment Impact Dashboard
```

---

# Final Mission Statement

The Affordable Tutor–Student Matching Platform exists to improve access to quality education while simultaneously creating sustainable income opportunities for capable individuals. The platform should not only connect tutors and students but also demonstrate measurable educational impact through verified learning outcomes and provide administrators with comprehensive analytics for continuous improvement and decision-making.
