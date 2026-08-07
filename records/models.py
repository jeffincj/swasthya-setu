import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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
    """
    Core patient record - one per migrant worker.
    """

    health_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="patient_profile"
    )

    # ---------- Basic Profile ----------

    full_name = models.CharField(max_length=150)

    photo = models.ImageField(
        upload_to="patient_photos/",
        blank=True,
        null=True
    )

    phone_number = models.CharField(
        max_length=15,
        blank=True
    )

    home_state = models.CharField(
        max_length=100,
        help_text="Worker's native state, e.g. West Bengal"
    )

    current_worksite = models.CharField(
        max_length=200,
        help_text="Current work location in Kerala"
    )

    occupation = models.CharField(
        max_length=100,
        blank=True,
        help_text="Worker's occupation, e.g. Construction, Factory, Fishing"
    )

    preferred_language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default="hi"
    )

    income_bracket = models.CharField(
        max_length=20,
        choices=INCOME_BRACKET_CHOICES,
        default="below_2.5l"
    )

    # ---------- Medical Information ----------

    known_conditions = models.TextField(
        blank=True,
        help_text="Comma-separated, e.g. Hypertension, Type 2 Diabetes"
    )

    known_allergies = models.TextField(
        blank=True,
        help_text="Comma-separated allergies"
    )

    # ---------- Migrant Health Passport ----------

    blood_group = models.CharField(
        max_length=5,
        blank=True
    )

    vaccination_status = models.CharField(
        max_length=100,
        blank=True
    )

    emergency_contact = models.CharField(
        max_length=20,
        blank=True
    )

    insurance_status = models.CharField(
        max_length=100,
        blank=True
    )

    current_medicines = models.TextField(
        blank=True,
        help_text="Current medicines, comma-separated"
    )

    worksite_history = models.TextField(
        blank=True,
        help_text="Previous worksites, comma-separated"
    )

    # ---------- Health Risk Information ----------

    bmi = models.FloatField(
        null=True,
        blank=True
    )

    last_follow_up = models.DateField(
        null=True,
        blank=True
    )

    # ---------- QR Code ----------

    qr_code = models.ImageField(
        upload_to="qr_codes/",
        blank=True,
        null=True
    )

    registered_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.full_name} ({self.health_id})"

    # =========================================================
    # SCHEME ELIGIBILITY
    # =========================================================

    @property
    def scheme_eligibility(self):
        """
        Simple rule-based PM-JAY eligibility flag.
        Not a live government API.
        """

        chronic_flags = [
            "hypertension",
            "diabetes",
            "tb",
            "tuberculosis",
            "asthma"
        ]

        conditions = self.known_conditions.lower()

        has_chronic_condition = any(
            flag in conditions
            for flag in chronic_flags
        )

        if self.income_bracket == "below_2.5l":

            if has_chronic_condition:
                return {
                    "eligible": True,
                    "message": (
                        "You may be eligible for FULL coverage under "
                        "PM-JAY (Ayushman Bharat) due to your income "
                        "bracket and existing health condition. "
                        "Please visit your nearest CSC or ask clinic "
                        "staff for help applying."
                    ),
                }

            return {
                "eligible": True,
                "message": (
                    "You may be eligible for PM-JAY (Ayushman Bharat) "
                    "coverage based on your income bracket. Ask clinic "
                    "staff for help checking your card status."
                ),
            }

        elif (
            self.income_bracket == "2.5l_to_5l"
            and has_chronic_condition
        ):
            return {
                "eligible": "possible",
                "message": (
                    "You may be eligible for state-specific health "
                    "schemes given your condition. Please check with "
                    "clinic staff for Kerala-specific migrant worker "
                    "health schemes."
                ),
            }

        return {
            "eligible": False,
            "message": (
                "Based on current details, you may not qualify for "
                "PM-JAY, but other state schemes may apply. Please "
                "confirm with clinic staff."
            ),
        }

    # =========================================================
    # OCCUPATIONAL DISEASE PREDICTION
    # =========================================================

    @property
    def occupational_warnings(self):
        """
        Rule-based occupational health warnings.
        No machine learning is used.
        """

        occupation = (self.occupation or "").lower()

        warnings = []

        if any(
            word in occupation
            for word in [
                "construction",
                "mason",
                "labour",
                "labor",
                "building"
            ]
        ):
            warnings = [
                "Dust Exposure",
                "Heat Stroke",
                "Back Injury",
            ]

        elif any(
            word in occupation
            for word in [
                "factory",
                "industrial",
                "manufacturing",
                "plant"
            ]
        ):
            warnings = [
                "Chemical Exposure",
                "Respiratory Disease",
            ]

        elif any(
            word in occupation
            for word in [
                "fishing",
                "fisherman",
                "fisher"
            ]
        ):
            warnings = [
                "Skin Disease",
            ]

        elif any(
            word in occupation
            for word in [
                "driver",
                "driving"
            ]
        ):
            warnings = [
                "Back Pain",
                "Fatigue",
            ]

        elif any(
            word in occupation
            for word in [
                "farmer",
                "agriculture",
                "agricultural"
            ]
        ):
            warnings = [
                "Heat Exposure",
                "Pesticide Exposure",
                "Back Injury",
            ]

        return warnings

    # =========================================================
    # AI HEALTH RISK SCORE
    # =========================================================

    @property
    def health_risk_score(self):
        """
        Simple rule-based health risk score.

        Diabetes history       +20
        Hypertension history   +15
        Missed follow-up       +20
        BMI > 30               +15

        Maximum score = 70.
        """

        score = 0
        reasons = []

        conditions = (self.known_conditions or "").lower()

        # Diabetes
        if "diabetes" in conditions:
            score += 20
            reasons.append("Diabetes history (+20)")

        # Hypertension
        if "hypertension" in conditions:
            score += 15
            reasons.append("Hypertension history (+15)")

        # Missed follow-up
        if self.last_follow_up:
            if self.last_follow_up < timezone.localdate():
                score += 20
                reasons.append("Missed follow-up (+20)")

        # BMI
        if self.bmi is not None and self.bmi > 30:
            score += 15
            reasons.append("BMI above 30 (+15)")

        # Risk category
        if score <= 20:
            level = "Low"
            emoji = "🟢"

        elif score <= 40:
            level = "Moderate"
            emoji = "🟡"

        else:
            level = "High"
            emoji = "🔴"

        return {
            "score": score,
            "level": level,
            "emoji": emoji,
            "reasons": reasons,
        }


