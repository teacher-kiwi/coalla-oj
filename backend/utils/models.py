from django.db.models import JSONField  # NOQA
from django.db import models

from utils.xss_filter import clean_html


class RichTextField(models.TextField):
    def get_prep_value(self, value):
        return clean_html(value)
