from django.contrib import admin

from .models import JournalEntry, MortalityReason, MortalityRecord, LiceCount, VaccinationType, Treatment, SampleType

# Register your models here.
admin.site.register(JournalEntry)
admin.site.register(MortalityReason)
admin.site.register(MortalityRecord)
admin.site.register(LiceCount)
admin.site.register(VaccinationType)
admin.site.register(Treatment)
admin.site.register(SampleType)
