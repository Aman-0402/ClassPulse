# Smart QR-Based Real-Time Attendance System

## 1. Project Overview

The **Smart QR-Based Real-Time Attendance System** is a web-based attendance management system designed for a single academic subject/class.

The system allows students to register themselves with their academic details and mark their attendance by scanning a dynamically generated QR code displayed by the teacher during class.

Unlike a traditional static QR attendance system, the QR code in this system automatically changes every **15 seconds**. This makes it difficult for students to reuse or share an old QR code.

The teacher can monitor attendance in **real time**. Whenever a student successfully marks attendance, the student's name, CRN, time, and other relevant information immediately appear on the teacher's dashboard.

The system can also identify suspicious activity such as duplicate attendance attempts, expired QR codes, and unusual login/device activity.

---

# 2. Problem Statement

Traditional attendance systems have several limitations:

* Manual attendance takes significant classroom time.
* Students may have to wait while the teacher calls names.
* Maintaining attendance records manually is error-prone.
* Static QR codes can easily be photographed and shared.
* Students may attempt proxy attendance using another student's account.
* Teachers cannot always monitor attendance activity immediately.
* Preparing attendance reports manually requires additional effort.

The proposed system addresses these problems through **dynamic QR codes, authenticated student accounts, automated attendance recording, and real-time monitoring**.

---

# 3. Objectives

The main objectives of the system are:

1. Allow students to register themselves.
2. Maintain a centralized student database.
3. Generate a unique attendance session for every class.
4. Generate a QR code that changes every 15 seconds.
5. Allow students to mark attendance by scanning the QR code.
6. Automatically validate the QR code before recording attendance.
7. Prevent duplicate attendance.
8. Provide real-time attendance information to the teacher.
9. Display instant notifications whenever attendance is marked.
10. Detect suspicious login and attendance activity.
11. Automatically calculate attendance percentages.
12. Provide attendance reports and export functionality.

---

# 4. Scope of the System

The initial version is designed for **one subject and one teacher/class**.

### Included

* Student registration
* Student login
* Teacher login
* Student profile
* Class/session creation
* Dynamic QR generation
* QR scanning
* Attendance validation
* Real-time attendance monitoring
* Attendance history
* Attendance percentage
* Duplicate detection
* Suspicious activity alerts
* Excel/CSV export
* Teacher dashboard

### Not Included in Initial Version

* Multiple subjects
* Multiple teachers
* University-wide attendance management
* Complex timetable management
* Payroll or faculty management

These features can be added in future versions.

---

# 5. User Roles

The system initially contains two primary roles.

## 5.1 Teacher

The teacher can:

* Login
* View registered students
* Start an attendance session
* Generate/display QR code
* Monitor live attendance
* Stop attendance
* View attendance history
* View student attendance percentage
* View suspicious activity
* Export attendance reports

## 5.2 Student

The student can:

* Register
* Login
* View profile
* Scan attendance QR
* View attendance status
* View attendance history
* View attendance percentage

---

# 6. Student Registration

Students register themselves before attending classes.

### Required Information

* Full Name
* CRN Number
* Course
* Semester
* Section
* Email
* Password
* Profile Photo

### Example

```text
Name: Aman Raj
CRN: 22030145
Course: B.Tech CSE
Semester: 5
Section: A
Email: aman@example.com
Password: ********
```

The CRN must be unique.

The system should reject registration if the same CRN already exists.

---

# 7. Authentication

Students and teachers must authenticate before accessing protected functionality.

### Student Login

```text
Email / CRN
Password
       ↓
Authentication
       ↓
Student Dashboard
```

### Teacher Login

```text
Teacher Username
Password
       ↓
Authentication
       ↓
Teacher Dashboard
```

Passwords must never be stored as plain text.

The backend should use secure password hashing.

---

# 8. Attendance Session

The teacher starts an attendance session whenever a class begins.

Example:

```text
Subject:
Artificial Intelligence

Date:
10 August 2026

Start Time:
10:00 AM

Attendance Duration:
5 Minutes

QR Refresh:
Every 15 Seconds
```

When the teacher clicks:

**Start Attendance**

the system creates a unique attendance session.

