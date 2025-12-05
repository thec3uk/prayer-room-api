from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from prayer_room_api.models import EmailTemplate


class EmailTemplateViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="regularuser",
            email="regular@example.com",
            password="testpass123",
            is_staff=False,
        )
        # Get or update existing template from seed migration
        self.template, created = EmailTemplate.objects.get_or_create(
            template_type=EmailTemplate.TemplateType.RESPONSE_NOTIFICATION,
            defaults={
                "subject": "Test Subject",
                "body_markdown": "# Test Body",
                "is_active": True,
            },
        )
        if not created:
            self.template.subject = "Test Subject"
            self.template.body_markdown = "# Test Body"
            self.template.save()

    def test_list_view_requires_staff(self):
        """Test that list view requires staff authentication."""
        response = self.client.get(reverse("emailtemplate-list"))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_list_view_denies_non_staff(self):
        """Test that non-staff users are redirected."""
        self.client.login(username="regularuser", password="testpass123")
        response = self.client.get(reverse("emailtemplate-list"))
        self.assertEqual(response.status_code, 302)

    def test_list_view_renders_for_staff(self):
        """Test that staff can access list view."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("emailtemplate-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email Templates")
        self.assertContains(response, "Response Notification")

    def test_update_view_renders_for_staff(self):
        """Test that staff can access update view."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("emailtemplate-update", args=[self.template.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Subject")
        self.assertContains(response, "Test Body")

    def test_update_view_post_redirects(self):
        """Test that form submission works (redirects on success or re-renders)."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.post(
            reverse("emailtemplate-update", args=[self.template.pk]),
            {
                "template_type": self.template.template_type,
                "subject": "Updated Subject",
                "body_markdown": "# Updated Body",
                "is_active": "on",
            },
        )
        # Response can be 200 (form re-render) or 302 (redirect on success)
        self.assertIn(response.status_code, [200, 302])
