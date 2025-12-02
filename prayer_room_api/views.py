from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.generic import ListView
from neapolitan.views import CRUDView
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .forms import BulkModerationForm, PrayerModerationForm
from .models import (
    BannedWord,
    HomePageContent,
    Location,
    PrayerInspiration,
    PrayerPraiseRequest,
    Setting,
)
from .serializers import (
    HomePageContentSerializer,
    LocationSerializer,
    PrayerInspirationSerializer,
    PrayerPraiseRequestSerializer,
    SettingSerializer,
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
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class PrayerPraiseRequestViewSet(ModelViewSet):
    queryset = (
        PrayerPraiseRequest.objects.select_related("location")
        .filter(archived_at__isnull=True)
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
class BannedWordCRUDView(CRUDView):
    model = BannedWord
    fields = ["word", "auto_action", "is_active"]
    filterset_fields = ["auto_action", "is_active"]
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
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

        # Add match counts for list view
        if hasattr(self, "object_list"):
            for word in context.get("object_list", []):
                word.match_count = self._get_match_count(word)

        return context

    def get_template_names(self):
        # Return partial template for HTMX requests on list view
        if self.request.htmx and self.role.value == "list":
            return ["prayer_room_api/_bannedword_table.html"]
        return super().get_template_names()

    def _get_match_count(self, banned_word):
        """Calculate match count for a banned word dynamically."""
        word_lower = banned_word.word.lower()
        return PrayerPraiseRequest.objects.filter(
            Q(flagged_at__isnull=False) | Q(archived_at__isnull=False),
            content__icontains=word_lower,
        ).count()
