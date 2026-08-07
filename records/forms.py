from django import forms
from django.contrib.auth.models import User
from .models import (
    Patient,
    VisitRecord,
    ClinicStaffProfile,
    PatientEditRequest,
    VisitDocument,
    HealthMetric,
    MedicineReminder,
)


class PatientRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Patient
        fields = [
            "full_name", "photo", "phone_number", "home_state",
            "current_worksite", "preferred_language", "income_bracket",
            "known_conditions", "known_allergies",
        ]
        widgets = {
            "known_conditions": forms.Textarea(attrs={"rows": 2, "placeholder": "e.g. Hypertension, Diabetes"}),
            "known_allergies": forms.Textarea(attrs={"rows": 2, "placeholder": "e.g. Penicillin"}),
        }


class VisitRecordForm(forms.ModelForm):
    class Meta:
        model = VisitRecord
        fields = [
            "clinic_name", "diagnosis", "medications_prescribed",
            "doctor_notes", "follow_up_date",
        ]
        widgets = {
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
            "doctor_notes": forms.Textarea(attrs={"rows": 3}),
            "medications_prescribed": forms.Textarea(attrs={"rows": 2}),
        }


class PatientLookupForm(forms.Form):
    health_id = forms.CharField(
        label="Scan or Enter Health ID",
        widget=forms.TextInput(attrs={"placeholder": "Paste QR value or Health ID here"}),
    )


class ClinicStaffRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = ClinicStaffProfile
        fields = ["clinic_name", "phone_number"]


class PatientEditRequestForm(forms.Form):
    """Clinic staff fills this to PROPOSE changes - not applied until the patient approves."""
    full_name = forms.CharField(required=False)
    phone_number = forms.CharField(required=False)
    current_worksite = forms.CharField(required=False)
    known_conditions = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    known_allergies = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Why is this change needed?"}),
        label="Reason for change (shown to patient)",
    )
class PatientSelfEditForm(forms.ModelForm):
    """
    Patients can self-edit these fields directly, no approval needed - these
    are personal-circumstance facts the patient always knows first (they know
    they moved before any clinic does). Medical fields (conditions, allergies)
    stay clinic-controlled via PatientEditRequestForm above, since those are
    medical facts, not personal circumstances - letting patients self-edit
    their own diagnosed conditions would be a real misrepresentation risk.
    """
    class Meta:
        model = Patient
        fields = ["phone_number", "current_worksite", "preferred_language"]
        
class MedicineReminderForm(forms.ModelForm):

    class Meta:
        model = MedicineReminder
        fields = [
            "medicine_name",
            "dosage",
            "time",
            "frequency",
            "weekly_day",
            "start_date",
            "end_date",
        ]

        widgets = {
            "time": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "type": "time"
                }
            ),

            "start_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date"
                }
            ),

            "end_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date"
                }
            ),

            "weekly_day": forms.Select(
                choices=[
                    ("", "Select day"),
                    (0, "Monday"),
                    (1, "Tuesday"),
                    (2, "Wednesday"),
                    (3, "Thursday"),
                    (4, "Friday"),
                    (5, "Saturday"),
                    (6, "Sunday"),
                ]
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        frequency = cleaned_data.get("frequency")
        weekly_day = cleaned_data.get("weekly_day")

        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date",
                "End date cannot be before start date."
            )

        if frequency == "weekly" and weekly_day is None:
            self.add_error(
                "weekly_day",
                "Please select a day for weekly medicines."
            )

        return cleaned_data