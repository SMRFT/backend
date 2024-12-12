from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework import viewsets, status
from datetime import datetime
from django.db.models import Max
from urllib.parse import quote_plus
from pymongo import MongoClient
from django.views.decorators.http import require_GET
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, FloatField, Value, F, Case, When
from django.db.models.functions import Cast, Coalesce
import json

from .serializers import RegisterSerializer
@api_view(['POST'])
@csrf_exempt
def registration(request):
    if request.method == 'POST':
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

from .models import Register
@api_view(['POST'])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    try:
        # Check if user exists
        user = Register.objects.get(email=email)

        # Directly compare the provided password with the stored password
        if password == user.password:
            # Successful login
            return Response({
                "message": f"Login successful as {user.role}",
                "role": user.role
            }, status=status.HTTP_200_OK)
        else:
            # Invalid password
            return Response({"error": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)

    except Register.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    

from .serializers import PatientSerializer
@api_view(['POST'])
@csrf_exempt
def create_patient(request):
    if request.method == 'POST':
        serializer = PatientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

from .serializers import PatientSerializer
@api_view(['GET'])
@csrf_exempt
def get_all_patients(request):
    # Check if 'B2B' is provided in the request query parameters
    b2b = request.query_params.get('B2B', None)

    if b2b:  # If B2B has a value, retrieve all patients
        patients = Patient.objects.all()
    else:  # If B2B is None or empty, retrieve only patients meeting specific criteria
        patients = Patient.objects.filter(B2B__isnull=False)  # Adjust the filter as needed

    serializer = PatientSerializer(patients, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_latest_patient_id(request):
    # Fetch the latest patient ID from the database
    latest_patient = Patient.objects.aggregate(Max('patient_id'))
    # If there's a patient ID, increment it, otherwise start with SD001
    if latest_patient['patient_id__max']:
        current_id = int(latest_patient['patient_id__max'].replace('SD', ''))
        new_patient_id = f"SD{str(current_id + 1).zfill(3)}"
    else:
        new_patient_id = "SD001"
    return Response({"patient_id": new_patient_id}, status=status.HTTP_200_OK)


@csrf_exempt
def get_patient_details(request):
    patient_id = request.GET.get('patient_id')
    phone = request.GET.get('phone')
    patientname = request.GET.get('patientname')

    try:
        patient = None

        # Check for patient_id
        if patient_id:
            patient = Patient.objects.filter(patient_id=patient_id).first()
        # Check for phone
        elif phone:
            patient = Patient.objects.filter(phone=phone).first()
        # Check for patientname (case-insensitive, partial match)
        elif patientname:
            patient = Patient.objects.filter(patientname__icontains=patientname).first()
        else:
            return JsonResponse({'error': 'Please provide either patient_id, phone, or patientname'}, status=400)

        # If patient is found, return patient data
        if patient:
            patient_data = {
                'patient_id': patient.patient_id,
                'patientname': patient.patientname,
                'age': patient.age,
                'gender': patient.gender,
                'phone': patient.phone,
                'address': patient.address,
                'email': patient.email,
            }
            return JsonResponse(patient_data)
        else:
            return JsonResponse({'error': 'Patient not found'}, status=404)
    
    except Exception as e:
        return JsonResponse({'error': f'Error fetching patient details: {str(e)}'}, status=500)
    

from .models import Patient  # Adjust the import based on your project structure
def get_patients_by_date(request):
    date = request.GET.get('date')
    if date:
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d').date()  # Convert date to datetime
            patients = Patient.objects.filter(date=parsed_date)
            # Ensure the response is a valid JSON
            patient_data = [model_to_dict(patient) for patient in patients]
            return JsonResponse({'data': patient_data}, safe=False)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    return JsonResponse({'error': 'Date parameter is required.'}, status=400)

def convert_to_float(value):
    """
    Converts a value to float if possible; otherwise, returns 0.0
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
from django.db.models import Sum
@api_view(['GET'])
def patient_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not start_date or not end_date:
        return Response({"error": "Start date and end date parameters are required"}, status=400)
    patients = Patient.objects.filter(date__range=[start_date, end_date])
    # Convert fields to float and handle non-numeric data
    total_amount = sum(convert_to_float(p.totalAmount) for p in patients)
    discount = sum(convert_to_float(p.discount) for p in patients)
    credit_amount = sum(convert_to_float(p.credit_amount) for p in patients)
    # Pending collection is the total of credit_amount for the selected date range
    pending_collection = credit_amount
    # Calculate net amounts
    net_amount = total_amount - discount - credit_amount
    pending_collection_net_amount = total_amount + pending_collection - (credit_amount + discount)
    # Construct the report dictionary
    report = {
        'no_of_patients': patients.count(),
        'total_amount': round(total_amount, 2),
        'discount': round(discount, 2),
        'credit_amount': round(credit_amount, 2),
        'net_amount': round(net_amount, 2),
        'pending_collection_net_amount': round(pending_collection_net_amount, 2)
    }
    return Response(report)


@require_GET
@csrf_exempt
def get_test_details(request):
    try:
        # MongoDB connection setup
        client = MongoClient(f'mongodb://3.109.210.34:27017/')
        db = client.Lab  # Database name
        collection =  db.labbackend_testdetails  # Collection name
        # Retrieve all documents in Testdetails collection
        test_details = list(collection.find({}, {'_id': 0}))  # Exclude MongoDB's default _id field
        return JsonResponse(test_details, safe=False, status=200)
    except Exception as e:
        print("Error fetching test details:", e)
        return JsonResponse({'error': 'Failed to fetch test details'}, status=500)
    

from .models import SampleCollector
from .serializers import SampleCollectorSerializer
@api_view(['GET', 'POST'])
def sample_collector(request):
    if request.method == 'POST':
        serializer = SampleCollectorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'GET':
        collectors = SampleCollector.objects.all()
        serializer = SampleCollectorSerializer(collectors, many=True)
        return Response(serializer.data)


from .models import ClinicalName
from .serializers import ClinicalNameSerializer
@api_view(['GET', 'POST'])
def clinical_name(request):
    if request.method == 'POST':
        serializer = ClinicalNameSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'GET':
        organisations = ClinicalName.objects.all()
        serializer = ClinicalNameSerializer(organisations, many=True)
        return Response(serializer.data)
    

from .models import RefBy
from .serializers import RefBySerializer
@api_view(['GET', 'POST'])
def refby(request):
    if request.method == 'POST':
        serializer = RefBySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'GET':
        organisations = RefBy.objects.all()
        serializer = RefBySerializer(organisations, many=True)
        return Response(serializer.data)
    


from .models import Patient
def compare_test_details(request):
    # MongoDB connection setup
    client = MongoClient('mongodb://3.109.210.34:27017/')
    db = client.Lab  # Database name
    collection = db.labbackend_testdetails  # Collection name
    # Retrieve the date and patient ID from the request
    date = request.GET.get('date')
    patient_id = request.GET.get('patient_id')
    if not date or not patient_id:
        return JsonResponse({'error': 'Date and patient_id parameters are required'}, status=400)
    try:
        formatted_date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Expected YYYY-MM-DD.'}, status=400)
    # Query SampleStatus for patients with status 'Received' and matching patient_id
    received_samples = SampleStatus.objects.filter(
        patient_id=patient_id,
        testdetails__isnull=False
    )
    test_data = []
    for sample in received_samples:
        try:
            # Check if testdetails is a string or list
            if isinstance(sample.testdetails, str):
                test_list = json.loads(sample.testdetails)  # Parse JSON string
            elif isinstance(sample.testdetails, list):
                test_list = sample.testdetails  # Already a list
            else:
                return JsonResponse({'error': 'Invalid testdetails format'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid testdetails format'}, status=400)
        for test_item in test_list:
            testname = test_item.get('testname')
            samplestatus = test_item.get('samplestatus')
            # Check if the sample status is 'Received'
            if samplestatus == "Received":
                # Fetch test details directly from MongoDB Testdetails collection
                test_details = collection.find({"test_name": testname})
                for test_detail in test_details:
                    test_info = {
                        "patient_id": sample.patient_id,
                        "patientname": sample.patientname,
                        "testname": test_detail.get('test_name'),  # Use 'test_name' from Testdetails
                        "specimen_type": test_detail.get('specimen_type'),
                        "unit": test_detail.get('units'),  # Updated key for units
                        "reference_range": test_detail.get('reference_range'),
                        "status": samplestatus
                    }
                    test_data.append(test_info)  # Append each test detail to test_data
    # Return all collected test details in the response
    return JsonResponse({'data': test_data})


def get_patient_test_status(request):
    date = request.GET.get('date')
    patient_id = request.GET.get('patient_id')

    if not date or not patient_id:
        return JsonResponse({'error': 'Date and patient_id parameters are required'}, status=400)

    try:
        # Retrieve samplestatus and testvalue records for the patient
        sample_status = SampleStatus.objects.filter(patient_id=patient_id).first()
        test_value = TestValue.objects.filter(patient_id=patient_id).first()

        # Process samplestatus data
        test_status = []
        if sample_status:
            for test in sample_status.testdetails:
                testname = test.get('testname')
                status = 'Pending'

                # Check if test exists in testvalue as "Completed"
                if test_value and any(tv.get('testname') == testname for tv in test_value.testdetails):
                    status = 'Completed'
                
                test_status.append({
                    'testname': testname,
                    'status': status
                })

        return JsonResponse({'data': test_status}, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

from .serializers import TestValueSerializer
from .models import Patient, Test
@api_view(['POST'])
def save_test_value(request):
    payload = request.data
    try:
        # Fetch patient details
        patient = Patient.objects.get(patient_id=payload['patient_id'])

        # Prepare data with patient information and nested JSON test details
        test_details_json = payload.get("testdetails", [])

        # Check for existing test values
        for test in test_details_json:
            existing_test_value = TestValue.objects.filter(
                patient_id=patient.patient_id,
            ).exists()

            if existing_test_value:
                return Response(
                    {"error": f"Test '{test['testname']}' for Patient ID '{patient.patient_id}' already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        data = {
            "patient_id": patient.patient_id,
            "patientname": patient.patientname,
            "age": patient.age,
            "date": payload.get("date"),
            "testdetails": test_details_json,  # Store test details as JSON array
        }

        # Serialize and save
        serializer = TestValueSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "All test details saved successfully.", "data": serializer.data}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Patient.DoesNotExist:
        return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)


from .models import  TestValue
@api_view(['GET'])
def get_test_report(request):
    day = request.GET.get('day')
    month = request.GET.get('month')
    queryset = TestValue.objects.all()

    # Filter based on day and month by constructing the date manually
    if day and month:
        queryset = [obj for obj in queryset if obj.date.day == int(day) and obj.date.month == int(month)]
    elif month:
        queryset = [obj for obj in queryset if obj.date.month == int(month)]

    report_data = [
        {
            "patient_id": obj.patient_id,
            "patientname": obj.patientname,
            "age": obj.age,
            "date": obj.date,
            "testdetails": obj.testdetails,
        }
        for obj in queryset
    ]
    return Response({"data": report_data})


def get_test_values(request):
    # Get date from request parameters
    date = request.GET.get('date')
    
    if date:
        try:
            # Ensure the date is in the correct format
            parsed_date = datetime.strptime(date, '%Y-%m-%d').date()  # This gets a date object
            
            # Filter patients by parsed date
            patients = TestValue.objects.filter(date=parsed_date)
            
            # Serialize patient details
            patient_data = [
                {
                    "patient_id": patient.patient_id,
                    "patientname": patient.patientname,
                    "age": patient.age,
                    "date": patient.date,
                    "testdetails": patient.testdetails
                }
                for patient in patients
            ]
            
            return JsonResponse(patient_data, safe=False)
        
        except ValueError:
            # Handle date parsing error
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    
    else:
        # If no date is provided, return all test values ordered by date
        test_values = TestValue.objects.order_by('-date')
        
        # Serialize the test values into a list of dictionaries
        data = [
            {
                "patient_id": test.patient_id,
                "patientname": test.patientname,
                "age": test.age,
                "date": test.date,
                "testdetails": test.testdetails
            }
            for test in test_values
        ]
        
        return JsonResponse(data, safe=False)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
# MongoDB connection
client = MongoClient(f'mongodb://3.109.210.34:27017/')
db = client.Lab  # Your database name
collection = db.labbackend_testvalue  # Your collection name
@csrf_exempt
@require_http_methods(["PATCH"])
def approve_test_detail(request, patient_id, test_index):
    # Log the incoming request body
    print("Request body:", request.body)
    # Check if the body is empty
    if not request.body:
        return JsonResponse({"error": "Empty request body."}, status=400)
    # Load the request data
    try:
        update_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    # Find the test value document for the given patient_id
    test_value = collection.find_one({"patient_id": patient_id})
    # Check if the document exists
    if test_value is None:
        return JsonResponse({"error": "Patient not found."}, status=404)
    # Convert testdetails from string to list
    try:
        test_details = json.loads(test_value.get("testdetails", "[]"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Failed to decode test details."}, status=500)
    # Check for valid index
    if 0 <= test_index < len(test_details):
        # Update approve status based on request data
        if "approve" in update_data:
            test_details[test_index]["approve"] = update_data["approve"]
        # Update the document in the MongoDB collection
        result = collection.update_one(
            {"patient_id": patient_id},
            {"$set": {"testdetails": json.dumps(test_details)}}
        )
        # Check if the update was acknowledged
        if result.acknowledged:
            return JsonResponse({"message": "Test detail approved successfully."})
        else:
            return JsonResponse({"error": "Failed to update test detail."}, status=500)
    else:
        return JsonResponse({"error": "Invalid test index."}, status=400)
    
    
@csrf_exempt
@require_http_methods(["PATCH"])
def rerun_test_detail(request, patient_id, test_index):
    """Rerun the test detail at the given index for the specified patient."""
    # Check if the request body is empty
    if not request.body:
        return JsonResponse({"error": "Empty request body."}, status=400)
    # Load the request data
    try:
        update_data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    # Find the test value document for the given patient_id
    test_value = collection.find_one({"patient_id": patient_id})
    # Check if the document exists
    if test_value is None:
        return JsonResponse({"error": "Patient not found."}, status=404)
    # Convert testdetails from string to list
    try:
        test_details = json.loads(test_value.get("testdetails", "[]"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Failed to decode test details."}, status=500)
    # Check for valid index
    if 0 <= test_index < len(test_details):
        # Update rerun status
        if "rerun" in update_data:
            test_details[test_index]["rerun"] = update_data["rerun"]
        # Update the document in the MongoDB collection
        result = collection.update_one(
            {"patient_id": patient_id},
            {"$set": {"testdetails": json.dumps(test_details)}}
        )
        # Check if the update was acknowledged
        if result.acknowledged:
            return JsonResponse({"message": "Test detail rerun status updated successfully."})
        else:
            return JsonResponse({"error": "Failed to update rerun status."}, status=500)
    else:
        return JsonResponse({"error": "Invalid test index."}, status=400)
    


# MongoDB connection
client = MongoClient(f'mongodb://3.109.210.34:27017/')
db = client.Lab  # Your database name
collection = db.labbackend_testvalue  # Your collection name
@csrf_exempt
@api_view(['PATCH'])
def update_test_detail(request, patient_id):
    """
    Update the value and rerun status of a specific test detail for a given patient in MongoDB.
    """
    try:
        # Find the document for the given patient_id
        test_value = collection.find_one({"patient_id": patient_id})

        if not test_value:
            return Response({'error': 'Patient data not found'}, status=status.HTTP_404_NOT_FOUND)

        # Extract test details and ensure it is in list form
        test_details = test_value.get("testdetails")
        if isinstance(test_details, str):  # If it's a JSON string, parse it into a list
            test_details = json.loads(test_details)

        # Extract data from the request
        testname = request.data.get('testname')
        new_value = request.data.get('value')

        # Find and update the specific test in the test details
        for detail in test_details:
            if detail['testname'] == testname:
                detail['value'] = new_value  # Update the value
                detail['rerun'] = False      # Set rerun to False
                break

        # Update the document in MongoDB with the modified test details as JSON
        collection.update_one(
            {"patient_id": patient_id},
            {"$set": {"testdetails": json.dumps(test_details)}}  # Encode as JSON string
        )

        return Response({'message': 'Test detail updated successfully'}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

from .models import SampleStatus
@csrf_exempt
def sample_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            for entry in data:
                patient = SampleStatus(
                    patient_id=entry['patient_id'],
                    patientname=entry['patientname'],
                    B2B=entry.get('B2B', ''),
                    home_collection=entry['home_collection'],
                    date=entry.get('date', ''),
                    testdetails=entry.get('testdetails', [])  # Expecting JSON data
                )
                patient.save()
            return JsonResponse({'message': 'Data saved successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def update_sample_status(request, patient_id):
    client = MongoClient(f'mongodb://3.109.210.34:27017/')
    db = client.Lab
    collection = db.labbackend_samplestatus
    
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)  # Parse the incoming JSON data
            testname = data.get('testname')  # Get the test name from the request
            samplestatus = data.get('samplestatus')  # Get the sample status from the request

            print(f"Received patient_id: {patient_id}, testname: {testname}, samplestatus: {samplestatus}")

            # Find all patients with the given patient_id in MongoDB
            patients = collection.find({"patient_id": patient_id})
            if not patients:
                print("No patients found with the given patient_id")
                return JsonResponse({'error': 'No patients found with the given patient_id'}, status=404)

            # Flag to track if any document was updated
            update_count = 0

            for patient in patients:
                print(f"Processing patient: {patient['patient_id']}")

                # Ensure testdetails is stored as a list, not a string
                if isinstance(patient.get('testdetails'), str):
                    try:
                        patient['testdetails'] = json.loads(patient['testdetails'])  # Parse the string to an array
                    except json.JSONDecodeError:
                        print(f"Failed to decode testdetails for patient {patient['patient_id']}: {patient['testdetails']}")
                        return JsonResponse({'error': 'Invalid test details format'}, status=400)

                # Print the testdetails to check if it is in the correct format
                print("Testdetails before update:", patient['testdetails'])

                # Update the test status in the testdetails list
                updated_testdetails = []
                test_found = False  # Flag to check if the testname is found
                for entry in patient['testdetails']:
                    if isinstance(entry, dict) and entry.get('testname') == testname:
                        entry['samplestatus'] = samplestatus  # Update the status for the matching test
                        # Add received_time if status is 'Pending'
                        if samplestatus == "Pending":
                            entry['pending_time'] = datetime.now().isoformat()  # Store the current datetime
                            # Add samplecollected_time if status is 'Collected'
                        if samplestatus == "Sample Collected":
                            entry['samplecollected_time'] = datetime.now().isoformat()  # Store the current datetime
                        test_found = True
                    updated_testdetails.append(entry)

                # Check if the testname was found and updated
                if not test_found:
                    print(f"Testname '{testname}' not found in testdetails for patient {patient['patient_id']}.")
                    continue  # Skip this patient if testname is not found

                # Update the testdetails array in the database
                result = collection.update_one(
                    {"_id": patient['_id']},  # Use the patient's unique MongoDB _id to update the document
                    {"$set": {"testdetails": json.dumps(updated_testdetails)}}
                )

                if result.modified_count > 0:
                    print(f"Updated test status for patient {patient['patient_id']}")
                    update_count += 1
                else:
                    print(f"Failed to update test status for patient {patient['patient_id']}")

            if update_count > 0:
                print(f"Successfully updated sample status for {update_count} patients.")
                return JsonResponse({'message': f'Successfully updated sample status for {update_count} patients.'}, status=200)
            else:
                print("No updates were made.")
                return JsonResponse({'error': 'No updates were made'}, status=400)
        
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)



from django.db.models import Q
from datetime import datetime
@csrf_exempt
def get_sample_collected(request):
    if request.method == "GET":
        try:
            # Extract the selected date from the query parameters
            selected_date_str = request.GET.get('date', None)
            if selected_date_str:
                selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
            else:
                selected_date = None

            # Fetch all sample statuses
            samples = SampleStatus.objects.all()

            patient_data = {}

            # Prepare the data grouped by patient
            for sample in samples:
                # Deserialize testdetails if it's a string
                if isinstance(sample.testdetails, str):
                    test_details = json.loads(sample.testdetails)
                else:
                    test_details = sample.testdetails

                # Filter test details based on samplestatus and selected date
                for detail in test_details:
                    if detail.get("samplestatus") == "Sample Collected":
                        sample_date_str = detail.get("samplecollected_time")
                        if sample_date_str:
                            try:
                                # Handle full datetime (with time and microseconds)
                                sample_date = datetime.strptime(sample_date_str, "%Y-%m-%dT%H:%M:%S.%f").date()
                            except ValueError:
                                sample_date = datetime.strptime(sample_date_str, "%Y-%m-%dT%H:%M:%S").date()

                        if not selected_date or sample_date == selected_date:
                            # If patient is not already in the dictionary, add them
                            if sample.patient_id not in patient_data:
                                patient_data[sample.patient_id] = {
                                    "patient_id": sample.patient_id,
                                    "patientname": sample.patientname,
                                    "B2B": sample.B2B,
                                    "home_collection": sample.home_collection,
                                    "testdetails": []
                                }

                            # Append the test details
                            patient_data[sample.patient_id]["testdetails"].append({
                                "testname": detail.get("testname", "N/A"),
                                "container": detail.get("container", "N/A"),
                                "samplecollector": detail.get("samplecollector", "N/A"),
                                "samplestatus": detail.get("samplestatus", "N/A"),
                                "samplecollected_time": sample_date,
                            })

            # Convert the dictionary to a list
            data = list(patient_data.values())

            # Return the filtered data as a response
            return JsonResponse({"data": data}, safe=False)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
        

@csrf_exempt
def update_sample_collected(request, patient_id):
    # Connect to MongoDB
    client = MongoClient(f'mongodb://3.109.210.34:27017/')
    db = client.Lab  # Your database name
    collection = db.labbackend_samplestatus  # Your collection name

    if request.method == "PUT":
        try:
            body = json.loads(request.body)
            updates = body.get("updates", [])

            if not updates:
                return JsonResponse({"error": "Updates are required"}, status=400)

            # Find the patient sample record
            patient_sample = collection.find_one({"patient_id": patient_id})
            if not patient_sample:
                return JsonResponse({"error": "Sample not found"}, status=404)

            testdetails = json.loads(patient_sample.get('testdetails', '[]'))

            # Apply updates
            for update in updates:
                test_index = update.get("testIndex")
                new_status = update.get("samplestatus")

                if test_index is None or not new_status:
                    return JsonResponse({"error": "samplestatus and testIndex are required"}, status=400)

                if not (0 <= int(test_index) < len(testdetails)):
                    return JsonResponse({"error": "Invalid testIndex"}, status=400)

                testdetails[int(test_index)]['samplestatus'] = new_status

            # Save changes
            collection.update_one(
                {"patient_id": patient_id},
                {"$set": {"testdetails": json.dumps(testdetails)}}
            )

            return JsonResponse({"message": "Sample status updated successfully"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@api_view(['GET'])
def patient_overview(request):
    patients = Patient.objects.all()
    serializer = PatientSerializer(patients, many=True)  # Serialize the queryset
    return Response(serializer.data)


from django.http import JsonResponse
from .models import SampleStatus, TestValue
def patient_test_status(request):
    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Patient ID is required'}, status=400)
    
    try:
        # Check if the patient exists in the Patient model
        patient = Patient.objects.get(patient_id=patient_id)
        
        # Try to fetch the sample status for the patient
        try:
            sample_status = SampleStatus.objects.get(patient_id=patient_id)

            # Parse test details
            test_details = sample_status.testdetails

            # Flags to track statuses
            all_collected = True
            all_received = True
            has_collected = False
            has_received = False
            
            # Iterate through each test in testdetails
            for test in test_details:
                sample_status = test.get("samplestatus")
                
                if sample_status == "Sample Collected":
                    has_collected = True
                    all_received = False  # If any test is only collected, not all are received
                    
                elif sample_status == "Received":
                    has_received = True
                    all_collected = False  # If any test is received, not all are just collected
                
                else:
                    # If any test is neither "Sample Collected" nor "Received",
                    # it means not all are collected or received.
                    all_collected = False
                    all_received = False

            # Determine the final status based on flags
            if all_received:
                status = "Received"
            elif all_collected:
                status = "Collected"
            elif has_received and has_collected:
                status = "Partially Received"
            elif has_collected:
                status = "Partially Collected"
            else:
                status = "Registered"  # Default to 'Registered' if no relevant status
            
            return JsonResponse({
                'patient_id': patient.patient_id,
                'patient_name': patient.patientname,
                'status': status
            })

        # If no sample status exists for this patient, return 'Registered' status
        except SampleStatus.DoesNotExist:
            return JsonResponse({
                'patient_id': patient.patient_id,
                'patient_name': patient.patientname,
                'status': 'Registered'
            })

    # If the patient does not exist in the Patient model
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)
    

def get_patient_test_details(request):
    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Patient ID is required'}, status=400)

    try:
        test_values = TestValue.objects.filter(patient_id=patient_id)
        try:
            patient_details = {
                "patient_id": test_values[0].patient_id,
                "patientname": test_values[0].patientname,
                "age": test_values[0].age,
                "date": test_values[0].date,
                "testdetails": test_values[0].testdetails,  # Ensure this is JSON serializable
            }
        except Exception as e:
            return JsonResponse({'error': f'Data formatting error: {e}'}, status=500)
        return JsonResponse(patient_details, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@api_view(['PATCH'])
def update_credit_amount(request, patient_id):
    # MongoDB connection setup
    client = MongoClient(f'mongodb://3.109.210.34:27017/')
    db = client['Lab']
    collection = db['labbackend_patient']
    # Retrieve the Django patient record, return 404 if not found
    patient = get_object_or_404(Patient, patient_id=patient_id)
    # Update only the credit amount if provided in the request data
    credit_amount = request.data.get("credit_amount")
    if credit_amount is not None:
        # Convert credit_amount to an integer for MongoDB consistency
        try:
            credit_amount = (credit_amount)
        except ValueError:
            return Response({"error": "Credit amount must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        # Update the credit amount in Django
        patient.credit_amount = credit_amount
        patient_id_str = str(patient_id)
        # Update MongoDB with credit_amount as an integer
        result = collection.update_one(
            {"patient_id": patient_id_str},
            {"$set": {"credit_amount": credit_amount}},
            upsert=False
        )
        # Check if the document was matched in MongoDB
        if result.matched_count == 0:
            return Response({"error": "Patient not found in MongoDB."}, status=status.HTTP_404_NOT_FOUND)
        # Save the updated credit amount in the Django model
        try:
            patient.save()
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "message": "Credit amount updated successfully",
            "credit_amount": credit_amount
        }, status=status.HTTP_200_OK)
    # Return an error if credit_amount was not provided in the request
    return Response({"error": "Credit amount is required."}, status=status.HTTP_400_BAD_REQUEST)

    


