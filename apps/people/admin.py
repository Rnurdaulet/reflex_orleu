from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Person

@admin.register(Person)
class PersonAdmin(ModelAdmin):
    list_display = ("full_name", "iin")
    search_fields = ("full_name", "iin")
    list_per_page = 25
    fields = ("iin", "full_name", "signature")

