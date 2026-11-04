from datetime import time, timedelta
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import CustomerForm
from .models import Customer, Job, StaffMember


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = Customer.objects.create(
            name="Test Customer", phone="2079460000", address="1 Test Street"
        )
        cls.fitter = StaffMember.objects.create(name="Sam", role=StaffMember.Role.FITTER)
        cls.tomorrow = timezone.localdate() + timedelta(days=1)

    def job_data(self, **overrides):
        data = {
            "customer": self.customer.pk,
            "staff": self.fitter.pk,
            "job_type": Job.JobType.INSTALLATION,
            "scheduled_date": self.tomorrow.isoformat(),
            "scheduled_time": "10:00",
            "description": "",
            "status": Job.Status.PENDING,
        }
        return data | overrides

    def make_job(self, **overrides):
        fields = {
            "customer": self.customer,
            "staff": self.fitter,
            "job_type": Job.JobType.INSTALLATION,
            "scheduled_date": self.tomorrow,
            "scheduled_time": time(10, 0),
        }
        return Job.objects.create(**fields | overrides)


class CustomerTests(BaseTestCase):
    def test_create_customer_defaults_to_new_enquiry_and_redirects_to_record(self):
        response = self.client.post(
            reverse("customer_create"),
            {
                "name": "New Co",
                "phone": "2079460001",
                "email": "a@example.com",
                "address": "2 Road",
                "onboarding_status": "new_enquiry",
            },
        )
        customer = Customer.objects.get(name="New Co")
        self.assertRedirects(response, customer.get_absolute_url())
        self.assertEqual(customer.onboarding_status, Customer.OnboardingStatus.NEW_ENQUIRY)

    def test_invalid_customer_is_rejected_with_errors(self):
        response = self.client.post(
            reverse("customer_create"),
            {"name": "", "phone": "not a phone", "email": "nope", "address": ""},
        )
        self.assertEqual(response.status_code, 200)
        for field in ("name", "phone", "email", "address"):
            self.assertIn(field, response.context["form"].errors)
        self.assertEqual(Customer.objects.count(), 1)

    def test_phone_must_be_exactly_10_digits(self):
        cases = {
            "2079460001": True,
            "207946000": False,
            "20794600012": False,
            "207 946 00": False,
            "+207946000": False,
            "20794600ab": False,
        }
        for phone, is_valid in cases.items():
            with self.subTest(phone=phone):
                form = CustomerForm(
                    {
                        "name": "Co",
                        "phone": phone,
                        "address": "2 Road",
                        "onboarding_status": "new_enquiry",
                    }
                )
                self.assertEqual("phone" not in form.errors, is_valid)

    def test_list_and_detail_show_customer(self):
        self.assertContains(self.client.get(reverse("customer_list")), "Test Customer")
        self.assertContains(self.client.get(self.customer.get_absolute_url()), "1 Test Street")

    def test_edit_customer(self):
        self.client.post(
            reverse("customer_edit", args=[self.customer.pk]),
            {
                "name": "Renamed",
                "phone": "2079460000",
                "email": "",
                "address": "1 Test Street",
                "onboarding_status": "active",
            },
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.name, "Renamed")

    def test_missing_customer_returns_404(self):
        self.assertEqual(self.client.get(reverse("customer_detail", args=[9999])).status_code, 404)

    def test_update_onboarding_status(self):
        url = reverse("customer_update_status", args=[self.customer.pk])
        self.client.post(url, {"onboarding_status": "in_progress"})
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.onboarding_status, Customer.OnboardingStatus.IN_PROGRESS)

    def test_invalid_onboarding_status_is_not_saved(self):
        url = reverse("customer_update_status", args=[self.customer.pk])
        self.client.post(url, {"onboarding_status": "bogus"})
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.onboarding_status, Customer.OnboardingStatus.NEW_ENQUIRY)

    def test_status_update_requires_post(self):
        url = reverse("customer_update_status", args=[self.customer.pk])
        self.assertEqual(self.client.get(url).status_code, 405)


class StaffTests(BaseTestCase):
    def test_create_and_list_staff(self):
        self.client.post(
            reverse("staff_create"),
            {"name": "Alex", "role": "engineer", "phone": "", "is_active": "on"},
        )
        self.assertContains(self.client.get(reverse("staff_list")), "Maintenance Engineer")

    def test_staff_page_shows_assigned_jobs(self):
        self.make_job()
        response = self.client.get(self.fitter.get_absolute_url())
        self.assertContains(response, "Test Customer")


