from django.contrib import admin
from .models import Patient, VisitRecord, ClinicStaffProfile, PatientEditRequest


class VisitRecordInline(admin.TabularInline):
    model = VisitRecord
    extra = 0
    readonly_fields = ["ocr_extracted_text"]


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["full_name", "health_id", "home_state", "current_worksite", "preferred_language", "registered_at"]
    search_fields = ["full_name", "health_id", "home_state", "current_worksite"]
    list_filter = ["home_state", "preferred_language", "income_bracket"]
    inlines = [VisitRecordInline]


@admin.register(VisitRecord)
class VisitRecordAdmin(admin.ModelAdmin):
    list_display = ["patient", "clinic_name", "visit_date", "diagnosis", "follow_up_date"]
    search_fields = ["patient__full_name", "clinic_name", "diagnosis"]
    list_filter = ["clinic_name", "visit_date"]


@admin.register(ClinicStaffProfile)
class ClinicStaffProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "clinic_name", "status", "requested_at", "reviewed_by"]
    list_filter = ["status"]


@admin.register(PatientEditRequest)
class PatientEditRequestAdmin(admin.ModelAdmin):
    list_display = ["patient", "requested_by", "status", "requested_at"]
    list_filter = ["status"]
