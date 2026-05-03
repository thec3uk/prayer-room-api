import random
from datetime import datetime, timedelta

import requests
from allauth.socialaccount.models import SocialToken
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views import View
from django.views.generic import ListView, TemplateView
from neapolitan.views import CRUDView

# Empty queue messages for Prayer Response page
EMPTY_QUEUE_MESSAGES = [
    "You did it! The prayer inbox is gloriously empty.",
    "No more prayers to respond to... time for a coffee break!",
    "All caught up! You're a prayer response champion.",
    "The queue is empty. Somewhere, angels are high-fiving.",
    "Nothing left! You've responded to everything. Gold star for you!",
    "Empty inbox achieved. Go forth and celebrate!",
    "That's all, folks! The prayer queue has been conquered.",
]
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .forms import (
    BulkModerationForm,
    EmailTemplateForm,
    PrayerModerationForm,
    PrayerResourceForm,
    PrayerResponseForm,
)
from .models import (
    BannedWord,
    EmailTemplate,
    HomePageContent,
    Location,
    PrayerInspiration,
    PrayerPraiseRequest,
    PrayerResource,
    Setting,
    UserProfile,
)
from .serializers import (
    HomePageContentSerializer,
    LocationSerializer,
    PrayerInspirationSerializer,
    PrayerPraiseRequestSerializer,
    PrayerResourceSerializer,
    SettingSerializer,
    UserProfileSerializer,
)


class PrayerInspirationModelViewSet(ReadOnlyModelViewSet):
    queryset = PrayerInspiration.objects.all()
    serializer_class = PrayerInspirationSerializer


class HomePageContentModelViewSet(ReadOnlyModelViewSet):
    queryset = HomePageContent.objects.all()
    serializer_class = HomePageContentSerializer


class SettingModelViewSet(ReadOnlyModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer


class LocationModelViewSet(ReadOnlyModelViewSet):
    queryset = Location.objects.filter(is_active=True)
    serializer_class = LocationSerializer


class PrayerResourceViewSet(ReadOnlyModelViewSet):
    queryset = PrayerResource.objects.select_related("section").filter(is_active=True)
    serializer_class = PrayerResourceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        resource_type = self.request.query_params.get("type")
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        return qs


class PrayerPraiseRequestViewSet(ModelViewSet):
    queryset = (
        PrayerPraiseRequest.objects.select_related("location")
        .filter(archived_at__isnull=True, approved_at__isnull=False)
        .order_by("-created_at")
    )
    serializer_class = PrayerPraiseRequestSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qst = super().get_queryset()
        location = self.request.query_params.get("location")
        if location:
            qst = qst.filter(location__slug=location)
        return qst

    @action(detail=True, methods=["post"])
    def increment_prayer_count(self, request, pk=None):
        prayer = self.get_object()
        prayer.prayer_count = F("prayer_count") + 1
        prayer.save()
        prayer.refresh_from_db()
        return Response({"prayer_count": prayer.prayer_count})

    @action(detail=True, methods=["post"])
    def mark_flagged(self, request, pk=None):
        prayer = self.get_object()
        prayer.flagged_at = now()
        prayer.save()
        prayer.refresh_from_db()
        return Response({"flagged_at": bool(prayer.flagged_at)})

    @action(detail=True, methods=["post"])
    def attach_to_user(self, request, pk=None):
        prayer = self.get_object()
        username = request.data.get("username")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if username:
                # If user does not exist, create a new user
                email = request.data.get("email", "")
                first_name = request.data.get("name", "")
                user = User.objects.create_user(
                    username, email, None, first_name=first_name
                )

        if prayer.created_by is None:
            prayer.created_by = user
            prayer.save()
            prayer.refresh_from_db()

        return Response({"created_by": prayer.created_by.username})


class UserProfileViewSet(ReadOnlyModelViewSet):
    serializer_class = UserProfileSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def user_profile(self, request, pk=None):
        username = request.data.get("username")
        try:
            userprofile = UserProfile.objects.get(username=username)
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found"}, status=404)

        serializer = self.get_serializer(userprofile)
        return Response(serializer.data)


class UpdatePreferencesView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        username = request.data.get("username")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if username:
                # If user does not exist, create a new user
                email = request.data.get("email", "")
                first_name = request.data.get("name", "")
                user = User.objects.create_user(
                    username, email, None, first_name=first_name
                )

        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user)

        profile.enable_digest_notifications = request.data.get(
            "digestNotifications", False
        )
        profile.enable_response_notifications = request.data.get(
            "responseNotifications", False
        )
        profile.save()

        return Response({"status": "Preferences updated successfully"})


