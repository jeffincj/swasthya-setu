from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("records", "0005_visitdocument")]

    operations = [
        migrations.AddField(model_name="patient", name="blood_group", field=models.CharField(choices=[("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"), ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-"), ("unknown", "Unknown")], default="unknown", max_length=10)),
        migrations.AddField(model_name="patient", name="occupation", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="patient", name="vaccination_status", field=models.CharField(default="Not recorded", blank=True, max_length=120)),
        migrations.AddField(model_name="patient", name="emergency_contact", field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name="patient", name="insurance_status", field=models.CharField(default="Not recorded", blank=True, max_length=120)),
        migrations.AddField(model_name="patient", name="worksite_history", field=models.TextField(blank=True, help_text="One worksite per line, oldest to newest")),
        migrations.AddField(model_name="patient", name="bmi", field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
        migrations.CreateModel(
            name="HealthMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recorded_at", models.DateField()),
                ("systolic_bp", models.PositiveIntegerField(blank=True, null=True)),
                ("diastolic_bp", models.PositiveIntegerField(blank=True, null=True)),
                ("blood_sugar", models.DecimalField(blank=True, decimal_places=1, max_digits=6, null=True)),
                ("weight", models.DecimalField(blank=True, decimal_places=1, max_digits=6, null=True)),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="health_metrics", to="records.patient")),
            ],
            options={"ordering": ["recorded_at"]},
        ),
        migrations.CreateModel(
            name="MedicineReminder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("medicine_name", models.CharField(max_length=150)),
                ("dosage", models.CharField(blank=True, max_length=100)),
                ("time", models.TimeField()),
                ("notes", models.CharField(blank=True, max_length=250)),
                ("active", models.BooleanField(default=True)),
                ("last_taken_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("patient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="medicine_reminders", to="records.patient")),
            ],
            options={"ordering": ["time", "medicine_name"]},
        ),
    ]
