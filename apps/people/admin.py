from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Person

@admin.register(Person)
class PersonAdmin(ModelAdmin):
    list_display = ("full_name", "iin","external_id","user")
    search_fields = ("full_name", "iin")