---

# 9. Dynamic QR Code

This is one of the most important features of the system.

The QR code automatically changes every **15 seconds**.

Example:

```text
10:00:00 - 10:00:15
QR Token A

10:00:15 - 10:00:30
QR Token B

10:00:30 - 10:00:45
QR Token C

10:00:45 - 10:01:00
QR Token D
```

Each QR contains a temporary, server-verifiable token.

The QR should not contain sensitive student information.

---

# 10. QR Validation

When the student scans the QR code, the application sends the token to the backend.

The backend validates:

```text
Is attendance session active?
        ↓
Is QR token valid?
        ↓
Has QR expired?
        ↓
Is student authenticated?
        ↓
Has student already attended?
        ↓
Is the session valid?
        ↓
Mark Attendance
```

If every condition is satisfied:

```text
Attendance Marked Successfully
```

Otherwise:

```text
Invalid or Expired QR
```

---

# 11. QR Expiration

Each QR token should have a short validity period.

Recommended:

**15 seconds**

For example:

```text
QR Generated:
10:00:00

Expires:
10:00:15
```

If a student tries to use the QR at 10:00:17:

```text
❌ QR Code Expired
Please scan the current QR code.
```

---

# 12. Attendance Duration

The teacher can define the attendance window.

Recommended default:

**5 minutes**

Example:

```text
Class Start: 10:00 AM
Attendance Open: 10:00 AM
Attendance Close: 10:05 AM
```

After 10:05 AM:

```text
Attendance Closed
```

The teacher can optionally configure a different duration.

---

# 13. Attendance Marking

Once the QR is successfully validated:

```text
Student
   ↓
Scan QR
   ↓
Server Validation
   ↓
Attendance Record Created
```

The database stores:

```text
Student
Session
Date
Time
Status
Device Information
```

Example:

```text
Aman Raj
CRN: 22030145
Session: AI-2026-08-10-01
Date: 10-08-2026
Time: 10:01:08
Status: Present
```

---

# 14. Duplicate Attendance Prevention

A student can mark attendance only once for a particular class session.

If Aman scans the QR again:

```text
⚠ Attendance Already Marked

You were marked present at
10:01:08 AM.
```

The second request will not create another attendance record.

This should also be enforced at the **database level**, not only through frontend validation.

---

# 15. Real-Time Teacher Dashboard

The teacher should not need to refresh the page.

Whenever a student successfully marks attendance, the dashboard updates automatically.

Example:

```text
------------------------------------------
Artificial Intelligence
Section A

Attendance: 28 / 40

🟢 LIVE
------------------------------------------

Recently Present

✓ Aman Raj       10:01:08
✓ Priya Singh    10:01:15
✓ Rahul Kumar    10:01:22
✓ Neha Sharma    10:01:27
------------------------------------------
```

Recommended implementation:

**WebSockets using Django Channels**

This allows the server to push attendance events directly to the teacher's browser.

---

# 16. Real-Time Notification

Whenever attendance is successfully marked, the teacher receives a notification.

Example:

```text
┌─────────────────────────────┐
│ 🟢 Attendance Marked        │
│                             │
│ Aman Raj                    │
│ CRN: 22030145               │
│ Section: A                  │
│ Time: 10:01:08 AM           │
└─────────────────────────────┘
```

The notification should appear immediately.

---

# 17. Suspicious Activity Detection

The system should also generate warnings when suspicious activity is detected.

### Example 1: Duplicate Scan

```text
🟡 Duplicate Attendance Attempt

Aman Raj has already marked
attendance for this class.
```

### Example 2: Expired QR

```text
🔴 Expired QR Attempt

A student attempted to use
an expired QR code.
```

### Example 3: Multiple Device Login

If the same account is detected on multiple devices:

```text
⚠ Suspicious Login

Account:
Aman Raj

New device detected.
```

The teacher can review the event.

---

# 18. Important Security Consideration

The rotating QR code significantly reduces the usefulness of screenshots and shared QR images, but it **cannot completely prevent proxy attendance**.

For example, someone could photograph the current QR and send it immediately to another person.

Therefore, stronger security can be added later.

### Possible additional security