@method_decorator(staff_member_required, name="dispatch")
class PrayerResponseView(View):
    """Typeform-style interface for moderators to respond to prayer requests one at a time."""

    template_name = "prayers/prayer_response.html"
    partial_template_name = "prayers/_prayer_response_content.html"

    def get_queryset(self):
        """Return queryset of eligible prayer requests."""
        return (
            PrayerPraiseRequest.objects.select_related("location")
            .filter(
                approved_at__isnull=False,
                flagged_at__isnull=True,
                archived_at__isnull=True,
                # Date when prayer responses got launched
                created_at__gte=datetime(2025, 12, 15),
            )
            .filter(Q(response_comment__isnull=True) | Q(response_comment=""))
            .order_by("?")
        )

    def get_object(self):
        """Get the next eligible prayer request."""
        return self.get_queryset().first()

    def get_context_data(self, **kwargs):
        """Build context for templates."""
        prayer = kwargs.get("prayer") or self.get_object()
        context = {"prayer": prayer}
        if prayer is None:
            context["empty_message"] = random.choice(EMPTY_QUEUE_MESSAGES)
        return context

    def render_to_response(self, context, **kwargs):
        """Render full template or HTMX partial based on request."""
        if self.request.htmx:
            html = render_to_string(
                self.partial_template_name, context, request=self.request
            )
            return HttpResponse(html)
        return render(self.request, self.template_name, context)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        prayer_id = request.POST.get("prayer_id")
        prayer = (
            get_object_or_404(PrayerPraiseRequest, pk=prayer_id) if prayer_id else None
        )
        form = PrayerResponseForm(request.POST, instance=prayer)
        message = None

        if form.is_valid():
            action = form.cleaned_data["action"]

            if action == "respond" and prayer:
                form.save()
                message = f"Response saved for {prayer.name}."

        # Get the next eligible prayer (skip just advances without saving)
        context = self.get_context_data()
        response = self.render_to_response(context)

        if message:
            if request.htmx:
                response["X-Message"] = message
            else:
                messages.success(request, message)

        if not request.htmx:
            return redirect("prayer-response")

        return response