class JobTests(BaseTestCase):
    def test_book_job(self):
        response = self.client.post(reverse("job_create"), self.job_data())
        self.assertRedirects(response, reverse("upcoming_jobs"))
        self.assertEqual(Job.objects.get().staff, self.fitter)

    def test_job_form_preselects_customer_from_query_string(self):
        response = self.client.get(reverse("job_create"), {"customer": self.customer.pk})
        self.assertEqual(response.context["form"]["customer"].value(), str(self.customer.pk))

    def test_cannot_book_job_in_the_past(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        response = self.client.post(
            reverse("job_create"), self.job_data(scheduled_date=yesterday.isoformat())
        )
        self.assertIn("scheduled_date", response.context["form"].errors)
        self.assertFalse(Job.objects.exists())

    def test_past_job_can_still_be_edited_if_schedule_is_unchanged(self):
        last_week = timezone.localdate() - timedelta(days=7)
        job = self.make_job(scheduled_date=last_week)
        response = self.client.post(
            reverse("job_edit", args=[job.pk]),
            self.job_data(scheduled_date=last_week.isoformat(), description="Notes added"),
        )
        self.assertRedirects(response, reverse("job_list"))
        job.refresh_from_db()
        self.assertEqual(job.description, "Notes added")

    def test_staff_cannot_be_double_booked(self):
        self.make_job()
        response = self.client.post(reverse("job_create"), self.job_data())
        self.assertContains(response, "already has a job at that date and time")
        self.assertEqual(Job.objects.count(), 1)

    def test_inactive_staff_cannot_be_assigned_to_a_new_job(self):
        inactive = StaffMember.objects.create(
            name="Gone", role=StaffMember.Role.FITTER, is_active=False
        )
        response = self.client.post(reverse("job_create"), self.job_data(staff=inactive.pk))
        self.assertIn("staff", response.context["form"].errors)

    def test_job_keeps_its_assignee_after_they_are_deactivated(self):
        inactive = StaffMember.objects.create(
            name="Gone", role=StaffMember.Role.FITTER, is_active=False
        )
        job = self.make_job(staff=inactive)
        response = self.client.post(
            reverse("job_edit", args=[job.pk]),
            self.job_data(staff=inactive.pk, description="Still editable"),
        )
        self.assertEqual(response.status_code, 302)

    def test_upcoming_hides_past_and_completed_jobs_and_sorts_soonest_first(self):
        today = timezone.localdate()
        later = self.make_job(scheduled_date=today + timedelta(days=5))
        sooner = self.make_job(scheduled_date=today + timedelta(days=2))
        self.make_job(scheduled_date=today - timedelta(days=1))
        self.make_job(scheduled_date=today + timedelta(days=3), status=Job.Status.COMPLETED)

        response = self.client.get(reverse("upcoming_jobs"))
        self.assertEqual(list(response.context["jobs"]), [sooner, later])

    def test_status_update_and_return_to_previous_page(self):
        job = self.make_job()
        response = self.client.post(
            reverse("job_update_status", args=[job.pk]),
            {"status": "completed", "next": reverse("upcoming_jobs")},
        )
        self.assertRedirects(response, reverse("upcoming_jobs"))
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.COMPLETED)

    def test_invalid_job_status_is_not_saved(self):
        job = self.make_job()
        self.client.post(reverse("job_update_status", args=[job.pk]), {"status": "bogus"})
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PENDING)

    def test_status_update_ignores_off_site_redirect(self):
        job = self.make_job()
        response = self.client.post(
            reverse("job_update_status", args=[job.pk]),
            {"status": "completed", "next": "https://evil.example/"},
        )
        self.assertRedirects(response, reverse("job_list"))

    def test_job_list_filters_by_status(self):
        pending = self.make_job()
        self.make_job(scheduled_time=time(11, 0), status=Job.Status.COMPLETED)
        response = self.client.get(reverse("job_list"), {"status": "pending"})
        self.assertEqual(list(response.context["jobs"]), [pending])

    def test_job_table_renders_status_options(self):
        self.make_job()
        response = self.client.get(reverse("upcoming_jobs"))
        self.assertContains(response, '<option value="in_progress">In Progress</option>', html=True)


class ErrorPageTests(TestCase):
    def test_unknown_url_shows_custom_404_page(self):
        response = self.client.get("/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Page not found", status_code=404)

    def test_missing_record_shows_custom_404_page(self):
        response = self.client.get(reverse("customer_detail", args=[9999]))
        self.assertTemplateUsed(response, "404.html")

    def test_unexpected_error_shows_custom_500_page(self):
        self.client.raise_request_exception = False
        with patch("crm.views.render", side_effect=RuntimeError("boom")):
            with self.assertLogs("django.request", level="ERROR"):
                response = self.client.get(reverse("customer_list"))
        self.assertContains(response, "Something went wrong", status_code=500)
        self.assertNotContains(response, "boom", status_code=500)


class SeedCommandTests(TestCase):
    def test_seed_loads_data_once(self):
        call_command("seed_demo", verbosity=0)
        job_count = Job.objects.count()
        self.assertGreater(job_count, 0)
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Job.objects.count(), job_count)
