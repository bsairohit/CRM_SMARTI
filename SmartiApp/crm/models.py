from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse

phone_validator = RegexValidator(
    regex=r"^[0-9]{10}$",
    message="Enter a phone number of exactly 10 digits, with no spaces or symbols.",
)


class Customer(models.Model):
    class OnboardingStatus(models.TextChoices):
        NEW_ENQUIRY = "new_enquiry", "New Enquiry"
        IN_PROGRESS = "in_progress", "In Progress"
        ACTIVE = "active", "Active"

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=10, validators=[phone_validator])
    email = models.EmailField(blank=True)
    address = models.TextField()
    onboarding_status = models.CharField(
        max_length=20,
        choices=OnboardingStatus.choices,
        default=OnboardingStatus.NEW_ENQUIRY,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("customer_detail", args=[self.pk])


class StaffMember(models.Model):
    class Role(models.TextChoices):
        FITTER = "fitter", "Fitter"
        ENGINEER = "engineer", "Maintenance Engineer"

    name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices)
    phone = models.CharField(max_length=10, blank=True, validators=[phone_validator])
    # Staff are deactivated rather than deleted so their job history is kept.
    is_active = models.BooleanField("active", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "staff"

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

    def get_absolute_url(self):
        return reverse("staff_detail", args=[self.pk])


class Job(models.Model):
    """A scheduled visit: this one model is both the appointment and the job."""

    class JobType(models.TextChoices):
        INSTALLATION = "installation", "Installation"
        MAINTENANCE = "maintenance", "Maintenance"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    # PROTECT: a customer or staff member with job history cannot be deleted.
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="jobs")
    staff = models.ForeignKey(StaffMember, on_delete=models.PROTECT, related_name="jobs")
    job_type = models.CharField(max_length=20, choices=JobType.choices)
    scheduled_date = models.DateField("date")
    scheduled_time = models.TimeField("time")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_date", "scheduled_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["staff", "scheduled_date", "scheduled_time"],
                name="unique_staff_time_slot",
                violation_error_message="This staff member already has a job at that date and time.",
            )
        ]

    def __str__(self):
        return f"{self.get_job_type_display()} for {self.customer} on {self.scheduled_date}"