# =============================================================
# VISIT RECORD
# =============================================================

class VisitRecord(models.Model):
    """
    One entry per clinic visit - the actual medical history trail.
    """

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="visits"
    )

    clinic_name = models.CharField(
        max_length=200
    )

    visit_date = models.DateField(
        auto_now_add=True
    )

    diagnosis = models.CharField(
        max_length=300
    )

    medications_prescribed = models.TextField(
        help_text="e.g. Amlodipine 5mg - once daily"
    )

    doctor_notes = models.TextField(
        blank=True
    )

    follow_up_date = models.DateField(
        blank=True,
        null=True
    )

    uploaded_document = models.ImageField(
        upload_to="visit_documents/",
        blank=True,
        null=True,
        help_text="Photo of prescription or lab report"
    )

    ocr_extracted_text = models.TextField(
        blank=True,
        editable=False,
        help_text="Auto-filled by OCR when a document is uploaded"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="visits_logged"
    )

    def __str__(self):
        return (
            f"{self.patient.full_name} - "
            f"{self.clinic_name} - "
            f"{self.visit_date}"
        )

    class Meta:
        ordering = ["-visit_date"]


# =============================================================
# VISIT DOCUMENT
# =============================================================

class VisitDocument(models.Model):
    """
    One or more supporting documents attached to a single visit.
    """

    visit = models.ForeignKey(
        VisitRecord,
        on_delete=models.CASCADE,
        related_name="documents"
    )

    file = models.ImageField(
        upload_to="visit_documents/"
    )

    ocr_extracted_text = models.TextField(
        blank=True,
        editable=False
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return (
            f"Document for {self.visit} "
            f"({self.uploaded_at:%d %b %Y})"
        )


# =============================================================
# CLINIC STAFF PROFILE
# =============================================================

class ClinicStaffProfile(models.Model):
    """
    A clinic worker's registration request.
    New staff cannot log in until the Central Government
    superuser approves them.
    """

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="staff_profile"
    )

    clinic_name = models.CharField(
        max_length=200
    )

    phone_number = models.CharField(
        max_length=15,
        blank=True
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending"
    )

    requested_at = models.DateTimeField(
        auto_now_add=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_reviews"
    )

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.clinic_name} ({self.status})"
        )


