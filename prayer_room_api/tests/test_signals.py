from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from prayer_room_api.models import Location, PrayerPraiseRequest


class ResponseNotificationSignalTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(name="Main", slug="main")
        self.user = User.objects.create_user(
            username="signaluser",
            email="signal@example.com",
        )

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_signal_triggers_on_response_comment_added(self, mock_task):
        """Test that adding response_comment triggers notification task."""
        prayer = PrayerPraiseRequest.objects.create(
            created_by=self.user,
            location=self.location,
            content="Test prayer",
            response_comment="",
        )

        # Now add a response comment
        prayer.response_comment = "We are praying for you!"
        prayer.save()

        mock_task.assert_called_once_with(prayer.pk)

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_signal_does_not_trigger_on_other_changes(self, mock_task):
        """Test that other field changes don't trigger notification."""
        prayer = PrayerPraiseRequest.objects.create(
            created_by=self.user,
            location=self.location,
            content="Test prayer",
            response_comment="",
        )
        mock_task.reset_mock()

        # Update other fields
        prayer.prayer_count = 5
        prayer.save()

        mock_task.assert_not_called()

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_signal_does_not_trigger_on_new_instance(self, mock_task):
        """Test that creating a new prayer with response doesn't trigger signal."""
        # Creating new instance with response should not trigger
        # (only when changing from empty to populated)
        PrayerPraiseRequest.objects.create(
            created_by=self.user,
            location=self.location,
            content="Test prayer",
            response_comment="Initial response",
        )

        mock_task.assert_not_called()

    @patch("prayer_room_api.tasks.send_response_notification.delay")
    def test_signal_does_not_trigger_when_already_has_response(self, mock_task):
        """Test that updating an existing response doesn't trigger again."""
        prayer = PrayerPraiseRequest.objects.create(
            created_by=self.user,
            location=self.location,
            content="Test prayer",
            response_comment="",
        )

        # First response triggers
        prayer.response_comment = "First response"
        prayer.save()
        mock_task.assert_called_once()
        mock_task.reset_mock()

        # Updating response should not trigger again
        prayer.response_comment = "Updated response"
        prayer.save()
        mock_task.assert_not_called()
