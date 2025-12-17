from django.conf import settings
from django.db import models
from django.utils.timezone import now


class PrayerInspiration(models.Model):
    verse = models.CharField(max_length=255)
    content = models.TextField()

    def __str__(self):
        return str(self.verse)


class Location(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.name)


class PrayerPraiseRequest(models.Model):
    class PrayerType(models.TextChoices):
        PRAYER = "prayer", "Prayer"
        PRAISE = "praise", "Praise"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=False)
    updated_at = models.DateTimeField(auto_now=True)
    type = models.CharField(
        choices=PrayerType, default=PrayerType.PRAYER, max_length=20
    )

    name = models.TextField(default="Anon")
    content = models.TextField()
    response_comment = models.TextField(blank=True, default="")

    prayer_count = models.IntegerField(default=0)

    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="prayer_requests"
    )

    flagged_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}: {self.content[:10]}"

    def save(self, *args, **kwargs):
        # this is manual until I have imported all the data
        if not self.pk and not self.created_at:
            self.created_at = now()
        super().save(*args, **kwargs)


class HomePageContent(models.Model):
    key = models.CharField(max_length=50)
    value = models.TextField()

    def __str__(self):
        return f"{self.key}"


class Setting(models.Model):
    name = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=True)
    button_text = models.CharField(max_length=255)


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    enable_digest_notifications = models.BooleanField(default=False)
    enable_response_notifications = models.BooleanField(default=False)


class BannedWord(models.Model):
    class AutoActionChoices(models.TextChoices):
        flag = "flag", "Flag Request"
        archive = "archive", "Archive Request"
        approve = "approve", "Approve Request"

    word = models.TextField()
    auto_action = models.CharField(
        max_length=255,
        choices=AutoActionChoices.choices,
        default=AutoActionChoices.flag,
    )
    is_active = models.BooleanField(default=True)


class EmailTemplate(models.Model):
    """
    Stores editable email templates for different notification types.
    Uses Markdown for body content, rendered to HTML at send time.
    Supports variable substitution using Django template syntax.
    """

    class TemplateType(models.TextChoices):
        MODERATOR_DIGEST = "moderator_digest", "Moderator Digest (Hourly)"
        USER_DIGEST = "user_digest", "User Digest (Daily/Weekly)"
        RESPONSE_NOTIFICATION = (
            "response_notification",
            "Response Notification (Immediate)",
        )

    template_type = models.CharField(
        max_length=50,
        choices=TemplateType.choices,
        unique=True,
        help_text="Type of notification this template is used for",
    )
    subject = models.CharField(
        max_length=200,
        help_text="Email subject line with optional template variables",
    )
    body_markdown = models.TextField(
        help_text="Email body in Markdown format. Supports Django template variables: {{ variable_name }}",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"

    def __str__(self):
        return self.get_template_type_display()


class EmailLog(models.Model):
    """Logs all sent emails for tracking and debugging."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name="logs",
    )
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Email Log"
        verbose_name_plural = "Email Logs"

    def __str__(self):
        return f"{self.recipient_email} - {self.subject[:30]}"
