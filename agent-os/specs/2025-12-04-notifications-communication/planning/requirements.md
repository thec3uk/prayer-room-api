# Requirements: Phase 4 - Notifications & Communication

## Overview
User engagement and communication features using Celery for email delivery via AWS SES.

## Prerequisites
- Merge branch `task/user-profile-request` into main before implementation
  - Adds `created_by` field linking PrayerPraiseRequest to User
  - Adds UserProfile model with `enable_digest_notifications` and `enable_response_notifications` fields
  - Adds API endpoints for updating user preferences

## Digest Notifications

### Moderator Digest (Hourly)
- **Recipients:** All users in the "staff" group
- **Frequency:** Hourly
- **Content:**
  - New pending prayer requests (awaiting approval)
  - New flagged requests

### User Digest (Daily/Weekly)
- **Recipients:** Users who have opted in via `enable_digest_notifications`
- **Frequency:** Daily and Weekly options (user preference set in Remix app)
- **Content:**
  - Updates/responses to user's own prayer requests
  - Prayer count updates (e.g., "5 people prayed for your request")
- **Eligibility:** Only ChurchSuite-authenticated users (requests linked via `created_by`)

### Email Content Management
- Email content should be easily editable by admins without code changes
- Consider: Django admin-editable templates or a simple EmailTemplate model

## Response Notifications

### Immediate Response Notification
- **Trigger:** When `response_comment` field is populated/updated on a PrayerPraiseRequest
- **Recipient:** The `created_by` user of that request (if they have `enable_response_notifications` enabled)
- **Delivery:** Immediate (not bundled into digest)
- **Eligibility:** Only for requests with a linked ChurchSuite user

## Email Infrastructure

### AWS SES Setup Required
- Configure django-anymail with AWS SES
- AWS Region: eu-west-1 (Ireland) or eu-west-2 (London)
- Tasks:
  - Set up SES in AWS account
  - Verify sending domain
  - Configure django-anymail settings
  - Set up appropriate IAM credentials

### Email Templates
- HTML templates (no existing branding guidelines)
- Simple, clean design appropriate for church/ministry context

## Existing Infrastructure

### Celery
- Already configured in `prayer_room_api/celery.py`
- Uses `CELERY_` prefix for settings
- Auto-discovers tasks from Django apps

### User Preferences API
- Handled in `task/user-profile-request` branch
- `UpdatePreferencesView` accepts `digestNotifications` and `responseNotifications`
- Remix app handles the preferences UI

### Models (from task/user-profile-request branch)
- `PrayerPraiseRequest.created_by` - ForeignKey to User
- `PrayerPraiseRequest.response_comment` - TextField for responses
- `UserProfile.enable_digest_notifications` - Boolean
- `UserProfile.enable_response_notifications` - Boolean

## Webhook Verification

### Scope
- Verify existing outgoing webhook notifications are working
- No new webhook events to add

## Out of Scope
- SMS notifications
- Push notifications
- In-app notification center
- Admin notification management UI (beyond email template editing)
- User preferences UI (handled by Remix app)
- Preferences API endpoints (handled in other branch)

## Visual Assets
- None provided
- HTML email templates to be designed as part of implementation
