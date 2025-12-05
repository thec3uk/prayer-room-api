# Specification: Notifications & Communication

## 1. Overview

This feature implements an email notification system for the Prayer Room API using Celery for asynchronous task processing and AWS SES for email delivery. The system provides:

- **Moderator digests** (hourly) with pending and flagged requests
- **User digests** (daily/weekly) with updates on their prayer requests
- **Immediate response notifications** when someone responds to a user's prayer request if the user is opt-ed in.
- **Admin-editable email templates** without code changes

## 2. Goals

1. **Moderator Awareness**: Keep staff informed of pending moderation tasks via hourly digests
2. **User Engagement**: Notify users of responses and prayer activity on their requests
3. **Customizable Communications**: Allow administrators to edit email content without code changes
4. **Opt-in Control**: Respect user preferences for digest and response notifications
5. **Reliable Delivery**: Use AWS SES with Celery for scalable, async email delivery

## 3. Prerequisites

### Branch to Merge First
**`task/user-profile-request`** must be merged to `main` before implementation.

This branch provides:
- `PrayerPraiseRequest.created_by` - ForeignKey linking requests to User
- `UserProfile.enable_digest_notifications` - Boolean preference
- `UserProfile.enable_response_notifications` - Boolean preference
- `UpdatePreferencesView` - API endpoint for Remix app to update preferences

### AWS SES Setup Required
1. **AWS Account**: With SES access enabled
2. **Region**: eu-west-1 (Ireland) or eu-west-2 (London)
3. **Domain Verification**: Verify sending domain in SES console
4. **Production Access**: Request to move out of SES sandbox
5. **IAM Credentials**: Create user with `ses:SendEmail` and `ses:SendRawEmail` permissions

### Dependencies to Install
```
django-anymail[amazon-ses]
markdown
```

## 4. Technical Design

### 4.1 New Models

#### EmailTemplate Model
Admin-editable email templates with Django template variable support.

```python
# prayer_room_api/models.py

class EmailTemplate(models.Model):
    """
    Stores editable email templates for different notification types.
    Uses Markdown for body content, rendered to HTML at send time.
    Supports variable substitution using Django template syntax.
    """
    TEMPLATE_TYPES = [
        ('moderator_digest', 'Moderator Digest (Hourly)'),
        ('user_digest', 'User Digest (Daily/Weekly)'),
        ('response_notification', 'Response Notification (Immediate)'),
    ]
    
    template_type = models.CharField(
        max_length=50,
        choices=TEMPLATE_TYPES,
        unique=True,
        help_text="Type of notification this template is used for"
    )
    subject = models.CharField(
        max_length=200,
        help_text="Email subject line with optional template variables"
    )
    body_markdown = models.TextField(
        help_text="Email body in Markdown format. Supports Django template variables: {{ variable_name }}"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"
    
    def __str__(self):
        return self.get_template_type_display()
```

#### EmailLog Model
Track sent emails for debugging and monitoring.

```python
class EmailLog(models.Model):
    """Logs all sent emails for tracking and debugging."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='logs'
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
```

### 4.2 Settings Configuration

Add to `prayer_room_api/settings.py`:

```python
# Email Configuration - AWS SES via django-anymail
EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='Prayer Room <noreply@example.com>')

ANYMAIL = {
    "AMAZON_SES_CLIENT_PARAMS": {
        "region_name": env('AWS_SES_REGION', default='eu-west-1'),
    },
}

# AWS credentials
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default=None)
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default=None)
```

### 4.3 Celery Tasks

Create `prayer_room_api/tasks.py`:

