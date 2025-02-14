from rest_framework import serializers
from bson import ObjectId

class ObjectIdField(serializers.Field):
    def to_representation(self, value):
        return str(value)
    def to_internal_value(self, data):
        return ObjectId(data)


from .models import Register   
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Register
        fields = '__all__'


from .models import Patient
class PatientSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = Patient
        fields = '__all__'


from .models import SampleCollector
class SampleCollectorSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = SampleCollector
        fields = '__all__'

        
from .models import ClinicalName
class ClinicalNameSerializer(serializers.ModelSerializer):
    # Convert ObjectId to string if using MongoDB
    id = ObjectIdField(read_only=True)
    class Meta:
        model = ClinicalName
        fields = '__all__'


from .models import RefBy
class RefBySerializer(serializers.ModelSerializer):
    # Convert ObjectId to string if using MongoDB
    id = ObjectIdField(read_only=True)
    class Meta:
        model = RefBy
        fields = '__all__'


class PatientReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['patient_id', 'totalAmount', 'discount', 'credit_amount', 'date']


from .models import TestValue
class TestValueSerializer(serializers.ModelSerializer):
    testdetails = serializers.JSONField()  # Store multiple test details as JSON
    class Meta:
        model = TestValue  # Replace with your model name
        fields = ['patient_id', 'patientname', 'age', 'date', 'testdetails']


from rest_framework import serializers
from .models import SampleStatus
class SampleStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleStatus
        fields = '__all__'  # Include all fields from the model


from .models import SalesVisitLog
class SalesVisitLogSerializer(serializers.ModelSerializer):
    id = ObjectIdField(read_only=True)
    class Meta:
        model = SalesVisitLog
        fields = "__all__"


from .models import HospitalLab
class HospitalLabSerializer(serializers.ModelSerializer):
    class Meta:
        model = HospitalLab
        fields = '__all__'


from .models import LogisticData
class LogisticDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogisticData
        fields = '__all__'


from .models import LogisticTask
class LogisticTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogisticTask
        fields = '__all__'