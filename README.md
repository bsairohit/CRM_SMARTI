# Smarti CRM

A small web-based CRM for a business that manages customers, appointments, fitters and maintenance engineers. Built with HTML, Django, and SQLite for the Smarti.

**What it does**

- **Customers:** add, list, view and edit customers (name, phone, email, address).
- **Onboarding:** give each customer a status (New Enquiry, In Progress, Active) and update it from their page.
- **Appointments and jobs:** book a job for a customer with a date, time and staff member, then view upcoming appointments.
- **Staff:** keep a list of fitters and maintenance engineers, and see the jobs assigned to each person.
- **Job tracking:** move jobs through Pending, In Progress and Completed.

## A. Getting started

You need Python 3.12 or newer, which Django 6.1 requires. Run these commands from the repository root.

### 1. Install the dependencies

```bash
python3 -m venv smarti
source smarti/bin/activate        # Windows: smarti\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up the database and test data

```bash
cd SmartiApp
python manage.py migrate
python manage.py seed_demo
```

`migrate` creates a local SQLite file at `SmartiApp/db.sqlite3`. `seed_demo` adds 3 customers, 2 staff members and 3 jobs, with dates relative to today. It does nothing if the database already contains customers or staff.

To start again from empty, delete `db.sqlite3` and repeat this step.

### 3. Run the application

```bash
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. No login is needed.

### 4. Test the main functionality

Run the automated tests:

```bash
python manage.py test
```

Then try the main workflow in the browser:

1. **Add a customer:** go to **Customers > Add customer** and save. Submit it again with an invalid phone number to see the validation errors.
2. **Update onboarding:** on the customer's page, change the onboarding status and click **Update**.
3. **Add a staff member:** go to **Staff > Add staff member** and save.
4. **Book a job:** on the customer's page, click **Book job**, choose the staff member, date and time, and save. It appears on **Upcoming**.
5. **Try invalid bookings:** book the same staff member at the same date and time, then try a date in the past. Both are rejected.
6. **Track the job:** change the job's status on **Upcoming** to In Progress, then to Completed. A completed job leaves **Upcoming** but stays on **All jobs**, where you can filter by status.

### 5. See the custom error pages (optional)

Django only shows the custom 404 and 500 pages when debug mode is off:

```bash
DJANGO_DEBUG=false python manage.py runserver --insecure
```

Then open a page that doesn't exist, such as <http://127.0.0.1:8000/customers/9999/>. `--insecure` lets the development server keep serving the CSS with debug off. The 500 page is checked by an automated test, because the app has no page that fails on demand.

## B. Architecture and design decisions

### Which technologies I chose and why

I chose **Django** because I have work experience with it, and with only 3 hours I wanted to spend my time on the problem rather than on learning a framework. It also includes most of what this project needs: models, migrations, forms and CSRF protection.

The other choices follow from keeping things simple:

- **SQLite:** it needs no setup, and the brief allows it.
- **Django templates:** these are simple forms and lists, so server-rendered pages are enough. There is no separate frontend or build step.
- **Function-based views:** each view reads from top to bottom, so it's easy to follow and change.
- **One small CSS file and no JavaScript:** the brief doesn't assess appearance, so I kept the styling basic.

### How I structured the application and database

Before writing any code, I went through the brief with pen and paper, worked out what was required, and then started building.

Everything is in one Django app, `crm`, because customers, staff and jobs are all part of the same workflow:

```
requirements.txt
README.md
SmartiApp/
├── manage.py
├── SmartiApp/                 Project configuration (settings, root URLs)
└── crm/                       The application
    ├── models.py              Customer, StaffMember, Job, and their statuses
    ├── forms.py               Input validation
    ├── views.py               Request handling
    ├── urls.py                Routes
    ├── tests.py               Automated tests
    ├── management/commands/seed_demo.py    Demo data
    ├── migrations/            Database schema history
    ├── static/crm/style.css
    └── templates/             404.html and 500.html
        └── crm/               Pages, plus the shared form.html and _job_table.html
```

The database has three tables, and `Job` is what connects the other two. Every job points to one customer and one staff member:

```
Customer 1 ──── * Job * ──── 1 StaffMember
```

| Table | Main fields |
| --- | --- |
| **Customer** | `name`, `phone` (exactly 10 digits), `email` (optional), `address`, `onboarding_status`, `created_at` |
| **StaffMember** | `name`, `role` (Fitter or Maintenance Engineer), `phone` (optional, exactly 10 digits), `is_active` |
| **Job** | `customer`, `staff`, `job_type` (Installation or Maintenance), `scheduled_date`, `scheduled_time`, `description`, `status`, `created_at` |

A few decisions are worth explaining:

- **Appointments and jobs are one table.** An appointment is really just when a job happens, for the same customer and staff member, so two tables would only need keeping in sync. The "Upcoming appointments" page simply shows jobs that aren't completed and are dated today or later.
- **The same person can't be booked twice for the same slot.** A unique constraint on staff, date and time enforces this in the database, and the form shows a normal error message.
- **Job history is kept.** A customer or staff member who has jobs can't be deleted. If someone leaves, you mark them inactive: they can't get new jobs, but their old jobs can still be edited.
- **Past dates are only blocked when scheduling.** A job from last week is valid, but booking a new one in the past is a mistake. The rule only applies when the date or time is set or changed, so you can still add notes to old jobs.

### How the main components interact

All the parts are linked. A customer's page shows their jobs, a staff member's page shows the jobs assigned to them, and the job pages show both.

