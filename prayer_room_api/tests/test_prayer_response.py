from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from prayer_room_api.models import Location, PrayerPraiseRequest
from prayer_room_api.views import EMPTY_QUEUE_MESSAGES


class PrayerResponseViewTests(TestCase):
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
        self.location = Location.objects.create(
            name="Test Location", slug="test-location"
        )

        # Create an eligible prayer request (approved, not flagged, not archived, no response)
        from django.utils.timezone import now

        self.eligible_prayer = PrayerPraiseRequest.objects.create(
            name="Test User",
            content="Please pray for my family",
            location=self.location,
            approved_at=now(),
            flagged_at=None,
            archived_at=None,
            response_comment="",
            type="prayer",
        )

    def test_get_requires_staff_authentication(self):
        """Test that the view requires staff authentication."""
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_get_denies_non_staff(self):
        """Test that non-staff users are redirected."""
        self.client.login(username="regularuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 302)

    def test_get_returns_eligible_prayer_request(self):
        """Test GET returns eligible prayer request (approved, not flagged, not archived, no response)."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test User")
        self.assertContains(response, "Please pray for my family")

    def test_get_returns_empty_state_when_no_eligible_requests(self):
        """Test GET returns empty state when no eligible requests exist."""
        # Remove ALL eligible prayers (including any from seed data)
        from django.db.models import Q

        PrayerPraiseRequest.objects.filter(
            approved_at__isnull=False,
            flagged_at__isnull=True,
            archived_at__isnull=True,
        ).filter(Q(response_comment__isnull=True) | Q(response_comment="")).delete()

        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 200)
        # Should contain one of the empty queue messages
        content = response.content.decode()
        has_empty_message = any(msg in content for msg in EMPTY_QUEUE_MESSAGES)
        self.assertTrue(has_empty_message, "Expected one of the empty queue messages")

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_get_excludes_prayers_with_response(self, mock_task):
        """Test that prayers with existing response_comment are excluded."""
        self.eligible_prayer.response_comment = "Already responded"
        self.eligible_prayer.save()

        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 200)
        # Should show empty state, not the prayer
        self.assertNotContains(response, "Please pray for my family")

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_post_respond_saves_response_comment(self, mock_task):
        """Test POST with action=respond saves response_comment and returns next request."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.post(
            reverse("prayer-response"),
            {
                "prayer_id": self.eligible_prayer.id,
                "action": "respond",
                "response_comment": "We are praying for you!",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

        # Verify the response was saved
        self.eligible_prayer.refresh_from_db()
        self.assertEqual(
            self.eligible_prayer.response_comment, "We are praying for you!"
        )

        # Verify toast message header
        self.assertIn("X-Message", response.headers)

    def test_post_skip_advances_without_saving(self):
        """Test POST with action=skip advances without saving response."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.post(
            reverse("prayer-response"),
            {
                "prayer_id": self.eligible_prayer.id,
                "action": "skip",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

        # Verify response was NOT saved
        self.eligible_prayer.refresh_from_db()
        self.assertEqual(self.eligible_prayer.response_comment, "")

    def test_htmx_request_returns_partial(self):
        """Test HTMX requests return partial template."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("prayer-response"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        # Partial should not contain full HTML structure
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_regular_request_returns_full_page(self):
        """Test regular requests return full page template."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 200)
        # Full page should contain HTML structure
        self.assertContains(response, "<!DOCTYPE html>")


class PrayerResponseTemplateTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.location = Location.objects.create(
            name="Test Location", slug="test-location"
        )

        from django.utils.timezone import now

        self.prayer = PrayerPraiseRequest.objects.create(
            name="John Doe",
            content="Please pray for healing",
            location=self.location,
            approved_at=now(),
            type="prayer",
        )

    def test_template_displays_prayer_details(self):
        """Test template displays prayer details (name, type, location, content)."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, "John Doe")
        self.assertContains(response, "Please pray for healing")
        self.assertContains(response, "Test Location")
        self.assertContains(response, "Prayer")  # Type badge

    def test_template_has_textarea_with_correct_name(self):
        """Test textarea is present with correct name attribute."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, 'name="response_comment"')

    def test_template_has_htmx_attributes_on_buttons(self):
        """Test HTMX attributes are correctly set on buttons."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, "hx-post=")
        self.assertContains(response, 'hx-target="#prayer-response-content"')
        self.assertContains(response, "hx-swap=")

    def test_empty_state_displays_fun_message(self):
        """Test empty state partial renders with fun message when no requests."""
        self.prayer.delete()
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, "Check back later")


class PrayerResponseIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.location = Location.objects.create(
            name="Test Location", slug="test-location"
        )

        from django.utils.timezone import now

        self.prayer1 = PrayerPraiseRequest.objects.create(
            name="User One",
            content="First prayer request",
            location=self.location,
            approved_at=now(),
            type="prayer",
        )
        self.prayer2 = PrayerPraiseRequest.objects.create(
            name="User Two",
            content="Second prayer request",
            location=self.location,
            approved_at=now(),
            type="praise",
        )

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_respond_workflow_advances_to_next(self, mock_task):
        """Test full respond workflow: respond to one, see the next."""
        self.client.login(username="staffuser", password="testpass123")

        # Respond to first prayer
        response = self.client.post(
            reverse("prayer-response"),
            {
                "prayer_id": self.prayer1.id,
                "action": "respond",
                "response_comment": "Praying for you!",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

        # Verify first prayer was saved
        self.prayer1.refresh_from_db()
        self.assertEqual(self.prayer1.response_comment, "Praying for you!")

        # Response should show second prayer (or empty state)
        content = response.content.decode()
        # Either shows next prayer or empty state
        self.assertTrue(
            "Second prayer request" in content or "Check back later" in content
        )

    def test_skip_workflow_preserves_prayer(self):
        """Test skip workflow: skip one, it remains eligible."""
        self.client.login(username="staffuser", password="testpass123")

        # Skip first prayer
        response = self.client.post(
            reverse("prayer-response"),
            {
                "prayer_id": self.prayer1.id,
                "action": "skip",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

        # Verify first prayer was NOT modified
        self.prayer1.refresh_from_db()
        self.assertEqual(self.prayer1.response_comment, "")

        # First prayer should still be eligible (would appear again)
        eligible = PrayerPraiseRequest.objects.filter(
            approved_at__isnull=False,
            flagged_at__isnull=True,
            archived_at__isnull=True,
            response_comment="",
        )
        self.assertIn(self.prayer1, eligible)

    def test_navigation_link_appears_for_staff(self):
        """Test navigation link appears for staff users."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, 'href="/prayers/respond/"')
        self.assertContains(response, "Respond")
