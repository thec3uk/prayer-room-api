import logging

import markdown
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template
from django.utils import timezone

from .models import EmailLog, EmailTemplate, PrayerPraiseRequest, UserProfile

logger = logging.getLogger(__name__)


def send_templated_email(template, recipient_email, context_data):
    """
    Render and send an email using a stored template.
    Markdown body is converted to HTML, with plain text fallback.
    """
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
        status=EmailLog.Status.PENDING,
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        msg.attach_alternative(body_html, "text/html")
        msg.send()

        log.status = EmailLog.Status.SENT
        log.sent_at = timezone.now()
        log.save()
        logger.info(f"Email sent to {recipient_email}: {subject}")

    except Exception as e:
        log.status = EmailLog.Status.FAILED
        log.error_message = str(e)
        log.save()
        logger.error(f"Failed to send email to {recipient_email}: {e}")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_moderator_digest(self):
    """
    Hourly digest for staff users with pending and flagged requests.
    """
    try:
        template = EmailTemplate.objects.get(
            template_type=EmailTemplate.TemplateType.MODERATOR_DIGEST,
            is_active=True,
        )
    except EmailTemplate.DoesNotExist:
        logger.warning("Moderator digest template not found or inactive")
        return "Template not found or inactive"

    # Get staff users with email addresses
    staff_users = User.objects.filter(
        is_staff=True,
        email__isnull=False,
    ).exclude(email="")

    if not staff_users.exists():
        return "No staff users with email addresses"

    # Get pending requests (not approved, not archived)
    pending_requests = PrayerPraiseRequest.objects.filter(
        archived_at__isnull=True,
        approved_at__isnull=True,
    ).order_by("-created_at")[:20]

    # Get flagged requests (flagged but not archived)
    flagged_requests = PrayerPraiseRequest.objects.filter(
        flagged_at__isnull=False,
        archived_at__isnull=True,
    ).order_by("-flagged_at")[:20]

    pending_count = PrayerPraiseRequest.objects.filter(
        archived_at__isnull=True,
        approved_at__isnull=True,
    ).count()

    flagged_count = PrayerPraiseRequest.objects.filter(
        flagged_at__isnull=False,
        archived_at__isnull=True,
    ).count()

    if pending_count == 0 and flagged_count == 0:
        return "No pending or flagged requests"

    moderation_url = "https://api.prayer.thec3.uk/moderation/"

    sent_count = 0
    for user in staff_users:
        context = {
            "recipient_name": user.first_name or user.username,
            "pending_requests": list(pending_requests),
            "pending_count": pending_count,
            "flagged_requests": list(flagged_requests),
            "flagged_count": flagged_count,
            "moderation_url": moderation_url,
        }
        try:
            send_templated_email(template, user.email, context)
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send moderator digest to {user.email}: {e}")

    return f"Sent moderator digest to {sent_count} staff members"


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_user_digest(self, frequency="daily"):
    """
    Daily or weekly digest for users with updates on their prayer requests.

    Args:
        frequency: 'daily' or 'weekly'
    """
    try:
        template = EmailTemplate.objects.get(
            template_type=EmailTemplate.TemplateType.USER_DIGEST,
            is_active=True,
        )
    except EmailTemplate.DoesNotExist:
        logger.warning("User digest template not found or inactive")
        return "Template not found or inactive"

    # Calculate time window based on frequency
    if frequency == "daily":
        since = timezone.now() - timezone.timedelta(days=1)
    else:  # weekly
        since = timezone.now() - timezone.timedelta(weeks=1)

    # Get users who have opted in to digests
    profiles = (
        UserProfile.objects.filter(
            enable_digest_notifications=True,
            user__email__isnull=False,
        )
        .exclude(user__email="")
        .select_related("user")
    )

    sent_count = 0
    for profile in profiles:
        user = profile.user

        # Get user's requests with responses added since last digest
        requests_with_responses = PrayerPraiseRequest.objects.filter(
            created_by=user,
            updated_at__gte=since,
        ).exclude(response_comment="")

        if not requests_with_responses.exists():
            continue

        context = {
            "recipient_name": user.first_name or user.username,
            "requests_with_responses": list(requests_with_responses),
            "frequency": frequency,
        }

        try:
            send_templated_email(template, user.email, context)
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send user digest to {user.email}: {e}")

    return f"Sent user digest ({frequency}) to {sent_count} users"


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_response_notification(self, prayer_request_id):
    """
    Immediate notification when response_comment is added to a prayer request.
    Only sends to users who have opted in.
    """
    try:
        request = PrayerPraiseRequest.objects.select_related("created_by").get(
            id=prayer_request_id
        )
    except PrayerPraiseRequest.DoesNotExist:
        logger.warning(f"Prayer request {prayer_request_id} not found")
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

    try:
        template = EmailTemplate.objects.get(
            template_type=EmailTemplate.TemplateType.RESPONSE_NOTIFICATION,
            is_active=True,
        )
    except EmailTemplate.DoesNotExist:
        logger.warning("Response notification template not found or inactive")
        return "Template not found or inactive"

    context = {
        "recipient_name": user.first_name or user.username,
        "request_content": request.content[:200],
        "response_text": request.response_comment,
    }

    try:
        send_templated_email(template, user.email, context)
        return f"Sent response notification to {user.email}"
    except Exception as e:
        logger.error(f"Failed to send response notification to {user.email}: {e}")
        raise