```python
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from django.contrib.auth.models import User
from django.utils import timezone
from .models import EmailTemplate, EmailLog, PrayerPraiseRequest, UserProfile

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_moderator_digest(self):
    """
    Hourly digest for staff users with pending and flagged requests.
    """
    staff_users = User.objects.filter(groups__name='staff', email__isnull=False).exclude(email='')
    
    pending_requests = PrayerPraiseRequest.objects.filter(
        archived_at__isnull=True,
        flagged_at__isnull=True,
        # Add approval status filter if applicable
    )
    
    flagged_requests = PrayerPraiseRequest.objects.filter(
        flagged_at__isnull=False,
        archived_at__isnull=True
    )
    
    if not pending_requests.exists() and not flagged_requests.exists():
        return "No pending or flagged requests"
    
    template = EmailTemplate.objects.get(template_type='moderator_digest', is_active=True)
    
    for user in staff_users:
        context = {
            'recipient_name': user.first_name or user.username,
            'pending_requests': pending_requests,
            'pending_count': pending_requests.count(),
            'flagged_requests': flagged_requests,
            'flagged_count': flagged_requests.count(),
            'moderation_url': '...',  # URL to moderation dashboard
        }
        send_templated_email(template, user.email, context)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_user_digest(self, frequency='daily'):
    """
    Daily or weekly digest for users with updates on their prayer requests.
    
    Args:
        frequency: 'daily' or 'weekly'
    """
    # Calculate time window based on frequency
    if frequency == 'daily':
        since = timezone.now() - timezone.timedelta(days=1)
    else:  # weekly
        since = timezone.now() - timezone.timedelta(weeks=1)
    
    # Get users who have opted in to digests
    profiles = UserProfile.objects.filter(enable_digest_notifications=True)
    
    template = EmailTemplate.objects.get(template_type='user_digest', is_active=True)
    
    for profile in profiles:
        user = profile.user
        
        # Get user's requests with updates
        user_requests = PrayerPraiseRequest.objects.filter(
            created_by=user,
            updated_at__gte=since
        )
        
        # Get requests with new responses
        requests_with_responses = user_requests.exclude(response_comment='')
        
        # Get prayer count changes (would need to track this)
        
        if not requests_with_responses.exists():
            continue
        
        context = {
            'recipient_name': user.first_name or user.username,
            'requests_with_responses': requests_with_responses,
            'frequency': frequency,
        }
        send_templated_email(template, user.email, context)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_response_notification(self, prayer_request_id):
    """
    Immediate notification when response_comment is added to a prayer request.
    Only sends to ChurchSuite-authenticated users who have opted in.
    """
    try:
        request = PrayerPraiseRequest.objects.select_related('created_by').get(id=prayer_request_id)
    except PrayerPraiseRequest.DoesNotExist:
        return "Prayer request not found"
    
    if not request.created_by:
        return "No user linked to request"
    
    user = request.created_by
    
    # Check user preference
    try:
        profile = UserProfile.objects.get(user=user)
        if not profile.enable_response_notifications:
            return "User has disabled response notifications"
    except UserProfile.DoesNotExist:
        return "No user profile found"
    
    if not user.email:
        return "User has no email address"
    
    template = EmailTemplate.objects.get(template_type='response_notification', is_active=True)
    
    context = {
        'recipient_name': user.first_name or user.username,
        'request_content': request.content[:100],
        'response_text': request.response_comment,
    }
    
    send_templated_email(template, user.email, context)


def send_templated_email(template, recipient_email, context_data):
    """
    Render and send an email using a stored template.
    Markdown body is converted to HTML, with plain text fallback.
    """
    import markdown
    
    # Render subject and markdown body with context
    subject_template = Template(template.subject)
    markdown_template = Template(template.body_markdown)
    
    context = Context(context_data)
    
    subject = subject_template.render(context)
    body_markdown = markdown_template.render(context)
    
    # Convert markdown to HTML, use markdown source as plain text fallback
    body_html = markdown.markdown(body_markdown)
    body_text = body_markdown
    
    # Create email log
    log = EmailLog.objects.create(
        template=template,
        recipient_email=recipient_email,
        subject=subject,
        status='pending'
    )
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            to=[recipient_email]
        )
        msg.attach_alternative(body_html, "text/html")
        msg.send()
        
        log.status = 'sent'
        log.sent_at = timezone.now()
        log.save()
        
    except Exception as e:
        log.status = 'failed'
        log.error_message = str(e)
        log.save()
        raise
```

