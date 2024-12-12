from django.db import models

# Create your models here.
from django.db import models
class Register(models.Model):
    id = models.CharField(max_length=500, primary_key=True)
    name = models.CharField(max_length=500)
    role = models.CharField(max_length=500)
    email = models.EmailField(max_length=500, unique=True)
    password = models.CharField(max_length=500)
    confirmPassword = models.CharField(max_length=500)
    
#new registration
class Patient(models.Model):
    patient_id = models.CharField(max_length=10, unique=True,primary_key=True)
    patientname = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=10)
    email = models.EmailField(blank=True)
    address = models.JSONField(blank=True, null=True) 
    age = models.IntegerField()
    age_type = models.CharField(max_length=10)  # Adjusted field name for consistency
    sample_collector = models.CharField(max_length=100, blank=True)
    date = models.DateField()
    discount= models.CharField(max_length=100, blank=True)
    # New fields
    lab_id = models.CharField(max_length=50, blank=True)
    refby = models.CharField(max_length=100, blank=True)  # Referring doctor or reference
    branch = models.CharField(max_length=100, blank=True)
    B2B = models.CharField(max_length=100, blank=True)
    home_collection = models.CharField(max_length=100, blank=True)
    testname = models.JSONField(max_length=100)
    totalAmount = models.CharField(max_length=100, blank=True)
    payment_method = models.JSONField(blank=True)
    credit_amount= models.CharField(max_length=50, blank=True)
    def save(self, *args, **kwargs):
        # Automatically set fields based on B2B and home_collection
        if self.B2B:
            self.home_collection = None  # Set home_collection to null if B2B is filled
        elif self.home_collection:
            self.B2B = None  # Set B2B to null if home_collection is filled
        super().save(*args, **kwargs)  # Call the parent save method
    def __str__(self):
        return self.patientname
    
class ClinicalName(models.Model):
    clinicalname = models.CharField(max_length=255)
    referrerCode = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=100, blank=True, null=True)
    salesMapping = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self):
        return f"{self.clinicalname}"
    
class RefBy(models.Model):
    name = models.CharField(max_length=255)
    def __str__(self):
        return f"{self.name}"
    
class SampleCollector(models.Model):
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField()
    def __str__(self):
        return f"{self.name}"
    
class Test(models.Model):
    testname = models.CharField(max_length=100, unique=True)
    specimen_type = models.CharField(max_length=50)
    unit = models.CharField(max_length=20)
    reference_range = models.CharField(max_length=50)

class TestValue(models.Model):
    patient_id = models.CharField(max_length=10)
    patientname = models.CharField(max_length=100)
    age = models.IntegerField()
    date = models.DateField()
    testdetails = models.JSONField()  # Store all test details in JSON format
    def __str__(self):
        return f"{self.patientname} ({self.patient_id}) - {self.date}"
    
class SampleStatus(models.Model):
    patient_id = models.CharField(max_length=50)
    patientname = models.CharField(max_length=100)
    testdetails = models.JSONField()  # JSONField for test details
    date = models.DateField()
    home_collection = models.CharField(max_length=100, blank=True)
    B2B = models.CharField(max_length=100, null=True, blank=True)
    def __str__(self):
        return f"{self.patientname} ({self.patient_id})"
    