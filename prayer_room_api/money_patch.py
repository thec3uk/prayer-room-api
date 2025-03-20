

def model_dict(model):
    """
    This is a hack so I can customise the serialization process
    """
    from .serializers import PrayerPraiseRequestWebhookSerializer
    if model._meta.model_name == 'prayerpraiserequest':
        serializer_class = PrayerPraiseRequestWebhookSerializer
    model.refresh_from_db()
    return serializer_class(instance=model).data