### 4.4 Celery Beat Schedule

Update `prayer_room_api/celery.py`:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'moderator-digest-hourly': {
        'task': 'prayer_room_api.tasks.send_moderator_digest',
        'schedule': crontab(minute=0),  # Every hour at :00
    },
    'user-digest-daily': {
        'task': 'prayer_room_api.tasks.send_user_digest',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8am
        'args': ('daily',),
    },
    'user-digest-weekly': {
        'task': 'prayer_room_api.tasks.send_user_digest',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),  # Monday 8am
        'args': ('weekly',),
    },
}
```

### 4.5 Signal Handler for Response Notifications

Create `prayer_room_api/signals.py`:

```python
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import PrayerPraiseRequest
from .tasks import send_response_notification

@receiver(pre_save, sender=PrayerPraiseRequest)
def check_response_change(sender, instance, **kwargs):
    """
    Trigger immediate notification when response_comment is added/changed.
    """
    if not instance.pk:
        return  # New instance, no previous value
    
    try:
        old_instance = PrayerPraiseRequest.objects.get(pk=instance.pk)
    except PrayerPraiseRequest.DoesNotExist:
        return
    
    # Check if response_comment changed from empty to populated
    if not old_instance.response_comment and instance.response_comment:
        # Queue the notification task
        send_response_notification.delay(instance.pk)
```

Register signals in `prayer_room_api/apps.py`:

```python
class PrayerRoomApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prayer_room_api'

    def ready(self):
        import prayer_room_api.signals  # noqa
```

## 5. Email Templates

### 5.1 Moderator Digest Template

**Subject**: `Prayer Room: {{ pending_count }} pending, {{ flagged_count }} flagged requests`

**Variables**:
- `{{ recipient_name }}` - Moderator's name
- `{{ pending_count }}` - Number of pending requests
- `{{ flagged_count }}` - Number of flagged requests
- `{{ pending_requests }}` - QuerySet of pending requests
- `{{ flagged_requests }}` - QuerySet of flagged requests
- `{{ moderation_url }}` - Link to moderation dashboard

### 5.2 User Digest Template

**Subject**: `Updates on your prayer requests`

**Variables**:
- `{{ recipient_name }}` - User's name
- `{{ requests_with_responses }}` - QuerySet of requests with new responses
- `{{ frequency }}` - 'daily' or 'weekly'

### 5.3 Response Notification Template

**Subject**: `Someone responded to your prayer request`

**Variables**:
- `{{ recipient_name }}` - User's name
- `{{ request_content }}` - Truncated original request
- `{{ response_text }}` - The response content

### 5.4 Default Templates Data Migration

Create a data migration to seed default templates:

```python
def seed_email_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('prayer_room_api', 'EmailTemplate')
    
    templates = [
        {
            'template_type': 'moderator_digest',
            'subject': 'Prayer Room: {{ pending_count }} pending, {{ flagged_count }} flagged',
            'body_markdown': '''...''',  # Markdown content
        },
        {
            'template_type': 'user_digest',
            'subject': 'Updates on your prayer requests',
            'body_markdown': '''...''',
        },
        {
            'template_type': 'response_notification',
            'subject': 'Someone responded to your prayer request',
            'body_markdown': '''...''',
        },
    ]
    
    for data in templates:
        EmailTemplate.objects.get_or_create(
            template_type=data['template_type'],
            defaults=data
        )
```

## 6. Admin Interface

### 6.1 Email Template Editor Page

A dedicated Django view at `/email-templates/` for editing email templates with live preview, built using **Neapolitan** for CRUD views and **HTMX** for live preview.

#### Features
- List all email templates with edit links (Neapolitan list view)
- Side-by-side editor: markdown on left, rendered HTML preview on right
- Context variable reference panel showing available variables per template type
- Live preview updates as you type (HTMX with debounce)
- Example data auto-fills template variables in preview

#### URL Configuration

```python
# prayer_room_api/urls.py

from .views import EmailTemplateView