* Registered device
* College Wi-Fi verification
* Classroom network verification
* GPS/geofencing
* Student photo verification
* Face verification

These should be considered optional layers rather than mandatory features for version 1.

---

# 19. Student Dashboard

The student dashboard should remain simple.

```text
--------------------------------
Welcome, Aman Raj

Attendance
88%

Total Classes: 25
Present: 22
Absent: 3

[ Scan QR ]

Attendance History
--------------------------------
```

The student can see all previous attendance records.

---

# 20. Attendance History

Example:

```text
Date          Subject             Status
---------------------------------------------
01-08-2026    Artificial Intel.   Present
03-08-2026    Artificial Intel.   Present
05-08-2026    Artificial Intel.   Absent
07-08-2026    Artificial Intel.   Present
10-08-2026    Artificial Intel.   Present
```

---

# 21. Attendance Percentage

The system automatically calculates attendance percentage.

Formula:

```text
Attendance % =
(Present Classes / Total Classes) × 100
```

Example:

```text
Present = 18
Total = 20

Attendance =
18 / 20 × 100

= 90%
```

---

# 22. Teacher Analytics

The teacher can see:

### Overall

```text
Total Students: 40
Present: 34
Absent: 6
Attendance Rate: 85%
```

### Student-wise

```text
Aman Raj
Present: 18 / 20
Attendance: 90%

Rahul Kumar
Present: 15 / 20
Attendance: 75%
```

Possible visualizations:

* Attendance percentage
* Present vs absent
* Attendance by date
* Students below required attendance
* Class attendance trend

---

# 23. Attendance Report

The teacher should be able to generate reports.

### Excel

```text
CRN | Name | Section | 01-Aug | 03-Aug | 05-Aug | %
------------------------------------------------------
101 | Aman | A       | P       | P       | A       | 66.6
102 | Rahul| A       | P       | P       | P       | 100
```

Supported export formats:

* XLSX
* CSV
* PDF

---

# 24. Database Design

## Student

```text
Student
---------
id
name
crn
course
semester
section
email
password
photo
created_at
updated_at
```

## Teacher

```text
Teacher
---------
id
name
email
password
created_at
```

## Attendance Session

```text
AttendanceSession
-----------------
id
subject
date
start_time
end_time
status
created_at
```

## QR Token

```text
QRToken
-------
id
session_id
token
created_at
expires_at
```

## Attendance

```text
Attendance
----------
id
student_id
session_id
marked_at
status
ip_address
device_info
```

## Activity Log

```text
ActivityLog
-----------
id
student_id
session_id
activity_type
description
ip_address
device_info
created_at
```

---

# 25. Database Relationships

```text
Teacher
   │
   │ creates
   ▼
Attendance Session
   │
   ├──────────► QR Tokens
   │
   ▼
Attendance
   ▲
   │
Student
```

One student can have many attendance records.

One attendance session can contain attendance records for many students.

---

# 26. Suggested Technology Stack

## Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript
* QR Scanner library

## Backend

* Python
* Django
* Django REST Framework
* Django Channels

## Database

Development:

* SQLite

Production:

* PostgreSQL

## Additional Libraries

* QR Code generation library
* WebSocket support
* Excel export library
* PDF generation library

---

# 27. System Architecture

```text
                 ┌─────────────────┐
                 │     Teacher      │
                 │    Dashboard    │
                 └────────┬────────┘
                          │
                    WebSocket
                          │
                          ▼
┌──────────────┐    ┌───────────────┐
│   Students   │───►│ Django Server │
│ Mobile/Web   │    │               │
└──────────────┘    └───────┬───────┘
                            │
                            ▼
                     ┌────────────┐
                     │ PostgreSQL │
                     └────────────┘
```

---

# 28. Complete Attendance Flow

```text
Student Registration
        ↓
Teacher approves / activates student
        ↓
Student Login
        ↓
Teacher starts class
        ↓
Attendance Session Created
        ↓
QR Code Generated
        ↓
QR changes every 15 seconds
        ↓
Student scans QR
        ↓
Backend validates token
        ↓
Check student authentication
        ↓
Check QR expiration
        ↓
Check duplicate attendance
        ↓
Attendance recorded
        ↓
WebSocket sends event
        ↓
Teacher dashboard updates
        ↓
Notification appears
        ↓
Attendance counter increases
```

