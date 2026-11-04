from django.db import models

class AILog(models.Model):
    symptoms = models.TextField()
    response_advice = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Search at {self.timestamp}"
