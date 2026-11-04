from django.contrib import admin

from .models import Customer, Job, StaffMember

admin.site.register([Customer, StaffMember, Job])