In the code, each request follows the same path:

```
Browser ──> urls.py ──> views.py ──> forms.py (validate) ──> models.py ──> SQLite
   ^                       │
   └── templates/crm/ <────┘
```

For example, when someone books a job:

1. The browser sends the form to `/jobs/new/`, and `urls.py` passes it to the `job_create` view.
2. The view builds a `JobForm` and hands it to `_form_page`, a helper shared by all the create and edit pages.
3. If the form is valid, the job is saved and the user is redirected with a success message. The redirect also means refreshing the page won't submit the form twice.
4. If it isn't valid, the form is shown again with the errors and what the user typed.

Status updates work the same way, but have their own views (`customer_update_status` and `job_update_status`) that only accept POST requests and only change the status field.

Errors are handled at three levels:

- **Invalid input:** the form shows the problem next to the field, and nothing is saved.
- **Missing pages or records (404):** `404.html` keeps the normal navigation so users can find their way back.
- **Unexpected errors (500):** `500.html` is self-contained, so it can still render when the app itself is failing. Users don't see any technical details.

### Alternative approaches I considered

- **A Django REST API:** I could have built an API with a separate frontend. That would make sense if a mobile app or other systems needed the data later, but for this brief it would add a lot of extra work with no real benefit.
- **Separate `Appointment` and `Job` tables:** this would be useful if one job needed several visits, but the brief doesn't need that yet.

### What I would change or improve with more time

The first thing I would add is **authentication**, so that only people with access can use the system. The brief didn't require it, but a real CRM holds customer details and shouldn't be open to anyone. I would also add roles, so office staff and engineers see what's relevant to them.

After that, I would add:

1. **Job durations:** so overlapping jobs are caught, not just identical start times.
2. **An overdue view:** to show unfinished jobs whose date has passed.
3. **Search and pagination:** for when the lists get longer.
4. **Production setup:** PostgreSQL, with secrets and settings read from environment variables.

## C. Development process

### Order of development

1. **Data model:** started here because the main design decision was how appointments and jobs relate.
2. **Forms and validation:** added next so that the rules were settled before any pages were built.
3. **Views, URLs and templates:** built for customers, then staff, then jobs.
4. **Demo data command:** so that a reviewer has something to look at straight away.
5. **Automated tests and a manual check:** run against the finished workflow.
6. **Documentation:** written last, then checked by following the setup steps from a clean environment.

### Challenges and how they were resolved

- **Validating past dates without blocking old jobs:** a simple "no past dates" rule would stop anyone editing last week's job. The form now applies the rule only when the date or time changes.
- **Deactivated staff on existing jobs:** limiting the dropdown to active staff made older jobs impossible to save. The list now includes active staff plus the job's current assignee.
- **Keeping forms consistent:** the first version of the shared form helper was awkward to use, and its template had to guess whether the Cancel link was a URL or a route name. I replaced it with `_form_page`, which accepts either and resolves it in one place.

### Known limitations

- **Double-booking:** only identical start times are detected, because jobs have no duration. A 10:00 and a 10:15 job for the same person are both allowed.
- **Overdue jobs:** unfinished jobs with a past date leave **Upcoming**. They are still listed on **All jobs**.
- **Status changes:** any status can change to any other, and a new job can be created as Completed.
- **Deactivated staff:** existing future jobs are not reassigned automatically.
- **Deleting records:** the app has no delete pages. Records can only be deleted through Django admin, which needs `python manage.py createsuperuser`.
- **Phone numbers:** must be exactly 10 digits with no spaces or symbols, so 11-digit and international numbers are rejected.
- **Duplicates:** duplicate customers are not detected.
- **Security and deployment:** there is no authentication, by design for this brief. Debug mode is on by default and the secret key is stored in `settings.py`. Both are for local development only and must change before any deployment.

### Testing

- **Automated:** 28 Django tests in `crm/tests.py` cover customer, staff and job creation and editing, validation failures, status updates, the upcoming filter, double-booking, deactivated staff, unsafe redirects, the custom error pages and the seed command.
- **Manual:** the setup steps were followed in a clean virtual environment with a new database. The main workflow was then run against the live development server over HTTP, with CSRF protection active.
- **Not tested:** cross-browser behaviour, concurrent users and performance with large data sets.

### Use of AI tools

I built this project with Claude Code, an AI coding assistant. I gave the directions, and it generated the code, tests and first draft of this README.

I set the approach, including basic Django with Django templates and a minimal interface, and asked for changes as I went, such as custom 404 and 500 pages and the 10-digit phone rule.

I then cross-checked the output by running the app myself, which is how I caught problems such as a missing database migration step and the styling not loading. The test suite, a clean setup from these instructions and a run of the main workflow on the live server provided further checks.

## D. Submission Summary

I developed a web-based CRM and job management system using Django, Python, HTML and SQLite. The application supports customer management, onboarding status tracking, appointment booking, staff allocation and job status management.

I am particularly pleased with the decision to combine appointments and jobs into a single workflow, keeping the database structure simple while maintaining clear relationships between customers, staff and scheduled work. I also implemented input validation, prevention of staff double-booking for identical time slots, custom error pages and 28 automated tests.

If I had more time, I would focus on introducing user authentication and role-based access, improving appointment scheduling to account for job durations, and adding search and reporting functionality. I would also prepare the application for production deployment using PostgreSQL and environment-based configuration.

This project allowed me to apply my software development experience to a practical business problem while considering maintainability, usability and future scalability.