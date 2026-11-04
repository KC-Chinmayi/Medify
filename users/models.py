from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    has_diabetes = models.BooleanField(default=False)
    has_thyroid = models.BooleanField(default=False)
    other_conditions = models.TextField(blank=True, help_text="List any other medical conditions or allergies")

    def __str__(self):
        return f"{self.user.username}'s Profile"
