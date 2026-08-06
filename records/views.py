import json
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone

from .models import Patient, VisitRecord, ClinicStaffProfile, PatientEditRequest
from .forms import (
    PatientRegistrationForm, VisitRecordForm, PatientLookupForm,
    ClinicStaffRegistrationForm, PatientEditRequestForm, PatientSelfEditForm,
)
from .utils import generate_qr_code, extract_text_from_document
from .ai_assistant import answer_patient_question

def csrf_failure(request, reason=""):
    """Custom-branded page for CSRF failures, instead of Django's raw debug page."""
    return render(request, "records/error_page.html", {
        "title": "Session Expired",
        "message": "Your form session expired or the page was loaded from cache "
                    "(this often happens after using the browser's Back button).",
        "suggestion": "Please go back to the home page and try again — no data was lost.",
    }, status=403)
    
def home(request):
    """
    Unified entry point: shows the combined Login / Register-as-Patient /
    Register-as-Clinic-Staff page for anonymous visitors. Logged-in users get
    routed to the right dashboard automatically.
    """
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect("govt_dashboard")
        if request.user.groups.filter(name="ClinicStaff").exists():
            return redirect("clinic_dashboard")
        return redirect("patient_dashboard")
    return render(request, "records/auth_hub.html", {
        "patient_form": PatientRegistrationForm(),
        "staff_form": ClinicStaffRegistrationForm(),
    })

def csrf_failure(request, reason=""):
    """Custom-branded page for CSRF failures, instead of Django's raw debug page."""
    return render(request, "records/error_page.html", {
        "title": "Session Expired",
        "message": "Your form session expired or the page was loaded from cache "
                    "(this often happens after using the browser's Back button).",
        "suggestion": "Please go back to the home page and try again — no data was lost.",
    }, status=403)
    
# ---------- Registration & Auth ----------

def register_patient(request):
    if request.method == "POST":
        form = PatientRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            if User.objects.filter(username=username).exists():
                form.add_error("username", "This username is already taken.")
            else:
                user = User.objects.create_user(username=username, password=password)
                patient_group, _ = Group.objects.get_or_create(name="Patient")
                user.groups.add(patient_group)

                patient = form.save(commit=False)
                patient.user = user
                patient.save()
                generate_qr_code(patient)
                patient.save()

                login(request, user)
                return redirect("patient_dashboard")
    else:
        form = PatientRegistrationForm()

    return render(request, "records/auth_hub.html", {
        "patient_form": form, "staff_form": ClinicStaffRegistrationForm(), "active_tab": "patient",
    })


def register_clinic_staff(request):
    """
    Creates an INACTIVE user + a pending ClinicStaffProfile. They cannot log
    in until the Central Government (superuser) approves the request.
    """
    if request.method == "POST":
        form = ClinicStaffRegistrationForm(request.POST)
        username = request.POST.get("username")
        password = request.POST.get("password")

        if form.is_valid() and username and password:
            if User.objects.filter(username=username).exists():
                form.add_error(None, "This username is already taken.")
            else:
                user = User.objects.create_user(username=username, password=password)
                user.is_active = False  # locked out until approved
                user.save()

                profile = form.save(commit=False)
                profile.user = user
                profile.save()

                return render(request, "records/registration_submitted.html", {
                    "clinic_name": profile.clinic_name,
                })
    else:
        form = ClinicStaffRegistrationForm()

    return render(request, "records/auth_hub.html", {
        "patient_form": PatientRegistrationForm(), "staff_form": form, "active_tab": "staff",
    })


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user_obj = User.objects.filter(username=username).first()
        if user_obj and user_obj.check_password(password) and not user_obj.is_active:
            return render(request, "records/auth_hub.html", {
                "patient_form": PatientRegistrationForm(),
                "staff_form": ClinicStaffRegistrationForm(),
                "active_tab": "login",
                "error": "Your clinic staff account is still pending Central Government approval.",
            })

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("home")
        return render(request, "records/auth_hub.html", {
            "patient_form": PatientRegistrationForm(),
            "staff_form": ClinicStaffRegistrationForm(),
            "active_tab": "login",
            "error": "Invalid credentials.",
        })
    return render(request, "records/auth_hub.html", {
        "patient_form": PatientRegistrationForm(),
        "staff_form": ClinicStaffRegistrationForm(),
        "active_tab": "login",
    })


def logout_view(request):
    logout(request)
    return redirect("home")


# ---------- Patient side ----------

@login_required
def patient_dashboard(request):
    patient = get_object_or_404(Patient, user=request.user)
    pending_edits = patient.edit_requests.filter(status="pending")
    return render(request, "records/patient_dashboard.html", {
        "patient": patient,
        "visits": patient.visits.all(),
        "eligibility": patient.scheme_eligibility,
        "pending_edits": pending_edits,
    })

@login_required
def edit_my_profile(request):
    """
    Patient self-edits their OWN worksite/phone/language directly - no
    approval needed, since these are facts the patient knows first, not
    medical facts a clinic needs to verify.
    """
    patient = get_object_or_404(Patient, user=request.user)

    if request.method == "POST":
        form = PatientSelfEditForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "Your details have been updated.")
            return redirect("patient_dashboard")
    else:
        form = PatientSelfEditForm(instance=patient)

    return render(request, "records/edit_my_profile.html", {"form": form, "patient": patient})

@login_required
def review_edit_request(request, request_id, decision):
    """Patient approves or rejects a clinic-proposed change to their own record."""
    edit_req = get_object_or_404(PatientEditRequest, id=request_id, patient__user=request.user)

    if decision == "approve":
        patient = edit_req.patient
        for field, value in edit_req.changes.items():
            if hasattr(patient, field):
                setattr(patient, field, value)
        patient.save()
        edit_req.status = "approved"
    elif decision == "reject":
        edit_req.status = "rejected"

    edit_req.reviewed_at = timezone.now()
    edit_req.save()
    return redirect("patient_dashboard")


