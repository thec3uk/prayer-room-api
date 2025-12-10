from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from prayer_room_api.models import (
    EmailLog,
    EmailTemplate,
    Location,
    PrayerPraiseRequest,
    UserProfile,
)
from prayer_room_api.tasks import (
    send_moderator_digest,
    send_response_notification,
    send_templated_email,
    send_user_digest,
)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SendTemplatedEmailTests(TestCase):
    def setUp(self):
        # Delete and recreate to ensure our test content
        EmailTemplate.objects.filter(
            template_type=EmailTemplate.TemplateType.RESPONSE_NOTIFICATION
        ).delete()
        self.template = EmailTemplate.objects.create(
            template_type=EmailTemplate.TemplateType.RESPONSE_NOTIFICATION,
            subject="Hello {{ recipient_name }}",
            body_markdown="# Hi {{ recipient_name }}\n\nContent: {{ request_content }}",
            is_active=True,
        )

    def test_send_templated_email_creates_log(self):
        """Test that sending email creates an EmailLog entry."""
        context = {
            "recipient_name": "John",
            "request_content": "Test content",
        }
        send_templated_email(self.template, "john@example.com", context)

        log = EmailLog.objects.get(recipient_email="john@example.com")
        self.assertEqual(log.status, EmailLog.Status.SENT)
        self.assertEqual(log.subject, "Hello John")
        self.assertIsNotNone(log.sent_at)

    def test_send_templated_email_renders_context(self):
        """Test that email content is rendered with context."""
        from django.core import mail

        context = {
            "recipient_name": "Sarah",
            "request_content": "My prayer request",
        }
        send_templated_email(self.template, "sarah@example.com", context)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Hello Sarah")
        self.assertIn("Hi Sarah", email.body)
        self.assertIn("My prayer request", email.body)

    @patch("prayer_room_api.tasks.EmailMultiAlternatives")
    def test_send_templated_email_failure_logs_error(self, mock_email_class):
        """Test that failed email sends are logged."""
        mock_email = MagicMock()
        mock_email.send.side_effect = Exception("SMTP Error")
        mock_email_class.return_value = mock_email

        context = {"recipient_name": "Test", "request_content": "Test"}

        with self.assertRaises(Exception):
            send_templated_email(self.template, "test@example.com", context)

        log = EmailLog.objects.get(recipient_email="test@example.com")
        self.assertEqual(log.status, EmailLog.Status.FAILED)
        self.assertIn("SMTP Error", log.error_message)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SendResponseNotificationTests(TestCase):
    def setUp(self):
        EmailTemplate.objects.filter(
            template_type=EmailTemplate.TemplateType.RESPONSE_NOTIFICATION
        ).delete()
        self.template = EmailTemplate.objects.create(
            template_type=EmailTemplate.TemplateType.RESPONSE_NOTIFICATION,
            subject="Response to your prayer",
            body_markdown="Hi {{ recipient_name }}, response: {{ response_text }}",
            is_active=True,
        )
        self.location = Location.objects.create(name="Main", slug="main")
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            first_name="Test",
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            enable_response_notifications=True,
        )
        self.prayer = PrayerPraiseRequest.objects.create(
            created_by=self.user,
            location=self.location,
            content="Please pray for me",
            response_comment="We are praying for you!",
        )

    def test_send_response_notification_success(self):
        """Test successful response notification."""
        result = send_response_notification(self.prayer.pk)

        self.assertIn("Sent response notification", result)
        self.assertTrue(
            EmailLog.objects.filter(recipient_email="testuser@example.com").exists()
        )

    def test_send_response_notification_no_user(self):
        """Test notification when prayer has no user."""
        self.prayer.created_by = None
        self.prayer.save()

        result = send_response_notification(self.prayer.pk)
        self.assertEqual(result, "No user linked to request")

    def test_send_response_notification_disabled(self):
        """Test notification when user has disabled notifications."""
        self.profile.enable_response_notifications = False
        self.profile.save()

        result = send_response_notification(self.prayer.pk)
        self.assertEqual(result, "User has disabled response notifications")

    def test_send_response_notification_no_email(self):
        """Test notification when user has no email."""
        self.user.email = ""
        self.user.save()

        result = send_response_notification(self.prayer.pk)
        self.assertEqual(result, "User has no email address")

    def test_send_response_notification_prayer_not_found(self):
        """Test notification for non-existent prayer."""
        result = send_response_notification(99999)
        self.assertEqual(result, "Prayer request not found")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SendModeratorDigestTests(TestCase):
    def setUp(self):
        EmailTemplate.objects.filter(
            template_type=EmailTemplate.TemplateType.MODERATOR_DIGEST
        ).delete()
        self.template = EmailTemplate.objects.create(
            template_type=EmailTemplate.TemplateType.MODERATOR_DIGEST,
            subject="Digest: {{ pending_count }} pending",
            body_markdown="Hi {{ recipient_name }}, {{ pending_count }} pending requests",
            is_active=True,
        )
        self.location = Location.objects.create(name="Main", slug="main")
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            first_name="Staff",
            is_staff=True,
        )

    def test_send_moderator_digest_no_requests(self):
        """Test digest when no pending/flagged requests."""
        result = send_moderator_digest()
        self.assertEqual(result, "No pending or flagged requests")

    def test_send_moderator_digest_with_pending(self):
        """Test digest with pending requests."""
        PrayerPraiseRequest.objects.create(
            location=self.location,
            content="Pending request",
            # Not approved, not archived = pending
        )

        result = send_moderator_digest()
        self.assertIn("Sent moderator digest to 1 staff", result)

    def test_send_moderator_digest_no_staff(self):
        """Test digest when no staff users."""
        self.staff_user.is_staff = False
        self.staff_user.save()

        PrayerPraiseRequest.objects.create(
            location=self.location,
            content="Pending request",
        )

        result = send_moderator_digest()
        self.assertEqual(result, "No staff users with email addresses")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SendUserDigestTests(TestCase):
    def setUp(self):
        EmailTemplate.objects.filter(
            template_type=EmailTemplate.TemplateType.USER_DIGEST
        ).delete()
        self.template = EmailTemplate.objects.create(
            template_type=EmailTemplate.TemplateType.USER_DIGEST,
            subject="Your digest",
            body_markdown="Hi {{ recipient_name }}",
            is_active=True,
        )
        self.location = Location.objects.create(name="Main", slug="main")
        self.user = User.objects.create_user(
            username="digestuser",
            email="digest@example.com",
            first_name="Digest",
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            enable_digest_notifications=True,
        )

    def test_send_user_digest_no_updates(self):
        """Test digest when user has no updates."""
        result = send_user_digest("daily")
        # No requests with responses = no emails sent
        self.assertIn("Sent user digest (daily) to 0 users", result)

    def test_send_user_digest_with_response(self):
        """Test digest when user has responses."""
        from django.utils import timezone

        prayer = PrayerPraiseRequest.objects.create(
            created_by=self.user,
            location=self.location,
            content="My prayer",
            response_comment="We're praying!",
        )
        # Update the updated_at to be recent
        prayer.updated_at = timezone.now()
        prayer.save()

        result = send_user_digest("daily")
        self.assertIn("Sent user digest (daily) to 1 users", result)

    def test_send_user_digest_disabled(self):
        """Test digest when user has disabled notifications."""
        self.profile.enable_digest_notifications = False
        self.profile.save()

        result = send_user_digest("daily")
        self.assertIn("Sent user digest (daily) to 0 users", result)