# =============================================================
# PATIENT EDIT REQUEST
# =============================================================

class PatientEditRequest(models.Model):
    """
    When clinic staff wants to change a patient's existing
    details, the change waits for patient approval.
    """

    STATUS_CHOICES = [
        ("pending", "Awaiting Patient Approval"),
        ("approved", "Approved & Applied"),
        ("rejected", "Rejected by Patient"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="edit_requests"
    )

    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="edit_requests_made"
    )

    changes = models.JSONField(
        help_text="field_name -> new_value"
    )

    reason = models.CharField(
        max_length=300,
        blank=True
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending"
    )

    requested_at = models.DateTimeField(
        auto_now_add=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"Edit request for "
            f"{self.patient.full_name} ({self.status})"
        )


# =============================================================
# HEALTH METRIC
# =============================================================

class HealthMetric(models.Model):
    """
    Stores health measurements used for the Health Trend Dashboard.
    """

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="health_metrics"
    )

    recorded_at = models.DateField(
        auto_now_add=True
    )

    blood_pressure = models.CharField(
        max_length=20,
        blank=True
    )

    blood_sugar = models.FloatField(
        null=True,
        blank=True
    )

    weight = models.FloatField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"{self.patient.full_name} - "
            f"{self.recorded_at}"
        )

    class Meta:
        ordering = ["recorded_at"]


# =============================================================
# MEDICINE REMINDER
# =============================================================

class MedicineReminder(models.Model):
    """
    Medicine reminder system.

    Supports:
    - Daily medicines
    - Weekly medicines
    - Start and end dates
    - Tracking whether today's dose was taken
    - Recording the exact time the dose was taken
    """

    FREQUENCY_CHOICES = [
        ("daily", "Every Day"),
        ("weekly", "Every Week"),
    ]

    WEEKDAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="medicine_reminders"
    )

    medicine_name = models.CharField(
        max_length=200
    )

    dosage = models.CharField(
        max_length=100,
        blank=True
    )

    time = models.TimeField()

    # Daily or weekly
    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default="daily"
    )

    # Used only when frequency = weekly
    weekly_day = models.IntegerField(
        choices=WEEKDAY_CHOICES,
        null=True,
        blank=True
    )

    # First day of the medicine course
    start_date = models.DateField(
        default=timezone.localdate
    )

    # Last day of the medicine course.
    # Blank means there is no fixed end date.
    end_date = models.DateField(
        null=True,
        blank=True
    )

    # Today's dose status
    taken = models.BooleanField(
        default=False
    )

    # Exact date/time when the dose was taken
    taken_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.patient.full_name} - {self.medicine_name}"
        
class MedicineDose(models.Model):
    """
    Represents one specific scheduled dose of a medicine.

    Example:
    Paracetamol - 07 Aug - 08:00 AM - Taken at 08:04 AM
    """

    reminder = models.ForeignKey(
        MedicineReminder,
        on_delete=models.CASCADE,
        related_name="doses"
    )

    scheduled_date = models.DateField()

    scheduled_time = models.TimeField()

    taken = models.BooleanField(default=False)

    taken_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_date", "scheduled_time"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "reminder",
                    "scheduled_date",
                ],
                name="unique_medicine_dose_per_day"
            )
        ]

    def __str__(self):
        return (
            f"{self.reminder.medicine_name} - "
            f"{self.scheduled_date}"
        )