@login_required
def ask_assistant(request):
    """AJAX endpoint the chat widget calls."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    patient = get_object_or_404(Patient, user=request.user)
    data = json.loads(request.body or "{}")
    question = data.get("question", "").strip()
    language = data.get("language", "").strip() or None
    if not question:
        return JsonResponse({"error": "No question provided"}, status=400)

    answer, is_offline = answer_patient_question(patient, question, language_override=language)
    return JsonResponse({"answer": answer, "offline": is_offline})


# ---------- Clinic staff side ----------

def _is_clinic_staff(user):
    return user.groups.filter(name="ClinicStaff").exists() or user.is_staff

@login_required
def my_patients(request):
    """Shows clinic staff the patients THEY have personally treated (logged a visit for)."""
    if not _is_clinic_staff(request.user):
        return redirect("patient_dashboard")

    treated_patient_ids = VisitRecord.objects.filter(
        created_by=request.user
    ).values_list("patient_id", flat=True).distinct()

    patients = Patient.objects.filter(id__in=treated_patient_ids)

    patients_with_last_visit = []
    for p in patients:
        last_visit = p.visits.filter(created_by=request.user).first()
        patients_with_last_visit.append({"patient": p, "last_visit": last_visit})

    return render(request, "records/my_patients.html", {"patients": patients_with_last_visit})

@login_required
def clinic_dashboard(request):
    if not _is_clinic_staff(request.user):
        return redirect("patient_dashboard")

    patient = None
    form = PatientLookupForm()

    if request.method == "POST":
        form = PatientLookupForm(request.POST)
        if form.is_valid():
            health_id = form.cleaned_data["health_id"].strip()
            patient = Patient.objects.filter(health_id=health_id).first()
            if not patient:
                form.add_error("health_id", "No patient found with this Health ID.")
    elif request.GET.get("health_id"):
        # Lets edit_patient redirect straight back into the looked-up patient view
        health_id = request.GET["health_id"].strip()
        patient = Patient.objects.filter(health_id=health_id).first()
        form = PatientLookupForm(initial={"health_id": health_id})

    pending_edits = patient.edit_requests.filter(status="pending") if patient else None

    return render(request, "records/clinic_dashboard.html", {
        "form": form, "patient": patient, "pending_edits": pending_edits,
    })


@login_required
def add_visit(request, health_id):
    if not _is_clinic_staff(request.user):
        return redirect("patient_dashboard")

    patient = get_object_or_404(Patient, health_id=health_id)

    if request.method == "POST":
        form = VisitRecordForm(request.POST, request.FILES)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.patient = patient
            visit.created_by = request.user

            if visit.uploaded_document:
                visit.ocr_extracted_text = extract_text_from_document(visit.uploaded_document)

            visit.save()
            return redirect("clinic_dashboard")
    else:
        form = VisitRecordForm()

    return render(request, "records/add_visit.html", {"form": form, "patient": patient})


@login_required
def edit_patient(request, health_id):
    """
    Clinic staff PROPOSES changes to a patient's core details. Nothing is
    saved directly here - it creates a PatientEditRequest the patient must
    approve from their own dashboard.
    """
    if not _is_clinic_staff(request.user):
        return redirect("patient_dashboard")

    patient = get_object_or_404(Patient, health_id=health_id)

    if request.method == "POST":
        form = PatientEditRequestForm(request.POST)
        if form.is_valid():
            changes = {}
            for field in ["full_name", "phone_number", "current_worksite", "known_conditions", "known_allergies"]:
                new_val = form.cleaned_data.get(field)
                if new_val and new_val != getattr(patient, field):
                    changes[field] = new_val

            if changes:
                PatientEditRequest.objects.create(
                    patient=patient, requested_by=request.user,
                    changes=changes, reason=form.cleaned_data["reason"],
                )
                messages.success(
                    request,
                    f"Change request submitted for {patient.full_name}. "
                    f"It will apply once the patient approves it from their dashboard."
                )
            else:
                messages.info(request, "No changes were detected - nothing was submitted.")
            return redirect(f"{reverse('clinic_dashboard')}?health_id={patient.health_id}")
    else:
        form = PatientEditRequestForm(initial={
            "full_name": patient.full_name,
            "phone_number": patient.phone_number,
            "current_worksite": patient.current_worksite,
            "known_conditions": patient.known_conditions,
            "known_allergies": patient.known_allergies,
        })

    return render(request, "records/edit_patient.html", {"form": form, "patient": patient})


# ---------- Central Government (superuser) ----------

def _is_govt(user):
    return user.is_superuser


@user_passes_test(_is_govt, login_url="home")
def govt_dashboard(request):
    pending_staff = ClinicStaffProfile.objects.filter(status="pending")
    all_staff = ClinicStaffProfile.objects.exclude(status="pending")
    return render(request, "records/govt_dashboard.html", {
        "pending_staff": pending_staff,
        "all_staff": all_staff,
    })


@user_passes_test(_is_govt, login_url="home")
def review_staff_request(request, profile_id, decision):
    profile = get_object_or_404(ClinicStaffProfile, id=profile_id)
    clinic_group, _ = Group.objects.get_or_create(name="ClinicStaff")

    if decision == "approve":
        profile.user.is_active = True
        profile.user.save()
        profile.user.groups.add(clinic_group)
        profile.status = "approved"
    elif decision == "reject":
        profile.status = "rejected"

    profile.reviewed_by = request.user
    profile.reviewed_at = timezone.now()
    profile.save()
    return redirect("govt_dashboard")