@method_decorator(staff_member_required, name="dispatch")
class ModerationView(ListView):
    template_name = "prayers/moderation.html"

    def get_queryset(self):
        return (
            PrayerPraiseRequest.objects.select_related("location")
            .filter(approved_at__isnull=True, archived_at__isnull=True)
            .order_by("-created_at")
        )

    def get(self, request, *args, **kwargs):
        # Handle confirmation dialog request
        if request.htmx and request.GET.get("confirm"):
            return self._render_confirm_dialog(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "")

        # Handle bulk actions
        if action in ("bulk_approve", "bulk_deny"):
            return self._handle_bulk_action(request, action)

        # Handle single actions
        return self._handle_single_action(request)

    def _render_confirm_dialog(self, request):
        """Render the confirmation dialog for bulk actions."""
        action = request.GET.get("action", "")
        prayer_ids = request.GET.get("prayer_ids", "")

        try:
            ids_list = [int(id.strip()) for id in prayer_ids.split(",") if id.strip()]
        except ValueError:
            ids_list = []

        count = len(ids_list)
        action_word = "approve" if action == "bulk_approve" else "deny"

        html = render_to_string(
            "prayers/_confirm_dialog.html",
            {
                "title": f"{action_word.capitalize()} {count} request{'s' if count != 1 else ''}",
                "message": f"Are you sure you want to {action_word} {count} prayer request{'s' if count != 1 else ''}?",
                "action": action,
                "prayer_ids": prayer_ids,
            },
            request=request,
        )
        return HttpResponse(html)

    def _render_content_partial(self, request, message):
        """Render the moderation content partial for HTMX responses."""
        queryset = self.get_queryset()
        html = render_to_string(
            "prayers/_moderation_content.html",
            {"object_list": queryset},
            request=request,
        )
        response = HttpResponse(html)
        response["X-Message"] = message
        return response

    def _handle_single_action(self, request):
        form = PrayerModerationForm(request.POST)
        if form.is_valid():
            prayer_id = form.cleaned_data["prayer_id"]
            action = form.cleaned_data["action"]
            prayer = get_object_or_404(PrayerPraiseRequest, pk=prayer_id)

            if action == "approve":
                prayer.approved_at = now()
                prayer.save()
                message = f"Prayer request from {prayer.name} approved."
            else:
                prayer.archived_at = now()
                prayer.save()
                message = f"Prayer request from {prayer.name} denied."

            if request.htmx:
                return self._render_content_partial(request, message)

            messages.success(request, message)

        return redirect("moderation")

    def _handle_bulk_action(self, request, action):
        form = BulkModerationForm(request.POST)
        if form.is_valid():
            prayer_ids = form.cleaned_data["prayer_ids"]
            prayers = PrayerPraiseRequest.objects.filter(pk__in=prayer_ids)
            count = prayers.count()

            if action == "bulk_approve":
                prayers.update(approved_at=now())
                message = f"{count} prayer request{'s' if count != 1 else ''} approved."
            else:  # bulk_deny
                prayers.update(archived_at=now())
                message = f"{count} prayer request{'s' if count != 1 else ''} denied."

            if request.htmx:
                return self._render_content_partial(request, message)

            messages.success(request, message)

        return redirect("moderation")


