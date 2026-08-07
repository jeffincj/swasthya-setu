import uuid
from django.db import models
from django.contrib.auth.models import User


LANGUAGE_CHOICES = [
    ("en", "English"),
    ("hi", "Hindi"),
    ("ml", "Malayalam"),
    ("bn", "Bengali"),
    ("or", "Odia"),
    ("as", "Assamese"),
]

INCOME_BRACKET_CHOICES = [
    ("below_2.5l", "Below ₹2.5 Lakh / year"),
    ("2.5l_to_5l", "₹2.5 Lakh - ₹5 Lakh / year"),
    ("above_5l", "Above ₹5 Lakh / year"),
]


class Patient(models.Model):
    """Core patient record - one per migrant worker."""
    health_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")

    full_name = models.CharField(max_length=150)
    photo = models.ImageField(upload_to="patient_photos/", blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    home_state = models.CharField(max_length=100, help_text="Worker's native state, e.g. West Bengal")
    current_worksite = models.CharField(max_length=200, help_text="Current work location in Kerala")
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="hi")
    income_bracket = models.CharField(max_length=20, choices=INCOME_BRACKET_CHOICES, default="below_2.5l")

    known_conditions = models.TextField(
        blank=True, help_text="Comma-separated, e.g. Hypertension, Type 2 Diabetes"
    )
    known_allergies = models.TextField(blank=True, help_text="Comma-separated allergies")

    qr_code = models.ImageField(upload_to="qr_codes/", blank=True, null=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.health_id})"

    @property
    def scheme_eligibility(self):
        """Simple rule-based PM-JAY eligibility flag. Not a live government API."""
        chronic_flags = ["hypertension", "diabetes", "tb", "tuberculosis", "asthma"]
        has_chronic_condition = any(
            flag in self.known_conditions.lower() for flag in chronic_flags
        )
        if self.income_bracket == "below_2.5l":
            if has_chronic_condition:
                return {
                    "eligible": True,
                    "message": "You may be eligible for FULL coverage under PM-JAY (Ayushman Bharat) "
                                "due to your income bracket and existing health condition. "
                                "Please visit your nearest CSC or ask clinic staff for help applying.",
                }
            return {
                "eligible": True,
                "message": "You may be eligible for PM-JAY (Ayushman Bharat) coverage based on your "
                            "income bracket. Ask clinic staff for help checking your card status.",
            }
        elif self.income_bracket == "2.5l_to_5l" and has_chronic_condition:
            return {
                "eligible": "possible",
                "message": "You may be eligible for state-specific health schemes given your condition. "
                            "Please check with clinic staff for Kerala-specific migrant worker health schemes.",
            }
        return {
            "eligible": False,
            "message": "Based on current details, you may not qualify for PM-JAY, but other state "
                        "schemes may apply. Please confirm with clinic staff.",
        }


class VisitRecord(models.Model):
    """One entry per clinic visit - the actual medical history trail."""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visits")
    clinic_name = models.CharField(max_length=200)
    visit_date = models.DateField(auto_now_add=True)
    diagnosis = models.CharField(max_length=300)
    medications_prescribed = models.TextField(help_text="e.g. Amlodipine 5mg - once daily")
    doctor_notes = models.TextField(blank=True)
    follow_up_date = models.DateField(blank=True, null=True)

    uploaded_document = models.ImageField(
        upload_to="visit_documents/", blank=True, null=True,
        help_text="Photo of prescription or lab report"
    )
    ocr_extracted_text = models.TextField(
        blank=True, editable=False,
        help_text="Auto-filled by OCR when a document is uploaded"
    )

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="visits_logged")

    def __str__(self):
        return f"{self.patient.full_name} - {self.clinic_name} - {self.visit_date}"

    class Meta:
        ordering = ["-visit_date"]


class VisitDocument(models.Model):
    """
    One or more supporting documents (prescriptions, lab reports) attached
    to a single visit. Replaces the old single uploaded_document field -
    clinic staff can now upload several files at once for one visit.
    """
    visit = models.ForeignKey(VisitRecord, on_delete=models.CASCADE, related_name="documents")
    file = models.ImageField(upload_to="visit_documents/")
    ocr_extracted_text = models.TextField(blank=True, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"Document for {self.visit} ({self.uploaded_at:%d %b %Y})"


class ClinicStaffProfile(models.Model):
    """
    A clinic worker's registration request. New staff cannot log in until the
    Central Government (a superuser) approves them - the account stays
    inactive until then.
    """
    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    clinic_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="staff_reviews"
    )

    def __str__(self):
        return f"{self.user.username} - {self.clinic_name} ({self.status})"


class PatientEditRequest(models.Model):
    """
    When clinic staff wants to change a PATIENT's existing details (not add a
    new visit - that's just an addition), the change is held here until the
    patient themselves approves it. This is the "patient data sovereignty"
    feature - clinic staff cannot unilaterally rewrite a patient's record.
    """
    STATUS_CHOICES = [
        ("pending", "Awaiting Patient Approval"),
        ("approved", "Approved & Applied"),
        ("rejected", "Rejected by Patient"),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="edit_requests")
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="edit_requests_made")
    changes = models.JSONField(help_text="field_name -> new_value")
    reason = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Edit request for {self.patient.full_name} ({self.status})"