urlpatterns += EmailTemplateView.get_urls()
```

#### Views

```python
# prayer_room_api/views.py

from neapolitan.views import CRUDView, Role
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.template import Template, Context
from django.http import HttpResponse
import markdown

from .models import EmailTemplate
from .forms import EmailTemplateForm


# Define available context variables and example data for each template type
TEMPLATE_CONTEXT_INFO = {
    'moderator_digest': {
        'description': 'Hourly digest sent to staff with pending and flagged requests',
        'variables': {
            'recipient_name': 'Name of the moderator receiving the email',
            'pending_count': 'Number of pending requests awaiting approval',
            'flagged_count': 'Number of flagged requests needing review',
            'pending_requests': 'List of pending request objects (use {% for req in pending_requests %})',
            'flagged_requests': 'List of flagged request objects',
            'moderation_url': 'URL to the moderation dashboard',
        },
        'example_data': {
            'recipient_name': 'John',
            'pending_count': 5,
            'flagged_count': 2,
            'pending_requests': [],
            'flagged_requests': [],
            'moderation_url': 'https://example.com/moderation/',
        }
    },
    'user_digest': {
        'description': 'Daily/weekly digest sent to users with updates on their prayer requests',
        'variables': {
            'recipient_name': 'Name of the user receiving the email',
            'requests_with_responses': "List of user's requests that received responses",
            'frequency': 'Either "daily" or "weekly"',
        },
        'example_data': {
            'recipient_name': 'Sarah',
            'requests_with_responses': [],
            'frequency': 'daily',
        }
    },
    'response_notification': {
        'description': 'Immediate notification when someone responds to a user\'s prayer request',
        'variables': {
            'recipient_name': 'Name of the user who submitted the prayer request',
            'request_content': 'The original prayer request content (truncated)',
            'response_text': 'The response/comment that was added',
        },
        'example_data': {
            'recipient_name': 'Sarah',
            'request_content': 'Please pray for my upcoming job interview...',
            'response_text': 'Praying for you! May God give you peace and confidence.',
        }
    },
}


