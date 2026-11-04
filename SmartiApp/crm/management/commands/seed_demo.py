from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from crm.models import Customer, Job, StaffMember


class Command(BaseCommand):
    help = "Load demo customers, staff and jobs into an empty database."

    @transaction.atomic
    def handle(self, *args, **options):
        if Customer.objects.exists() or StaffMember.objects.exists():
            self.stdout.write("Database already has data, nothing was added.")
            return

        Status = Customer.OnboardingStatus
        ada = Customer.objects.create(
            name="Ada Lovelace Ltd",
            phone="2079460001",
            email="office@adalovelace.example",
            address="1 St James's Square\nLondon\nSW1Y 4JU",
            onboarding_status=Status.ACTIVE,
        )
        brunel = Customer.objects.create(
            name="Brunel Engineering",
            phone="1174960002",
            email="hello@brunel.example",
            address="2 Temple Way\nBristol\nBS1 6QF",
            onboarding_status=Status.IN_PROGRESS,
        )
        Customer.objects.create(
            name="Curie Laboratories",
            phone="1614960003",
            address="3 Oxford Road\nManchester\nM13 9PL",
        )

        fitter = StaffMember.objects.create(
            name="Sam Fitter", role=StaffMember.Role.FITTER, phone="7700900001"
        )
        engineer = StaffMember.objects.create(
            name="Alex Engineer", role=StaffMember.Role.ENGINEER, phone="7700900002"
        )

        today = timezone.localdate()
        Job.objects.create(
            customer=ada,
            staff=engineer,
            job_type=Job.JobType.MAINTENANCE,
            scheduled_date=today - timedelta(days=7),
            scheduled_time=time(9, 0),
            description="Annual service.",
            status=Job.Status.COMPLETED,
        )
        Job.objects.create(
            customer=brunel,
            staff=fitter,
            job_type=Job.JobType.INSTALLATION,
            scheduled_date=today + timedelta(days=1),
            scheduled_time=time(10, 30),
            description="Install new unit.",
            status=Job.Status.IN_PROGRESS,
        )
        Job.objects.create(
            customer=ada,
            staff=engineer,
            job_type=Job.JobType.MAINTENANCE,
            scheduled_date=today + timedelta(days=3),
            scheduled_time=time(14, 0),
            description="Investigate reported fault.",
        )
        self.stdout.write(self.style.SUCCESS("Demo data loaded."))
