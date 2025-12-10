from django.template import Context, Template
from django.test import TestCase

from prayer_room_api.models import EmailLog, EmailTemplate


class EmailTemplateModelTests(TestCase):
    def setUp(self):
        # Delete existing template if it exists (from seed migration)
        EmailTemplate.objects.filter(
            template_type=EmailTemplate.TemplateType.RESPONSE_NOTIFICATION
        ).delete()
        self.template = EmailTemplate.objects.create(
            template_type=EmailTemplate.TemplateType.RESPONSE_NOTIFICATION,
            subject="Test: {{ recipient_name }}",
            body_markdown="# Hello {{ recipient_name }}\n\nYour request: {{ request_content }}",
            is_active=True,
        )

    def test_template_str(self):
        """Test the string representation of EmailTemplate."""
        self.assertEqual(str(self.template), "Response Notification (Immediate)")

    def test_template_type_unique(self):
        """Test that template_type is unique."""
        with self.assertRaises(Exception):
            EmailTemplate.objects.create(
                template_type=EmailTemplate.TemplateType.RESPONSE_NOTIFICATION,
                subject="Duplicate",
                body_markdown="Duplicate body",
            )

    def test_subject_rendering(self):
        """Test that subject can be rendered with context."""
        subject_template = Template(self.template.subject)
        context = Context({"recipient_name": "John"})
        rendered = subject_template.render(context)
        self.assertEqual(rendered, "Test: John")

    def test_body_markdown_rendering(self):
        """Test that body_markdown can be rendered with context."""
        body_template = Template(self.template.body_markdown)
        context = Context(
            {
                "recipient_name": "John",
                "request_content": "Please pray for me",
            }
        )
        rendered = body_template.render(context)
        self.assertIn("Hello John", rendered)
        self.assertIn("Please pray for me", rendered)

    def test_markdown_to_html_conversion(self):
        """Test markdown to HTML conversion."""
        import markdown

        body_template = Template(self.template.body_markdown)
        context = Context(
            {
                "recipient_name": "John",
                "request_content": "Please pray for me",
            }
        )
        rendered_markdown = body_template.render(context)
        html = markdown.markdown(rendered_markdown)

        self.assertIn("<h1>", html)
        self.assertIn("Hello John", html)


class EmailLogModelTests(TestCase):
    def setUp(self):
        # Use existing template from seed migration or create new one
        self.template, _ = EmailTemplate.objects.get_or_create(
            template_type=EmailTemplate.TemplateType.MODERATOR_DIGEST,
            defaults={
                "subject": "Moderator Digest",
                "body_markdown": "# Digest",
                "is_active": True,
            },
        )

    def test_email_log_creation(self):
        """Test creating an EmailLog entry."""
        log = EmailLog.objects.create(
            template=self.template,
            recipient_email="test@example.com",
            subject="Test Subject",
            status=EmailLog.Status.PENDING,
        )
        self.assertEqual(log.status, EmailLog.Status.PENDING)
        self.assertEqual(log.recipient_email, "test@example.com")

    def test_email_log_str(self):
        """Test string representation of EmailLog."""
        log = EmailLog.objects.create(
            template=self.template,
            recipient_email="test@example.com",
            subject="A very long subject line that should be truncated",
            status=EmailLog.Status.SENT,
        )
        self.assertIn("test@example.com", str(log))

    def test_email_log_ordering(self):
        """Test that logs are ordered by created_at descending."""
        log1 = EmailLog.objects.create(
            template=self.template,
            recipient_email="first@example.com",
            subject="First",
        )
        log2 = EmailLog.objects.create(
            template=self.template,
            recipient_email="second@example.com",
            subject="Second",
        )
        logs = list(EmailLog.objects.all())
        self.assertEqual(logs[0], log2)
        self.assertEqual(logs[1], log1)

    def test_email_log_status_choices(self):
        """Test that status choices are valid."""
        log = EmailLog.objects.create(
            template=self.template,
            recipient_email="test@example.com",
            subject="Test",
        )
        log.status = EmailLog.Status.SENT
        log.save()
        log.refresh_from_db()
        self.assertEqual(log.status, EmailLog.Status.SENT)

        log.status = EmailLog.Status.FAILED
        log.save()
        log.refresh_from_db()
        self.assertEqual(log.status, EmailLog.Status.FAILED)