@method_decorator(staff_member_required, name="dispatch")
class FlaggedView(ListView):
    template_name = "prayers/flagged.html"
    paginate_by = 25

    def get_queryset(self):
        return (
            PrayerPraiseRequest.objects.select_related("location")
            .filter(flagged_at__isnull=False, archived_at__isnull=True)
            .order_by("-flagged_at")
        )

    def get(self, request, *args, **kwargs):
        # Handle confirmation dialog request
        if request.htmx and request.GET.get("confirm"):
            return self._render_confirm_dialog(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "")

        # Handle bulk actions
        if action in ("bulk_unflag", "bulk_archive"):
            return self._handle_bulk_action(request, action)

        # Handle single actions
        return self._handle_single_action(request)

    def _render_confirm_dialog(self, request):
        """Render the confirmation dialog for bulk actions."""
        action = request.GET.get("action", "")
        prayer_ids = request.GET.get("prayer_ids", "")

        try:
            ids_list = [int(id.strip()) for id in prayer_ids.split(",") if id.strip()]
        except ValueError:
            ids_list = []

        count = len(ids_list)
        action_word = "unflag" if action == "bulk_unflag" else "archive"

        html = render_to_string(
            "prayers/_flagged_confirm_dialog.html",
            {
                "title": f"{action_word.capitalize()} {count} request{'s' if count != 1 else ''}",
                "message": f"Are you sure you want to {action_word} {count} prayer request{'s' if count != 1 else ''}?",
                "action": action,
                "prayer_ids": prayer_ids,
            },
            request=request,
        )
        return HttpResponse(html)

    def _render_content_partial(self, request, message):
        """Render the flagged content partial for HTMX responses."""
        from django.core.paginator import Paginator

        queryset = self.get_queryset()
        page_number = request.GET.get("page", 1)
        paginator = Paginator(queryset, self.paginate_by)
        page_obj = paginator.get_page(page_number)

        html = render_to_string(
            "prayers/_flagged_content.html",
            {
                "object_list": page_obj,
                "page_obj": page_obj,
                "paginator": paginator,
                "is_paginated": page_obj.has_other_pages(),
            },
            request=request,
        )
        response = HttpResponse(html)
        response["X-Message"] = message
        return response

    def _handle_single_action(self, request):
        from .forms import FlaggedModerationForm

        form = FlaggedModerationForm(request.POST)
        if form.is_valid():
            prayer_id = form.cleaned_data["prayer_id"]
            action = form.cleaned_data["action"]
            prayer = get_object_or_404(PrayerPraiseRequest, pk=prayer_id)

            if action == "unflag":
                prayer.flagged_at = None
                prayer.save()
                message = f"Prayer request from {prayer.name} unflagged."
            else:
                prayer.archived_at = now()
                prayer.save()
                message = f"Prayer request from {prayer.name} archived."

            if request.htmx:
                return self._render_content_partial(request, message)

            messages.success(request, message)

        return redirect("flagged")

    def _handle_bulk_action(self, request, action):
        from .forms import BulkFlaggedModerationForm

        form = BulkFlaggedModerationForm(request.POST)
        if form.is_valid():
            prayer_ids = form.cleaned_data["prayer_ids"]
            prayers = PrayerPraiseRequest.objects.filter(pk__in=prayer_ids)
            count = prayers.count()

            if action == "bulk_unflag":
                prayers.update(flagged_at=None)
                message = (
                    f"{count} prayer request{'s' if count != 1 else ''} unflagged."
                )
            else:  # bulk_archive
                prayers.update(archived_at=now())
                message = f"{count} prayer request{'s' if count != 1 else ''} archived."

            if request.htmx:
                return self._render_content_partial(request, message)

            messages.success(request, message)

        return redirect("flagged")


