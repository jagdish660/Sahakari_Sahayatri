from django.db import models
from datetime import date

class Member(models.Model):
    member_id = models.IntegerField(unique=True, primary_key=True)
    # Separate name fields
    first_name = models.CharField(max_length=30, blank=False)
    middle_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=False)
    # This stores the full name
    name = models.CharField(max_length=100, blank=False, editable=False)

    email = models.EmailField(unique=True, blank=True)
    phone_number = models.CharField(max_length=15, unique=True, blank=True)
    address = models.TextField(blank=False)
    date_of_birth = models.DateField(blank=True, null=True)
    citizenship_number = models.CharField(max_length=20, unique=True, blank=False)
    occupation = models.CharField(max_length=100, blank=True)
    date_joined = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Build full name before saving
        parts = [self.first_name.strip()]
        if self.middle_name:
            parts.append(self.middle_name.strip())
        parts.append(self.last_name.strip())
        self.name = " ".join(parts)

        # Set date_joined to today's date if not already set
        if not self.date_joined:
            self.date_joined = date.today()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"({self.member_id}) - {self.name}"
    
    class Meta:
        ordering = ['member_id']  # Ascending order
        # ordering = ['-member_id']  # For descending order
