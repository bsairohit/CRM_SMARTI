from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CustomerForm, CustomerStatusForm, JobForm, JobStatusForm, StaffForm
from .models import Customer, Job, StaffMember


def _form_page(request, form, title, cancel_to, success_to=None):
    """Shared create/edit flow: save a valid POST and redirect, otherwise show the form.

    cancel_to and success_to accept anything redirect() does: a URL name or a model
    instance. success_to defaults to the saved object's own page.
    """
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"Saved: {obj}")
        return redirect(success_to or obj)
    context = {"form": form, "title": title, "cancel_url": resolve_url(cancel_to)}
    return render(request, "crm/form.html", context)


def _jobs():
    return Job.objects.select_related("customer", "staff")


# --- Customers ---


def customer_list(request):
    return render(request, "crm/customer_list.html", {"customers": Customer.objects.all()})


def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    context = {
        "customer": customer,
        "jobs": _jobs().filter(customer=customer),
        "status_choices": Customer.OnboardingStatus.choices,
    }
    return render(request, "crm/customer_detail.html", context)


def customer_create(request):
    form = CustomerForm(request.POST or None)
    return _form_page(request, form, "Add customer", "customer_list")


def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    return _form_page(request, form, f"Edit {customer}", customer)


@require_POST
def customer_update_status(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerStatusForm(request.POST, instance=customer)
    if form.is_valid():
        form.save()
        messages.success(request, "Onboarding status updated.")
    else:
        messages.error(request, "That is not a valid onboarding status.")
    return redirect("customer_detail", pk=pk)


# --- Staff ---


def staff_list(request):
    return render(request, "crm/staff_list.html", {"staff_members": StaffMember.objects.all()})


def staff_detail(request, pk):
    member = get_object_or_404(StaffMember, pk=pk)
    context = {"member": member, "jobs": _jobs().filter(staff=member)}
    return render(request, "crm/staff_detail.html", context)


def staff_create(request):
    form = StaffForm(request.POST or None)
    return _form_page(request, form, "Add staff member", "staff_list")


def staff_edit(request, pk):
    member = get_object_or_404(StaffMember, pk=pk)
    form = StaffForm(request.POST or None, instance=member)
    return _form_page(request, form, f"Edit {member.name}", member)


# --- Jobs and appointments ---


def upcoming_jobs(request):
    """Home page: unfinished jobs from today onwards, soonest first."""
    jobs = _jobs().filter(scheduled_date__gte=timezone.localdate()).exclude(
        status=Job.Status.COMPLETED
    )
    return render(request, "crm/upcoming.html", {"jobs": jobs})


def job_list(request):
    """All jobs, newest first, optionally filtered with ?status=<value>."""
    jobs = _jobs().order_by("-scheduled_date", "-scheduled_time")
    selected = request.GET.get("status", "")
    if selected in Job.Status.values:
        jobs = jobs.filter(status=selected)
    else:
        selected = ""
    context = {"jobs": jobs, "selected": selected, "status_choices": Job.Status.choices}
    return render(request, "crm/job_list.html", context)


def job_create(request):
    # ?customer=<id> pre-selects the customer when coming from a customer page.
    initial = {"customer": request.GET.get("customer")}
    form = JobForm(request.POST or None, initial=initial)
    return _form_page(request, form, "Book job", "upcoming_jobs", success_to="upcoming_jobs")


def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk)
    form = JobForm(request.POST or None, instance=job)
    return _form_page(request, form, f"Edit job #{job.pk}", "job_list", success_to="job_list")


@require_POST
def job_update_status(request, pk):
    job = get_object_or_404(Job, pk=pk)
    form = JobStatusForm(request.POST, instance=job)
    if form.is_valid():
        form.save()
        messages.success(request, "Job status updated.")
    else:
        messages.error(request, "That is not a valid job status.")

    # Return to the page the form was on, ignoring any off-site redirect target.
    next_url = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("job_list")
