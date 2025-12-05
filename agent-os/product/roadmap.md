# Prayer Room API - Product Roadmap

## Phase 1: Foundation (Completed)

Core infrastructure and basic functionality.

### Completed Features
- [x] Django project setup with Python 3.13
- [x] Core models: PrayerPraiseRequest, Location, PrayerInspiration
- [x] REST API with Django REST Framework
- [x] Token authentication for API access
- [x] Django Admin interface
- [x] Import/export functionality for data migration
- [x] Basic CORS configuration
- [x] Deployment infrastructure (Dokku on AWS EC2)
- [x] GitHub Actions CI/CD
- [x] Sentry error monitoring
- [x] ChurchSuite OAuth integration (django-allauth)

## Phase 2: Core Features (Completed)

Essential prayer management functionality.

### Completed Features
- [x] Prayer/praise request submission
- [x] Location-based categorization
- [x] Prayer count increment API
- [x] Flagging system
- [x] Archive functionality
- [x] Approval workflow
- [x] Webhook integration (incoming/outgoing via Zapier)
- [x] API pagination
- [x] Historic prayer data import

## Phase 3: Safety & Moderation (Completed)

Content moderation and safety features.

### Completed Features
- [x] Banned word model with auto-actions
- [x] Banned word detection on submission (auto-flag/archive/approve)
- [x] Flagged requests page
- [x] Moderation queue dashboard (`/moderation/`)
- [x] Bulk moderation actions (approve/deny multiple)

## Phase 4: Notifications & Communication (Completed)

User engagement and communication features.

### Completed Features
- [x] Email infrastructure with django-anymail (AWS SES for production)
- [x] EmailTemplate model with markdown support
- [x] EmailLog model for delivery tracking
- [x] Celery tasks for email delivery
  - Moderator digest (hourly)
  - User digest (daily/weekly)
  - Response notifications
- [x] Signal handlers for automatic response notifications
- [x] Email template editor UI with live preview (`/emailtemplate/`)
- [x] Django Admin for email templates and logs
- [x] Seed templates for all notification types

### Remaining (Manual Setup)
- [ ] AWS SES configuration and domain verification
- [ ] Environment variables for production email settings
- [ ] User notification preferences UI

## Phase 5: Tooling & Developer Experience

Infrastructure and development improvements.

### Planned
- [ ] Migrate from Poetry to uv package manager
- [ ] Enhanced testing suite
- [ ] API documentation (OpenAPI/Swagger)

## Phase 6: User Experience

Enhanced user-facing features.

### Planned
- [ ] Custom error pages (404 & 500 handlers)

## Phase 7: Future Considerations

Features for future evaluation.

### Ideas
- [ ] Prayer request categories/tags
- [ ] Prayer chains/groups
- [ ] Mobile app support
- [ ] Multi-tenant support for multiple churches
- [ ] Analytics dashboard
- [ ] Scheduled prayer reminders

---

## Known Bugs

None currently tracked.
