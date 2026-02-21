from django import forms

from .models import EmailTemplate, PrayerPraiseRequest, PrayerResource


class EmailTemplateForm(forms.ModelForm):
    class Meta:
        model = EmailTemplate
        fields = ["template_type", "subject", "body_markdown", "is_active"]
        widgets = {
            "template_type": forms.Select(attrs={"readonly": True, "disabled": True}),
            "subject": forms.TextInput(
                attrs={
                    "class": "form-input",
                }
            ),
            "body_markdown": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 15,
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class PrayerModerationForm(forms.Form):
    ACTION_CHOICES = [
        ("approve", "Approve"),
        ("deny", "Deny"),
    ]

    prayer_id = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.HiddenInput())


class BulkModerationForm(forms.Form):
    ACTION_CHOICES = [
        ("bulk_approve", "Approve"),
        ("bulk_deny", "Deny"),
    ]

    prayer_ids = forms.CharField(widget=forms.HiddenInput())
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.HiddenInput())

    def clean_prayer_ids(self):
        ids_str = self.cleaned_data["prayer_ids"]
        try:
            return [int(id.strip()) for id in ids_str.split(",") if id.strip()]
        except ValueError:
            raise forms.ValidationError("Invalid prayer IDs")


class FlaggedModerationForm(forms.Form):
    ACTION_CHOICES = [
        ("unflag", "Unflag"),
        ("archive", "Archive"),
    ]

    prayer_id = forms.IntegerField(widget=forms.HiddenInput())
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.HiddenInput())


class PrayerResponseForm(forms.ModelForm):
    ACTION_CHOICES = [
        ("respond", "Respond"),
        ("skip", "Skip"),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.HiddenInput())

    class Meta:
        model = PrayerPraiseRequest
        fields = ["response_comment"]
        widgets = {
            "response_comment": forms.Textarea(
                attrs={
                    "class": "response-textarea",
                    "placeholder": "Write your prayer response here...",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        response_comment = cleaned_data.get("response_comment", "").strip()

        if action == "respond" and not response_comment:
            raise forms.ValidationError("Response comment is required when responding.")

        cleaned_data["response_comment"] = response_comment
        return cleaned_data


class BulkFlaggedModerationForm(forms.Form):
    ACTION_CHOICES = [
        ("bulk_unflag", "Unflag"),
        ("bulk_archive", "Archive"),
    ]

    prayer_ids = forms.CharField(widget=forms.HiddenInput())
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.HiddenInput())

    def clean_prayer_ids(self):
        ids_str = self.cleaned_data["prayer_ids"]
        try:
            return [int(id.strip()) for id in ids_str.split(",") if id.strip()]
        except ValueError:
            raise forms.ValidationError("Invalid prayer IDs")


class PrayerResourceForm(forms.ModelForm):
    class Meta:
        model = PrayerResource
        fields = [
            "title",
            "description",
            "resource_type",
            "section",
            "url",
            "content",
            "is_active",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-input", "placeholder": "Resource title"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 3,
                    "placeholder": "Brief description",
                }
            ),
            "resource_type": forms.Select(attrs={"class": "form-select"}),
            "section": forms.Select(attrs={"class": "form-select"}),
            "url": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "https://..."}
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 8,
                    "placeholder": "Body text for text-type resources",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        resource_type = cleaned_data.get("resource_type")
        section = cleaned_data.get("section")
        if resource_type == PrayerResource.ResourceType.SECTION and section:
            raise forms.ValidationError("Sections cannot belong to another section.")
        return cleaned_data
