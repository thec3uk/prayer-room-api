from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.html import escape
from django.utils.timezone import now

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

    def _delete_seed_prayers(self):
        """Remove every prayer eligible for the response queue."""
        from django.db.models import Q

        PrayerPraiseRequest.objects.filter(
            approved_at__isnull=False,
            flagged_at__isnull=True,
            archived_at__isnull=True,
            response_skipped_at__isnull=True,
        ).filter(Q(response_comment__isnull=True) | Q(response_comment="")).delete()

    def test_get_requires_staff_authentication(self):
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 302)

    def test_get_denies_non_staff(self):
        self.client.login(username="regularuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 302)

    def test_get_lists_eligible_prayer_requests(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test User")
        self.assertContains(response, "Please pray for my family")

    def test_get_returns_empty_state_when_no_eligible_requests(self):
        self._delete_seed_prayers()

        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        has_empty_message = any(escape(msg) in content for msg in EMPTY_QUEUE_MESSAGES)
        self.assertTrue(has_empty_message, "Expected one of the empty queue messages")

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_get_excludes_prayers_with_response(self, mock_task):
        self.eligible_prayer.response_comment = "Already responded"
        self.eligible_prayer.save()

        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Please pray for my family")

    def test_get_excludes_prayers_marked_no_response(self):
        self.eligible_prayer.response_skipped_at = now()
        self.eligible_prayer.save()

        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Please pray for my family")

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_post_respond_saves_response_comment(self, mock_task):
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

        self.eligible_prayer.refresh_from_db()
        self.assertEqual(
            self.eligible_prayer.response_comment, "We are praying for you!"
        )
        self.assertIn("X-Message", response.headers)

    def test_post_no_response_sets_response_skipped_at(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.post(
            reverse("prayer-response"),
            {
                "prayer_id": self.eligible_prayer.id,
                "action": "no_response",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

        self.eligible_prayer.refresh_from_db()
        self.assertIsNotNone(self.eligible_prayer.response_skipped_at)
        self.assertEqual(self.eligible_prayer.response_comment, "")
        self.assertIn("X-Message", response.headers)

    def test_htmx_request_returns_partial(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("prayer-response"),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<!DOCTYPE html>")

    def test_regular_request_returns_full_page(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertEqual(response.status_code, 200)
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

        self.prayer = PrayerPraiseRequest.objects.create(
            name="John Doe",
            content="Please pray for healing",
            location=self.location,
            approved_at=now(),
            type="prayer",
        )

    def test_template_displays_prayer_details(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, "John Doe")
        self.assertContains(response, "Please pray for healing")
        self.assertContains(response, "Test Location")
        self.assertContains(response, "Prayer")

    def test_template_has_textarea_with_correct_name(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, 'name="response_comment"')

    def test_template_has_htmx_attributes_on_buttons(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, "hx-post=")
        self.assertContains(response, 'hx-target="#prayer-response-content"')
        self.assertContains(response, "hx-swap=")

    def test_template_has_no_response_button(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, "Mark as no response")
        self.assertContains(response, '"action": "no_response"')

    def test_empty_state_displays_fun_message(self):
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

    def test_list_shows_all_eligible_prayers(self):
        """List view shows every eligible prayer at once (not one-at-a-time)."""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, "First prayer request")
        self.assertContains(response, "Second prayer request")

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_respond_removes_prayer_from_list(self, mock_task):
        self.client.login(username="staffuser", password="testpass123")

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

        self.prayer1.refresh_from_db()
        self.assertEqual(self.prayer1.response_comment, "Praying for you!")

        content = response.content.decode()
        self.assertNotIn("First prayer request", content)
        self.assertIn("Second prayer request", content)

    def test_no_response_removes_prayer_from_list(self):
        self.client.login(username="staffuser", password="testpass123")

        response = self.client.post(
            reverse("prayer-response"),
            {
                "prayer_id": self.prayer1.id,
                "action": "no_response",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

        self.prayer1.refresh_from_db()
        self.assertIsNotNone(self.prayer1.response_skipped_at)
        self.assertEqual(self.prayer1.response_comment, "")

        content = response.content.decode()
        self.assertNotIn("First prayer request", content)
        self.assertIn("Second prayer request", content)

    def test_navigation_link_appears_for_staff(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("prayer-response"))
        self.assertContains(response, 'href="/prayers/respond/"')
        self.assertContains(response, "Respond")
