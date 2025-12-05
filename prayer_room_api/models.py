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
