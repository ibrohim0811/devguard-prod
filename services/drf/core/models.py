from django.db import models

from users.models import WebApplications


class TestHistory(models.Model):
    class StatusChoices(models.TextChoices):
        PASSED = 'passed', 'passed'
        FAILED = 'failed', 'failed'
        NORMAL = 'normal', 'normal'

    web = models.ForeignKey(WebApplications, on_delete=models.CASCADE, related_name="history")
    status = models.CharField(max_length=25, choices=StatusChoices.choices)
    about = models.TextField()


