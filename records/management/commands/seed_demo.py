from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from records.models import Patient, VisitRecord, ClinicStaffProfile
from records.utils import generate_qr_code


class Command(BaseCommand):
    help = "Sets up demo data: ClinicStaff group, a clinic login, and one sample patient (Ramesh)."

    def handle(self, *args, **kwargs):
        # 0. Central Government superuser
        if not User.objects.filter(username="centralgov").exists():
            User.objects.create_superuser(username="centralgov", password="demo1234", email="")
            self.stdout.write(self.style.SUCCESS("Created Central Government login: centralgov / demo1234"))
        else:
            self.stdout.write("Central Government user already exists.")

        # 1. ClinicStaff group + demo clinic user (pre-approved for convenience)
        clinic_group, _ = Group.objects.get_or_create(name="ClinicStaff")

        if not User.objects.filter(username="clinicstaff").exists():
            clinic_user = User.objects.create_user(
                username="clinicstaff", password="demo1234", is_staff=True
            )
            clinic_user.groups.add(clinic_group)
            ClinicStaffProfile.objects.create(
                user=clinic_user, clinic_name="Kochi Community Health Camp",
                phone_number="9876511111", status="approved",
            )
            self.stdout.write(self.style.SUCCESS("Created clinic staff login: clinicstaff / demo1234 (pre-approved)"))
        else:
            self.stdout.write("Clinic staff user already exists.")

        # 1b. A SECOND clinic staff request left PENDING, to demo the approval flow live
        if not User.objects.filter(username="newclinic_demo").exists():
            pending_user = User.objects.create_user(username="newclinic_demo", password="demo1234")
            pending_user.is_active = False
            pending_user.save()
            ClinicStaffProfile.objects.create(
                user=pending_user, clinic_name="Thrissur Migrant Worker Clinic",
                phone_number="9876522222", status="pending",
            )
            self.stdout.write(self.style.SUCCESS(
                "Created a PENDING clinic staff request (newclinic_demo) - approve it live in your demo as Central Government."
            ))

        # 2. Demo patient: Ramesh
        if not User.objects.filter(username="ramesh_demo").exists():
            patient_group, _ = Group.objects.get_or_create(name="Patient")
            ramesh_user = User.objects.create_user(username="ramesh_demo", password="demo1234")
            ramesh_user.groups.add(patient_group)

            ramesh = Patient.objects.create(
                user=ramesh_user,
                full_name="Ramesh Halder",
                phone_number="9876500000",
                home_state="West Bengal",
                current_worksite="Kochi Construction Site, Kerala",
                preferred_language="bn",
                income_bracket="below_2.5l",
                known_conditions="Hypertension",
                known_allergies="Penicillin",
            )
            generate_qr_code(ramesh)
            ramesh.save()

            VisitRecord.objects.create(
                patient=ramesh,
                clinic_name="Kochi Community Health Camp",
                diagnosis="Mild Hypertension",
                medications_prescribed="Amlodipine 5mg - once daily, morning",
                doctor_notes="Advised low-sodium diet, follow-up in 3 months.",
                follow_up_date=date.today() + timedelta(days=90),
            )

            self.stdout.write(self.style.SUCCESS(
                f"Created demo patient Ramesh (login: ramesh_demo / demo1234) "
                f"with Health ID: {ramesh.health_id}"
            ))
        else:
            self.stdout.write("Demo patient already exists.")

        self.stdout.write(self.style.SUCCESS("\nDemo setup complete. You're ready to present."))