@method_decorator(staff_member_required, name='dispatch')
class EmailTemplateView(CRUDView):
    model = EmailTemplate
    fields = ['template_type', 'subject', 'body_markdown', 'is_active']
    form_class = EmailTemplateForm
    
    @classmethod
    def get_urls(cls, roles=None):
        """Generate URLs including custom preview endpoint."""
        if roles is None:
            roles = {Role.LIST, Role.DETAIL, Role.UPDATE}
        urls = super().get_urls(roles=roles)
        # Add preview endpoint
        urls.append(
            path('emailtemplate/<int:pk>/preview/',
                 cls.as_view(role=Role.DETAIL),
                 name='emailtemplate-preview')
        )
        return urls
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, 'object') and self.object:
            context['context_info'] = TEMPLATE_CONTEXT_INFO.get(
                self.object.template_type, {}
            )
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle HTMX preview requests."""
        if request.htmx and request.POST.get('preview'):
            return self.render_preview(request)
        return super().post(request, *args, **kwargs)
    
    def render_preview(self, request):
        """Render markdown preview with example data."""
        self.object = self.get_object()
        context_info = TEMPLATE_CONTEXT_INFO.get(self.object.template_type, {})
        example_data = context_info.get('example_data', {})
        
        subject = request.POST.get('subject', '')
        body_markdown = request.POST.get('body_markdown', '')
        
        try:
            # Render Django template variables with example data
            subject_rendered = Template(subject).render(Context(example_data))
            markdown_rendered = Template(body_markdown).render(Context(example_data))
            
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_rendered)
            
            return HttpResponse(f'''
                <div class="preview-subject"><strong>Subject:</strong> {subject_rendered}</div>
                <hr>
                <div class="preview-body">{html_content}</div>
            ''')
        except Exception as e:
            return HttpResponse(f'<div class="alert alert-danger">Error: {e}</div>')
```

#### Form

```python
# prayer_room_api/forms.py

from django import forms
from .models import EmailTemplate


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ['template_type', 'subject', 'body_markdown', 'is_active']
        widgets = {
            'template_type': forms.Select(attrs={'readonly': True, 'disabled': True}),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'hx-post': '',  # Will be set in template
                'hx-trigger': 'keyup changed delay:300ms',
                'hx-target': '#preview-panel',
                'hx-include': '[name="body_markdown"]',
            }),
            'body_markdown': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'hx-post': '',  # Will be set in template
                'hx-trigger': 'keyup changed delay:300ms',
                'hx-target': '#preview-panel',
                'hx-include': '[name="subject"]',
            }),
        }
```

#### Templates

**templates/emailtemplate/emailtemplate_list.html**
```html
{% extends "base.html" %}
{% load neapolitan %}

{% block content %}
<div class="container">
    <h1>Email Templates</h1>
    <p class="text-muted">Edit email notification templates. Changes take effect immediately.</p>
    
    <table class="table">
        <thead>
            <tr>
                <th>Template</th>
                <th>Subject</th>
                <th>Status</th>
                <th>Last Updated</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for template in object_list %}
            <tr>
                <td>{{ template.get_template_type_display }}</td>
                <td>{{ template.subject|truncatechars:50 }}</td>
                <td>
                    {% if template.is_active %}
                        <span class="badge bg-success">Active</span>
                    {% else %}
                        <span class="badge bg-secondary">Inactive</span>
                    {% endif %}
                </td>
                <td>{{ template.updated_at|date:"M d, Y H:i" }}</td>
                <td>
                    <a href="{% url 'emailtemplate-update' template.pk %}" class="btn btn-sm btn-primary">Edit</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
```

**templates/emailtemplate/emailtemplate_form.html**
```html
{% extends "base.html" %}

{% block extra_head %}
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
{% endblock %}

{% block content %}
<div class="container-fluid">
    <h1>Edit: {{ object.get_template_type_display }}</h1>
    <p class="text-muted">{{ context_info.description }}</p>
    
    <div class="row">
        <!-- Left: Editor -->
        <div class="col-md-6">
            <form method="post">
                {% csrf_token %}
                
                <div class="mb-3">
                    <label class="form-label">Template Type</label>
                    <input type="text" class="form-control" 
                           value="{{ object.get_template_type_display }}" readonly disabled>
                    <input type="hidden" name="template_type" value="{{ object.template_type }}">
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Subject</label>
                    <input type="text" name="subject" class="form-control" 
                           value="{{ object.subject }}"
                           hx-post="{% url 'emailtemplate-preview' object.pk %}"
                           hx-trigger="keyup changed delay:300ms"
                           hx-target="#preview-panel"
                           hx-include="[name='body_markdown']"
                           hx-vals='{"preview": "1"}'>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Body (Markdown)</label>
                    <textarea name="body_markdown" class="form-control" rows="15"
                              hx-post="{% url 'emailtemplate-preview' object.pk %}"
                              hx-trigger="keyup changed delay:300ms"
                              hx-target="#preview-panel"
                              hx-include="[name='subject']"
                              hx-vals='{"preview": "1"}'>{{ object.body_markdown }}</textarea>
                </div>
                
                <div class="mb-3 form-check">
                    <input type="checkbox" name="is_active" class="form-check-input" 
                           id="is-active" {% if object.is_active %}checked{% endif %}>
                    <label class="form-check-label" for="is-active">Active</label>
                </div>
                
                <!-- Context Variables Reference -->
                <div class="card mb-3">
                    <div class="card-header">Available Variables</div>
                    <div class="card-body">
                        <table class="table table-sm mb-0">
                            {% for var_name, var_desc in context_info.variables.items %}
                            <tr>
                                <td><code>{{ "{{" }} {{ var_name }} {{ "}}" }}</code></td>
                                <td>{{ var_desc }}</td>
                            </tr>
                            {% endfor %}
                        </table>
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary">Save Template</button>
                <a href="{% url 'emailtemplate-list' %}" class="btn btn-secondary">Cancel</a>
            </form>
        </div>
        
        <!-- Right: Live Preview -->
        <div class="col-md-6">
            <div class="card sticky-top" style="top: 20px;">
                <div class="card-header">
                    Preview <span class="text-muted">(with example data)</span>
                    <span class="htmx-indicator float-end">Loading...</span>
                </div>
                <div class="card-body">
                    <div id="preview-panel" class="email-preview">
                        <div class="text-muted">Start typing to see preview...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
.email-preview {
    background: #fff;
    min-height: 300px;
}
.preview-body {
    padding: 10px 0;
}
.preview-body h1, .preview-body h2, .preview-body h3 {
    margin-top: 0;
}
.htmx-request .htmx-indicator {
    display: inline;
}
.htmx-indicator {
    display: none;
}
</style>
{% endblock %}
```

### 6.2 Django Admin

The standard Django admin provides full editing capability with a link to the enhanced template editor:

```python
# prayer_room_api/admin.py

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['template_type', 'subject', 'is_active', 'updated_at']
    list_filter = ['is_active', 'template_type']
    readonly_fields = ['created_at', 'updated_at']
    change_list_template = 'admin/emailtemplate_changelist.html'
    
    fieldsets = (
        (None, {
            'fields': ('template_type', 'is_active')
        }),
        ('Content', {
            'fields': ('subject', 'body_markdown'),
            'description': 'Use Markdown for formatting. Django template variables: {{ variable_name }}'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient_email', 'subject', 'status', 'sent_at', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['recipient_email', 'subject']
    readonly_fields = ['template', 'recipient_email', 'subject', 'status', 
                       'error_message', 'sent_at', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
```

**admin/emailtemplate_changelist.html**
```html
{% extends "admin/change_list.html" %}
{% block object-tools-items %}
    <li>
        <a href="{% url 'emailtemplate-list' %}" class="button">
            Open Template Editor
        </a>
    </li>
    {{ block.super }}
{% endblock %}
```

## 7. Webhook Verification

As part of this phase, verify existing outgoing webhook functionality:

1. Review current webhook configuration in admin
2. Test webhook triggers (new request, flag, archive, etc.)
3. Verify Zapier integration is receiving events
4. Document any issues found

## 8. Testing Strategy

### Unit Tests
- EmailTemplate model validation
- Template rendering with context variables
- Celery task logic (mocked email sending)
- Signal handler triggers correctly
- User preference checking

### Integration Tests
- Full email flow with test SES configuration
- Celery task execution
- Admin template editing

### Manual Testing Checklist
- [ ] Moderator digest received hourly by staff users
- [ ] User digest received daily/weekly by opted-in users
- [ ] Response notification received immediately when response added
- [ ] Users with notifications disabled don't receive emails
- [ ] Admin can edit templates and changes take effect
- [ ] Email renders correctly in major clients (Gmail, Outlook)

## 9. Rollout Plan

### Phase 1: Infrastructure Setup
1. Merge `task/user-profile-request` branch
2. Configure AWS SES (verify domain, IAM credentials)
3. Install `django-anymail[amazon-ses]`
4. Add environment variables

### Phase 2: Models & Migrations
1. Create EmailTemplate and EmailLog models
2. Create and run migrations
3. Seed default templates

### Phase 3: Celery Tasks
1. Implement Celery tasks
2. Configure Celery Beat schedule
3. Set up signal handlers

### Phase 4: Admin Interface
1. Configure EmailTemplate admin
2. Configure EmailLog admin

### Phase 5: Testing
1. Unit and integration tests
2. Manual testing with real emails
3. Webhook verification

### Phase 6: Deployment
1. Deploy to staging
2. Full QA pass
3. Deploy to production
4. Monitor email logs and SES metrics

## 10. Out of Scope

- SMS notifications
- Push notifications
- In-app notification center
- Admin notification management UI (beyond template editing)
- User preferences UI (handled by Remix app)
- Preferences API endpoints (in `task/user-profile-request` branch)
- Email analytics dashboard
- Bounce/complaint webhook handling
