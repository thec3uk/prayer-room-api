# Tasks: Notifications & Communication

## Prerequisites

**IMPORTANT**: Before starting any tasks, merge the `task/user-profile-request` branch into main:

```bash
git checkout main
git merge task/user-profile-request
```

This branch provides:
- `PrayerPraiseRequest.created_by` - ForeignKey linking requests to User
- `UserProfile.enable_digest_notifications` - Boolean preference
- `UserProfile.enable_response_notifications` - Boolean preference
- `UpdatePreferencesView` - API endpoint for preferences

---

## Task Groups

### Group 1: AWS SES & Email Infrastructure

- [ ] 1.1 Configure AWS SES in AWS Console (MANUAL - requires user action)
  - Create IAM user with `ses:SendEmail` and `ses:SendRawEmail` permissions
  - Verify sending domain in SES console (eu-west-1 or eu-west-2)
  - Request production access (move out of sandbox)
- [x] 1.2 Install and configure django-anymail
  - Add `django-anymail[amazon-ses]` and `markdown` to pyproject.toml
  - Configure `EMAIL_BACKEND` and `ANYMAIL` settings
- [ ] 1.3 Add environment variables (MANUAL - requires user action)
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_SES_REGION` (eu-west-1 or eu-west-2)
  - `DEFAULT_FROM_EMAIL`
- [ ] 1.4 Test email sending (MANUAL - requires user action)
  - Send test email via Django shell
  - Verify delivery

---

### Group 2: Database Models & Migrations

- [x] 2.1 Create EmailTemplate model
  - Fields: `template_type`, `subject`, `body_markdown`, `is_active`, timestamps
  - Template types: `moderator_digest`, `user_digest`, `response_notification`
- [x] 2.2 Create EmailLog model
  - Fields: `template`, `recipient_email`, `subject`, `status`, `error_message`, `sent_at`, timestamps
  - Status choices: `pending`, `sent`, `failed`
- [x] 2.3 Create and run migrations
- [x] 2.4 Create data migration to seed default templates
  - Moderator digest template
  - User digest template
  - Response notification template

---

### Group 3: Celery Tasks

- [x] 3.1 Create `send_templated_email()` helper function
  - Render markdown to HTML
  - Create EmailLog entry
  - Send via django-anymail
  - Update EmailLog status
- [x] 3.2 Create `send_moderator_digest` task (hourly)
  - Query staff group users
  - Get pending and flagged requests
  - Send digest if there are items
- [x] 3.3 Create `send_user_digest` task (daily/weekly)
  - Query users with `enable_digest_notifications=True`
  - Get responses to their requests since last digest
  - Send personalized digest
- [x] 3.4 Create `send_response_notification` task (immediate)
  - Load prayer request by ID
  - Check user has `enable_response_notifications=True`
  - Send notification email
- [x] 3.5 Configure Celery Beat schedule
  - Moderator digest: hourly (`crontab(minute=0)`)
  - User digest daily: 8am (`crontab(hour=8, minute=0)`)
  - User digest weekly: Monday 8am (`crontab(hour=8, minute=0, day_of_week=1)`)

---

### Group 4: Signal Handlers

- [x] 4.1 Create signal handler for response notifications
  - Listen to `pre_save` on PrayerPraiseRequest
  - Detect when `response_comment` changes from empty to populated
  - Queue `send_response_notification.delay(request.pk)`
- [x] 4.2 Register signal in apps.py `ready()` method

---

### Group 5: Email Template Editor UI

- [x] 5.1 Create `EmailTemplateForm` with HTMX attributes
- [x] 5.2 Create `EmailTemplateView` (Neapolitan CRUDView)
  - List, Detail, Update roles only (no Create/Delete)
  - Staff-only access
  - `get_urls()` includes preview endpoint
  - `render_preview()` for HTMX requests
- [x] 5.3 Define `TEMPLATE_CONTEXT_INFO` with variables and example data per template type
- [x] 5.4 Create list template (`emailtemplate_list.html`)
- [x] 5.5 Create form template (`emailtemplate_form.html`)
  - Side-by-side editor and preview
  - Context variables reference panel
  - HTMX live preview on keyup (300ms debounce)
- [x] 5.6 Add URL routes to urls.py

---

### Group 6: Django Admin

- [x] 6.1 Configure EmailTemplateAdmin
  - List display, filters, fieldsets
  - Link to custom template editor
- [x] 6.2 Configure EmailLogAdmin
  - Read-only (no add/change)
  - List display, filters, search
- [x] 6.3 Create admin changelist template with link to editor

---

### Group 7: Webhook Verification

- [x] 7.1 Review current webhook configuration
- [ ] 7.2 Test webhook triggers (new request, flag, archive) (MANUAL - requires user action)
- [ ] 7.3 Verify Zapier integration receiving events (MANUAL - requires user action)
- [x] 7.4 Document any issues found (None found - configuration is working)

---

### Group 8: Testing

- [x] 8.1 Unit tests for EmailTemplate model
  - Template rendering with context
  - Markdown to HTML conversion
- [x] 8.2 Unit tests for Celery tasks
  - Mock email sending
  - Verify EmailLog creation
  - Test user preference checking
- [x] 8.3 Unit tests for signal handler
  - Verify task queued on response_comment change
  - Verify no task on other field changes
- [x] 8.4 Integration tests for template editor
  - List view renders
  - Edit form saves
  - Preview endpoint returns HTML
- [ ] 8.5 Manual testing checklist (MANUAL - requires user action)
  - [ ] Trigger moderator digest manually
  - [ ] Add response_comment and verify notification
  - [ ] Edit template in editor with live preview
  - [ ] Check emails render correctly in Gmail/Outlook

---

## Execution Order

```
Prerequisites (merge branch)
    │
    ▼
Group 1: AWS SES Setup
    │
    ▼
Group 2: Models & Migrations
    │
    ├──────────────────┐
    ▼                  ▼
Group 3: Celery    Group 5: Template Editor
    │                  │
    ▼                  ▼
Group 4: Signals   Group 6: Django Admin
    │                  │
    └────────┬─────────┘
             ▼
      Group 7: Webhooks
             │
             ▼
      Group 8: Testing
```

---

## Key Files to Create/Modify

| File | Action |
|------|--------|
| `pyproject.toml` | Add django-anymail, markdown |
| `prayer_room_api/settings.py` | Email backend, Celery Beat schedule |
| `prayer_room_api/models.py` | EmailTemplate, EmailLog models |
| `prayer_room_api/tasks.py` | Celery tasks |
| `prayer_room_api/signals.py` | Response notification signal |
| `prayer_room_api/apps.py` | Register signals |
| `prayer_room_api/views.py` | EmailTemplateView |
| `prayer_room_api/forms.py` | EmailTemplateForm |
| `prayer_room_api/urls.py` | Template editor URLs |
| `prayer_room_api/admin.py` | Admin configuration |
| `templates/emailtemplate/` | List and form templates |

---

## Environment Variables

```
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_SES_REGION=eu-west-1
DEFAULT_FROM_EMAIL=Prayer Room <noreply@example.com>
```
