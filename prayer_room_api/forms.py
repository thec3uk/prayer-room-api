from django import forms


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
