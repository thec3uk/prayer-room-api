from dateutil import parser
from django.utils.timezone import now
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateTimeWidget


from .models import PrayerPraiseRequest, Location

class PrayerRequestResource(resources.ModelResource):
    location = fields.Field(
        column_name='Location',
        attribute='location',
        widget=ForeignKeyWidget(Location, field='name'))
    content = fields.Field(
        column_name='prayer',
        attribute='content',
    )
    prayer_count = fields.Field(
        column_name='Prayer Count',
        attribute='prayer_count',
    )
    flagged_at = fields.Field(
        column_name="Date time prayer flagged",
        attribute='flagged_at',
        widget=DateTimeWidget(format='%d/%m/%Y %I:%M%p'),
    )
    # 15/1/2025 5:26pm
    created_at = fields.Field(
        widget=DateTimeWidget(format="%Y-%m-%dT%H:%M:%S"),
        column_name="created_at",
        attribute='created_at',
    )


    class Meta:
        model = PrayerPraiseRequest
        fields = (
            'id',
            'type',
            'name',
            'content',
            "created_at",
            'location',
            'prayer_count',
            'flagged_at',
            'archived_at',
        )

    def before_import_row(self, row, **kwargs):
        if row['Archived'] == "checked":
            row['archived_at'] = now()
        row['created_at'] = parser.parse(row['created_at']).isoformat()
