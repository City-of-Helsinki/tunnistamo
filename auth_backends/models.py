from django.db import models
from parler.models import TranslatableModel, TranslatedFields


class SuomiFiUserAttribute(models.Model):
    friendly_name = models.CharField(max_length=100, unique=True)
    uri = models.CharField(max_length=100, unique=True)
    name = models.TextField()
    description = models.TextField()


class SuomiFiAccessLevel(TranslatableModel):
    translations = TranslatedFields(
        name=models.CharField(max_length=100),
        description=models.TextField(blank=True)
    )
    shorthand = models.CharField(max_length=100, unique=True)
    attributes = models.ManyToManyField(SuomiFiUserAttribute)