---

# 29. Example Classroom Scenario

Suppose there are 40 students.

The teacher starts attendance at:

**10:00 AM**

The system creates:

```text
Session ID:
AI-20260810-001
```

The first QR is valid from:

```text
10:00:00 → 10:00:15
```

Aman scans at:

```text
10:00:08
```

His attendance is recorded.

The teacher immediately sees:

```text
🟢 Aman Raj marked present
10:00:08 AM
```

At 10:00:15, the QR changes.

A student tries to use a screenshot of the previous QR at 10:00:20.

The server responds:

```text
❌ QR Expired
```

The student must scan the current QR.

At 10:05:

```text
Attendance Session Closed
```

The teacher dashboard now shows:

```text
Present: 36
Absent: 4
Attendance Rate: 90%
```

---

# 30. Functional Requirements

### FR-01

The system shall allow students to register.

### FR-02

The system shall prevent duplicate CRN registration.

### FR-03

The system shall authenticate students.

### FR-04

The system shall authenticate the teacher.

### FR-05

The teacher shall be able to start an attendance session.

### FR-06

The system shall generate a unique QR token.

### FR-07

The QR token shall automatically expire after 15 seconds.

### FR-08

The system shall generate a new QR token every 15 seconds.

### FR-09

The system shall validate QR tokens on the server.

### FR-10

The system shall prevent duplicate attendance.

### FR-11

The teacher shall see attendance updates in real time.

### FR-12

The system shall display attendance notifications.

### FR-13

The system shall record suspicious activity.

### FR-14

The system shall calculate attendance percentage.

### FR-15

The teacher shall be able to export attendance reports.

---

# 31. Non-Functional Requirements

### Security

* Passwords must be hashed.
* QR tokens must be unpredictable.
* QR validation must happen on the server.
* Authentication must be required.
* Sensitive information must not be stored inside QR codes.

### Performance

Attendance should be recorded within a few seconds of scanning.

### Availability

The system should remain available throughout the class session.

### Usability

The student attendance process should require only:

```text
Login → Scan → Confirmation
```

### Scalability

Although initially designed for one subject, the architecture should allow additional subjects and classes to be added later.

---

# 32. Version 1 Development Plan

## Phase 1 — Authentication

* Student registration
* Student login
* Teacher login
* Student profile

## Phase 2 — Attendance

* Create class session
* Start attendance
* Generate QR
* QR refresh mechanism
* QR scanning
* Attendance validation

## Phase 3 — Real-Time System

* WebSocket integration
* Live attendance counter
* Live student list
* Popup notifications

## Phase 4 — Security

* Duplicate detection
* QR expiration
* Device information
* Suspicious activity logging

## Phase 5 — Reports

* Attendance history
* Percentage calculation
* Excel export
* PDF export
* Analytics

---

# 33. Future Enhancements

The system can later be expanded into a complete college attendance platform.

Possible additions:

* Multiple subjects
* Multiple teachers
* Multiple departments
* Timetable integration
* Faculty dashboard
* Admin dashboard
* College Wi-Fi validation
* Geofencing
* Face verification
* Mobile application
* Email/SMS notifications
* Low-attendance alerts
* Parent notification
* Advanced attendance analytics

---

# 34. Recommended Final Product

The first production version should focus on **simplicity + security + real-time monitoring**.

### Core Experience

```text
                 TEACHER
                    │
             Start Attendance
                    │
                    ▼
             Dynamic QR Code
             Changes / 15 sec
                    │
                    ▼
                STUDENTS
                    │
                Scan QR
                    │
                    ▼
             Server Validation
                    │
                    ▼
             Attendance Saved
                    │
                    ▼
          Real-Time WebSocket
                    │
                    ▼
            TEACHER DASHBOARD
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
    Live Attendance      Notifications
```

The key idea is that **the QR code itself is not trusted**. The backend decides whether the scan is valid. The rotating QR simply makes sharing old QR codes much less effective.

---
