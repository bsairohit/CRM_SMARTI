from datetime import datetime

from django import forms
from django.db.models import Q
from django.utils import timezone

from .models import Customer, Job, StaffMember


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "email", "address", "onboarding_status"]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}


class CustomerStatusForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["onboarding_status"]


class StaffForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = ["name", "role", "phone", "is_active"]


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "customer",
            "staff",
            "job_type",
            "scheduled_date",
            "scheduled_time",
            "description",
            "status",
        ]
        widgets = {
            "scheduled_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "scheduled_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active staff can be picked, but keep the current assignee selectable
        # so a job can still be edited after its staff member has been deactivated.
        self.fields["staff"].queryset = StaffMember.objects.filter(
            Q(is_active=True) | Q(pk=self.instance.staff_id)
        )

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("scheduled_date")
        time = cleaned_data.get("scheduled_time")
        schedule_changed = {"scheduled_date", "scheduled_time"} & set(self.changed_data)

        # Only checked when the schedule changes, so that past jobs stay editable.
        if date and time and schedule_changed:
            now = timezone.localtime().replace(tzinfo=None)
            if datetime.combine(date, time) < now:
                self.add_error("scheduled_date", "A job cannot be scheduled in the past.")
        return cleaned_data


class JobStatusForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ["status"]
