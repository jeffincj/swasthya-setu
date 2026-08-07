# Swasthya Setu - Health Feature Upgrade

Added:
1. Migrant Health Passport
2. Rule-based Occupational Disease Prediction
3. Rule-based AI Health Risk Score
4. Emergency SOS QR
5. Health Trend Dashboard
6. Medicine Reminder DB + Taken action

## Apply
From the project root:

```bash
python manage.py migrate
python manage.py runserver
```

No new Python package is required beyond the existing `qrcode` and Django dependencies.

### New routes
- `/dashboard/health-passport/`
- `/dashboard/emergency-qr/`
- `/dashboard/medicine-reminders/`
- `/dashboard/health-trends/`

### Notes
- Passport uses browser Print / Save as PDF, so no PDF library is required.
- Trend charts use Chart.js CDN and show demo data if no HealthMetric records exist.
- Risk scoring is a screening aid, not a medical diagnosis.
- SOS QR contains only blood group, allergies, current medicines, and emergency contact.
