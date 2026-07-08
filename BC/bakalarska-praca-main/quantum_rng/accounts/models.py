from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class RNGHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    generator_type = models.CharField(max_length=50)  # e.g. dice, coin, custom
    params = models.JSONField()  # store range or dice type, count
    result = models.JSONField()   # store result array / number

    def __str__(self):
        return f"{self.user.username} - {self.generator_type} @ {self.timestamp}"


class Profile(models.Model):
    USER_TYPES = [
        ("standard", "Standard"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default="standard")
    token = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} ({self.user_type})"

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()