@method_decorator(staff_member_required, name="dispatch")
class BannedWordCRUDView(CRUDView):
    model = BannedWord
    fields = ["word", "auto_action", "is_active"]
    filterset_fields = ["auto_action", "is_active"]
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()

        # Annotate with match count using a scalar subquery
        # Note: __icontains is already case-insensitive, so no need for Lower()
        match_count_subquery = (
            PrayerPraiseRequest.objects.filter(
                Q(flagged_at__isnull=False) | Q(archived_at__isnull=False),
                content__icontains=OuterRef("word"),
            )
            .annotate(dummy=Value(1))
            .values("dummy")
            .annotate(count=Count("*"))
            .values("count")
        )
        queryset = queryset.annotate(
            match_count=Coalesce(Subquery(match_count_subquery), Value(0))
        )

        # Add search functionality
        search = self.request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(word__icontains=search)

        # Add sorting
        sort = self.request.GET.get("sort", "word")
        order = self.request.GET.get("order", "asc")

        if sort == "word":
            queryset = queryset.order_by("word" if order == "asc" else "-word")
        elif sort == "auto_action":
            queryset = queryset.order_by(
                "auto_action" if order == "asc" else "-auto_action"
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search"] = self.request.GET.get("search", "")
        context["sort"] = self.request.GET.get("sort", "word")
        context["order"] = self.request.GET.get("order", "asc")
        return context

    def get_template_names(self):
        # Return partial template for HTMX requests on list view
        if self.request.htmx and self.role.value == "list":
            return ["prayer_room_api/_bannedword_table.html"]
        return super().get_template_names()


# Define available context variables and example data for each template type
TEMPLATE_CONTEXT_INFO = {
    "moderator_digest": {
        "description": "Hourly digest sent to staff with pending and flagged requests",
        "variables": {
            "recipient_name": "Name of the moderator receiving the email",
            "pending_count": "Number of pending requests awaiting approval",
            "flagged_count": "Number of flagged requests needing review",
            "pending_requests": "List of pending request objects (use {% for req in pending_requests %})",
            "flagged_requests": "List of flagged request objects",
            "moderation_url": "URL to the moderation dashboard",
        },
        "example_data": {
            "recipient_name": "John",
            "pending_count": 5,
            "flagged_count": 2,
            "pending_requests": [],
            "flagged_requests": [],
            "moderation_url": "https://example.com/moderation/",
        },
    },
    "user_digest": {
        "description": "Daily/weekly digest sent to users with updates on their prayer requests",
        "variables": {
            "recipient_name": "Name of the user receiving the email",
            "requests_with_responses": "List of user's requests that received responses",
            "frequency": 'Either "daily" or "weekly"',
        },
        "example_data": {
            "recipient_name": "Sarah",
            "requests_with_responses": [],
            "frequency": "daily",
        },
    },
    "response_notification": {
        "description": "Immediate notification when someone responds to a user's prayer request",
        "variables": {
            "recipient_name": "Name of the user who submitted the prayer request",
            "request_content": "The original prayer request content (truncated)",
            "response_text": "The response/comment that was added",
        },
        "example_data": {
            "recipient_name": "Sarah",
            "request_content": "Please pray for my upcoming job interview...",
            "response_text": "Praying for you! May God give you peace and confidence.",
        },
    },
}


@method_decorator(staff_member_required, name="dispatch")
class EmailTemplateCRUDView(CRUDView):
    model = EmailTemplate
    form_class = EmailTemplateForm
    fields = ["template_type", "subject", "body_markdown", "is_active"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, "object") and self.object:
            context["context_info"] = TEMPLATE_CONTEXT_INFO.get(
                self.object.template_type, {}
            )
        context["all_context_info"] = TEMPLATE_CONTEXT_INFO
        return context


@method_decorator(staff_member_required, name="dispatch")
class EmailTemplatePreviewView(View):
    """HTMX endpoint for live template preview."""

    def post(self, request, pk):
        import markdown
        from django.template import Context, Template

        from .models import EmailTemplate

        template = get_object_or_404(EmailTemplate, pk=pk)
        context_info = TEMPLATE_CONTEXT_INFO.get(template.template_type, {})
        example_data = context_info.get("example_data", {})

        subject = request.POST.get("subject", "")
        body_markdown = request.POST.get("body_markdown", "")

        try:
            subject_rendered = Template(subject).render(Context(example_data))
            markdown_rendered = Template(body_markdown).render(Context(example_data))
            html_content = markdown.markdown(markdown_rendered)

            return HttpResponse(
                f"""
                <div class="preview-subject"><strong>Subject:</strong> {subject_rendered}</div>
                <hr>
                <div class="preview-body">{html_content}</div>
            """
            )
        except Exception as e:
            return HttpResponse(f'<div class="alert alert-danger">Error: {e}</div>')


@method_decorator(staff_member_required, name="dispatch")
class PrayerResourceCRUDView(CRUDView):
    model = PrayerResource
    form_class = PrayerResourceForm
    fields = ["title", "description", "resource_type", "url", "content", "is_active"]
    url_base = "resources"

    def get_queryset(self):
        return PrayerResource.objects.select_related("section").order_by("sort_order", "-created_at")

    def form_valid(self, form):
        if not form.instance.pk:
            from django.db.models import Max

            max_order = PrayerResource.objects.aggregate(
                max_order=Max("sort_order")
            )["max_order"]
            form.instance.sort_order = (max_order or 0) + 1
        return super().form_valid(form)


@method_decorator(staff_member_required, name="dispatch")
class PrayerResourceReorderView(View):
    def post(self, request):
        import json

        try:
            order = json.loads(request.body).get("order", [])
        except (json.JSONDecodeError, AttributeError):
            order = []

        if not order:
            return HttpResponse(status=400)

        resources = {
            r.pk: r
            for r in PrayerResource.objects.filter(pk__in=order).only(
                "pk", "resource_type", "sort_order", "section"
            )
        }

        current_section = None
        to_update = []
        for index, resource_id in enumerate(order):
            resource = resources.get(resource_id)
            if not resource:
                continue
            resource.sort_order = index
            if resource.resource_type == PrayerResource.ResourceType.SECTION:
                current_section = resource_id
                resource.section_id = None
            else:
                resource.section_id = current_section
            to_update.append(resource)

        PrayerResource.objects.bulk_update(to_update, ["sort_order", "section"])

        response = HttpResponse(status=204)
        response["X-Message"] = "Resource order updated"
        return response


@method_decorator(staff_member_required, name="dispatch")
class StaffDashboardView(TemplateView):
    """Staff home page: action tiles + 30-day activity chart."""

    template_name = "prayers/dashboard.html"
    activity_window_days = 30

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current = now()
        today = current.date()
        window_start_date = today - timedelta(days=self.activity_window_days - 1)
        window_start = current - timedelta(days=self.activity_window_days - 1)
        window_start = window_start.replace(hour=0, minute=0, second=0, microsecond=0)
        last_24h = current - timedelta(hours=24)

        prayers = PrayerPraiseRequest.objects

        pending_count = prayers.filter(
            approved_at__isnull=True, archived_at__isnull=True
        ).count()
        flagged_count = prayers.filter(
            flagged_at__isnull=False, archived_at__isnull=True
        ).count()
        awaiting_response_count = prayers.filter(
            approved_at__isnull=False,
            archived_at__isnull=True,
            flagged_at__isnull=True,
            created_at__gte=datetime(2025, 12, 15),
        ).filter(Q(response_comment__isnull=True) | Q(response_comment="")).count()
        new_today_count = prayers.filter(created_at__gte=last_24h).count()

        total_approved = prayers.filter(approved_at__isnull=False).count()
        total_archived = prayers.filter(archived_at__isnull=False).count()
        total_active = prayers.filter(
            approved_at__isnull=False, archived_at__isnull=True
        ).count()

        # Activity timeseries: count per day for submitted, approved, flagged.
        # Three queries (one per timestamp column) instead of one because each
        # series buckets on a different field.
        submitted_by_day = dict(
            prayers.filter(created_at__gte=window_start)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(n=Count("id"))
            .values_list("day", "n")
        )
        approved_by_day = dict(
            prayers.filter(approved_at__gte=window_start)
            .annotate(day=TruncDate("approved_at"))
            .values("day")
            .annotate(n=Count("id"))
            .values_list("day", "n")
        )
        flagged_by_day = dict(
            prayers.filter(flagged_at__gte=window_start)
            .annotate(day=TruncDate("flagged_at"))
            .values("day")
            .annotate(n=Count("id"))
            .values_list("day", "n")
        )

        activity = []
        for offset in range(self.activity_window_days):
            day = window_start_date + timedelta(days=offset)
            activity.append(
                {
                    "day": day,
                    "submitted": submitted_by_day.get(day, 0),
                    "approved": approved_by_day.get(day, 0),
                    "flagged": flagged_by_day.get(day, 0),
                }
            )

        peak = max(
            (max(d["submitted"], d["approved"]) for d in activity), default=0
        )
        # Round chart ceiling up to a clean number so gridlines look tidy.
        if peak <= 5:
            chart_max = 5
        elif peak <= 10:
            chart_max = 10
        else:
            chart_max = ((peak + 4) // 5) * 5

        # SVG chart geometry. Computed server-side so the template stays
        # purely declarative (no widthratio gymnastics, no JS plotting).
        chart_w, chart_h = 900, 220
        pad_t, pad_b, pad_l, pad_r = 20, 40, 40, 20
        plot_w = chart_w - pad_l - pad_r
        plot_h = chart_h - pad_t - pad_b
        slot = plot_w / self.activity_window_days
        bar_w = slot * 0.62

        def y_for(value):
            return pad_t + plot_h - (value / chart_max * plot_h if chart_max else 0)

        chart_points = []
        for i, d in enumerate(activity):
            cx = pad_l + slot * i + slot / 2
            submitted_h = (
                d["submitted"] / chart_max * plot_h if chart_max else 0
            )
            chart_points.append(
                {
                    "i": i,
                    "day": d["day"],
                    "submitted": d["submitted"],
                    "approved": d["approved"],
                    "flagged": d["flagged"],
                    "cx": round(cx, 2),
                    "bar_x": round(cx - bar_w / 2, 2),
                    "bar_y": round(pad_t + plot_h - submitted_h, 2),
                    "bar_w": round(bar_w, 2),
                    "bar_h": round(max(submitted_h, 0), 2),
                    "approved_y": round(y_for(d["approved"]), 2),
                    "flag_y": round(pad_t + plot_h + 14, 2),
                }
            )

        approved_path = "M " + " L ".join(
            f"{p['cx']} {p['approved_y']}" for p in chart_points
        )

        y_ticks = [
            {"y": round(y_for(chart_max * frac), 2), "label": int(round(chart_max * frac))}
            for frac in (0, 1 / 3, 2 / 3, 1)
        ]

        last_index = len(chart_points) - 1
        x_label_indices = {i for i in range(0, last_index + 1, 7)}
        # Always include the last day, but drop the prior weekly tick if it's
        # within 2 days of the end (avoids label collision at the right edge).
        x_label_indices.add(last_index)
        x_label_indices = {
            i for i in x_label_indices if i == last_index or last_index - i > 2
        }
        x_labels = [
            {"x": round(p["cx"], 2), "day": p["day"]}
            for p in chart_points
            if p["i"] in x_label_indices
        ]

        context.update(
            {
                "tiles": [
                    {
                        "key": "pending",
                        "label": "Pending moderation",
                        "count": pending_count,
                        "url_name": "moderation",
                        "tone": "amber" if pending_count else "neutral",
                        "hint": "Awaiting approve or deny",
                    },
                    {
                        "key": "flagged",
                        "label": "Flagged",
                        "count": flagged_count,
                        "url_name": "flagged",
                        "tone": "red" if flagged_count else "neutral",
                        "hint": "Needs review",
                    },
                    {
                        "key": "respond",
                        "label": "Awaiting response",
                        "count": awaiting_response_count,
                        "url_name": "prayer-response",
                        "tone": "blue" if awaiting_response_count else "neutral",
                        "hint": "Approved, no response yet",
                    },
                    {
                        "key": "new",
                        "label": "New in last 24h",
                        "count": new_today_count,
                        "url_name": "moderation",
                        "tone": "neutral",
                        "hint": "Submitted since yesterday",
                    },
                ],
                "totals": {
                    "approved": total_approved,
                    "archived": total_archived,
                    "active": total_active,
                },
                "activity": activity,
                "activity_window_days": self.activity_window_days,
                "chart_max": chart_max,
                "chart": {
                    "width": chart_w,
                    "height": chart_h,
                    "plot_left": pad_l,
                    "plot_right": chart_w - pad_r,
                    "plot_top": pad_t,
                    "plot_bottom": pad_t + plot_h,
                    "points": chart_points,
                    "approved_path": approved_path,
                    "y_ticks": y_ticks,
                    "x_labels": x_labels,
                    "slot": round(slot, 2),
                },
                "activity_totals": {
                    "submitted": sum(d["submitted"] for d in activity),
                    "approved": sum(d["approved"] for d in activity),
                    "flagged": sum(d["flagged"] for d in activity),
                },
            }
        )
        return context
