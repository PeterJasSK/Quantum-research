from django.contrib import admin
from .models import QuantumShotResult

@admin.register(QuantumShotResult)
class QuantumShotResultAdmin(admin.ModelAdmin):
    list_display = ("id", "shot_index", "bits", "used_bits" , "batch_id", "created_at")
    list_filter = ("batch_id", "created_at")
    search_fields = ("bits", "batch_id")

