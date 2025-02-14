from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework import viewsets, status
from datetime import datetime, timedelta
from django.db.models import Max
from urllib.parse import quote_plus
from pymongo import MongoClient
from django.views.decorators.http import require_GET
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
import json

from .serializers import RegisterSerializer

@api_view(['GET', 'POST'])
@csrf_exempt
def registration(request):
    if request.method == 'POST':
        # Handle Registration
        name = request.data.get('name')
        role = request.data.get('role')
        password = request.data.get('password')
        confirm_password = request.data.get('confirmPassword')
        if password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)
        if Register.objects.filter(name=name, role=role).exists():
            return Response({"error": "User with this name and role already exists"}, status=status.HTTP_400_BAD_REQUEST)
        Register.objects.create(name=name, role=role, password=password)
        return Response({"message": "Registration successful!"}, status=status.HTTP_201_CREATED)
    elif request.method == 'GET':
        # Handle fetching users with the role "Sales Person"
        sales_persons = Register.objects.filter(role='Sales Person')
        serializer = RegisterSerializer(sales_persons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
   

from .models import Register
@api_view(['POST'])
def login(request):
    name = request.data.get('name')
    password = request.data.get('password')
    try:
        user = Register.objects.get(name=name)
        if user.password == password:
            return Response({
                "message": f"Login successful as {user.role}, {user.name}",
                "role": user.role,
                "name": user.name
            }, status=status.HTTP_200_OK)
        else:
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
   

@api_view(['GET'])
def get_latest_bill_no(request):
    today = datetime.now().strftime('%Y%m%d')  # Get today's date in YYYYMMDD format
    # Get the latest bill_no that starts with today's date
    last_bill = Patient.objects.filter(bill_no__startswith=today).aggregate(Max('bill_no'))
    if last_bill['bill_no__max']:
        # Extract the numeric part of the last bill number and increment it
        last_id = int(last_bill['bill_no__max'][-4:])  # Extract the last 4 digits
        next_id = last_id + 1
    else:
        # Start with 0001 if no bills exist for today
        next_id = 1
    # Generate the new bill number
    new_bill_no = f"{today}{next_id:04d}"  # Format: YYYYMMDD0001
    return Response({"bill_no": new_bill_no}, status=status.HTTP_200_OK)


from .models import BarcodeTestDetails
def get_existing_barcode(request):
    patient_id = request.GET.get('patient_id')
    date = request.GET.get('date')
    if patient_id and date:
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d').date()
            barcode_record = BarcodeTestDetails.objects.filter(patient_id=patient_id, date=parsed_date).first()
            if barcode_record:
                return JsonResponse({
                    'patient_id': barcode_record.patient_id,
                    'patientname': barcode_record.patientname,
                    'age': barcode_record.age,
                    'gender': barcode_record.gender,
                    'date': barcode_record.date,
                    'bill_no': barcode_record.bill_no,
                    'tests': barcode_record.tests  # Ensure tests are serialized correctly
                }, status=200)
            return JsonResponse({'message': 'No barcode found for this patient on this date.'}, status=404)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    return JsonResponse({'error': 'Patient ID and date are required.'}, status=400)





import logging
from django.http import JsonResponse
from .models import BarcodeTestDetails  # Replace with your actual model import

logger = logging.getLogger(__name__)

def get_max_barcode(request):
    try:
        max_barcode = 0  # Initialize the maximum barcode value
        # Retrieve all 'tests' fields from the database
        all_tests = BarcodeTestDetails.objects.values_list('tests', flat=True)
        for tests in all_tests:
            try:
                # Parse the tests JSON string if needed
                if isinstance(tests, str):  
                    tests = eval(tests)  # Convert string representation to a list of dicts (use json.loads if stored as JSON)

                if isinstance(tests, list):  # Ensure it's a list of test dictionaries
                    for test in tests:
                        barcode = test.get("barcode", "")
                        if barcode:
                            # Extract numeric part from the barcode
                            numeric_part = ''.join(filter(str.isdigit, barcode))
                            if numeric_part.isdigit():
                                numeric_value = int(numeric_part)
                                max_barcode = max(max_barcode, numeric_value)
            except Exception as inner_exception:
                logger.warning(f"Error processing tests: {inner_exception}")
                continue

        # Increment the max barcode value by 1
        next_barcode = max_barcode + 1

        # Format as a zero-padded 6-digit string
        formatted_next_barcode = f"{next_barcode:06d}"
        logger.debug(f"Next barcode generated: {formatted_next_barcode}")
        return JsonResponse({'next_barcode': formatted_next_barcode}, status=200)

    except Exception as e:
        logger.error(f"Error in get_max_barcode: {e}")
        return JsonResponse({'error': 'Failed to generate barcode'}, status=500)






   

from datetime import datetime

@csrf_exempt
def save_barcodes(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            patient_id = data.get('patient_id')
            patientname = data.get('patientname')
            age = data.get('age')
            gender = data.get('gender')
            segment = data.get('segment')
            sample_collector = data.get('sample_collector')
            barcode=data.get('barcode')
            date = data.get('date')  # Date as a string
            # Convert string to date object if needed
            if date:
                date = datetime.strptime(date, "%d/%m/%Y").date()  # Match format 'DD/MM/YYYY'
            bill_no = data.get('bill_no')
            tests = data.get('tests')
            # Save or update patient details
            BarcodeTestDetails.objects.create(
                patient_id=patient_id,
                patientname=patientname,
                age=age,
                gender=gender,
                date=date,
                segment=segment,
                sample_collector=sample_collector,
                barcode=barcode,
                bill_no=bill_no,
                tests=tests,
            )
            return JsonResponse({'message': 'Barcodes saved successfully!'}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

   

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
                'bill_no':patient.bill_no,
            }
            return JsonResponse(patient_data)
        else:
            return JsonResponse({'error': 'Patient not found'}, status=404)
   
    except Exception as e:
        return JsonResponse({'error': f'Error fetching patient details: {str(e)}'}, status=500)
   

from .models import Patient
from django.forms.models import model_to_dict

def get_patients_by_date(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        try:
            # Parse the input dates
            start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d').date()

            # Filter manually by comparing the date part
            patients = Patient.objects.all()
            filtered_patients = [
                patient for patient in patients if start_date_parsed <= patient.date.date() <= end_date_parsed
            ]

            # Convert the queryset to a list of dictionaries
            patient_data = [model_to_dict(patient) for patient in filtered_patients]
            return JsonResponse({'data': patient_data}, safe=False)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    return JsonResponse({'error': 'Both start_date and end_date parameters are required.'}, status=400)


def get_received_samples(request):
    # Get patient_id and date from the query parameters
    patient_id = request.GET.get('patient_id')
    date_str = request.GET.get('date')

    if not patient_id or not date_str:
        return JsonResponse({'error': 'Missing patient_id or date parameter'}, status=400)

    try:
        # Fetch SampleStatus entries for the given patient_id
        received_samples = SampleStatus.objects.filter(patient_id=patient_id)

        test_data = []
        for sample in received_samples:
            # Check if testdetails is a string or a list
            if isinstance(sample.testdetails, str):
                try:
                    test_list = json.loads(sample.testdetails)  # Parse JSON string
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Invalid testdetails format'}, status=400)
            elif isinstance(sample.testdetails, list):
                test_list = sample.testdetails  # Use as-is
            else:
                continue  # Skip invalid testdetails format

            for test_item in test_list:
                testname = test_item.get('testname')
                samplestatus = test_item.get('samplestatus')

                # Only include tests with 'Received' status and matching date
                if samplestatus == 'Received' and str(sample.date) == date_str:
                    test_info = {
                        "patient_id": sample.patient_id,
                        "patientname": sample.patientname,
                        "testname": testname,
                        "samplestatus": samplestatus,
                        "date": sample.date,
                        "segment": sample.segment
                    }
                    test_data.append(test_info)

        return JsonResponse({'data': test_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def convert_to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

@api_view(['GET'])
def patient_report(request):
    # Get the date parameter from the request
    date_str = request.GET.get('date')
    if not date_str:
        return Response({"error": "Date parameter is required"}, status=400)
   
    # Parse the date-time string and extract only the date part
    try:
        if 'T' in date_str:
            selected_date = datetime.fromisoformat(date_str).date()  # Handle ISO 8601 format
        else:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()  # Handle only date format
    except ValueError:
        return Response({"error": "Invalid date format. Use ISO 8601 format (YYYY-MM-DDTHH:MM:SS) or only the date (YYYY-MM-DD)."}, status=400)
   
    # Filter patients for the selected date, ensuring we match the date only
    patients = Patient.objects.filter(date__gte=selected_date, date__lt=selected_date + timedelta(days=1))
   
    # If no patients are found for the selected date, return a message
    if not patients:
        return Response({
            'message': "No data available for the selected date.",
            'report': {}
        })
   
    # Initialize variables to calculate totals
    gross_amount = 0
    discount = 0
    due_amount = 0
    payment_totals = {'Cash': 0, 'UPI': 0, 'Neft': 0, 'Cheque': 0, 'Credit': 0, 'PartialPayment': 0}
   
    # Process each patient's data
    for patient in patients:
        gross_amount += convert_to_float(patient.totalAmount)
        discount += convert_to_float(patient.discount)
        partial_payment = patient.PartialPayment
       
        # Safely parse PartialPayment
        if isinstance(partial_payment, str) and partial_payment.strip():
            try:
                partial_payment = json.loads(partial_payment)
            except json.JSONDecodeError:
                partial_payment = {}
        elif not isinstance(partial_payment, dict):
            partial_payment = {}
       
        # Add credited amount (due amount)
        if isinstance(partial_payment, dict):
            due_amount += convert_to_float(partial_payment.get('credit', 0))
            # Add payment method totals
            method = partial_payment.get('method')
            if method in payment_totals:
                payment_totals[method] += convert_to_float(partial_payment.get('totalAmount', 0))
       
        # Handle the main payment method field
        payment_method = patient.payment_method
        if isinstance(payment_method, str) and payment_method.strip():
            try:
                payment_method = json.loads(payment_method)
            except json.JSONDecodeError:
                payment_method = {}
       
        if isinstance(payment_method, dict):
            method = payment_method.get('paymentmethod')
            if method in payment_totals:
                payment_totals[method] += convert_to_float(patient.totalAmount)
   
    # Calculate pending amounts from the previous day
    previous_date = selected_date - timedelta(days=1)
    previous_day_patients = Patient.objects.filter(date__gte=previous_date, date__lt=previous_date + timedelta(days=1))
   
    pending_amount = 0
    for patient in previous_day_patients:
        partial_payment = patient.PartialPayment
       
        # Safely parse PartialPayment
        if isinstance(partial_payment, str) and partial_payment.strip():
            try:
                partial_payment = json.loads(partial_payment)
            except json.JSONDecodeError:
                partial_payment = {}
        elif not isinstance(partial_payment, dict):
            partial_payment = {}
       
        # Only add remainingAmount to pending_amount
        if isinstance(partial_payment, dict):
            pending_amount += convert_to_float(partial_payment.get('remainingAmount', 0))
   
    # Calculate the totals
    net_amount = gross_amount - (discount + due_amount)
    total_collection = net_amount
   
    # Prepare the report
    report = {
        'gross_amount': round(gross_amount, 2),
        'discount': round(discount, 2),
        'due_amount': round(due_amount, 2),  # Only credits are included in due amount
        'net_amount': round(net_amount, 2),
        'pending_amount': round(pending_amount, 2),  # Pending amounts from previous day
        'total_collection': round(total_collection, 2),
        'payment_totals': {key: round(value, 2) for key, value in payment_totals.items()},
    }
   
    return Response(report)





from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus

@csrf_exempt  # Allow GET, POST, and PATCH requests without CSRF protection
def get_test_details(request):
    try:
        # Securely encode password
        password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
        client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

        db = client.Lab  # Database name
        collection = db.labbackend_testdetails  # Collection name

        if request.method == 'GET':
            # Retrieve all documents in Testdetails collection
            test_details = list(collection.find({}, {'_id': 0}))  # Exclude MongoDB's default _id field
            return JsonResponse(test_details, safe=False, status=200)

        elif request.method == 'POST':
            try:
                data = json.loads(request.body.decode('utf-8'))
                if 'parameters' in data and isinstance(data['parameters'], list):
                    if not all(isinstance(param, dict) for param in data['parameters']):
                        return JsonResponse({'error': 'Invalid format for parameters: all elements must be dictionaries'}, status=400)
                    data['parameters'] = json.dumps(data['parameters'])
                else:
                    return JsonResponse({'error': 'Parameters should be a JSON array of dictionaries'}, status=400)

                # Insert data into MongoDB
                collection.insert_one(data)
                return JsonResponse({'message': 'Test details added successfully'}, status=201)

            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON data'}, status=400)
            except Exception as e:
                print("Error:", e)
                return JsonResponse({'error': 'An error occurred while saving data'}, status=500)

        elif request.method == 'PATCH':
            try:
                data = json.loads(request.body.decode('utf-8'))
                test_name = data.get('test_name')
                updated_parameters = data.get('parameters')

                if not test_name or updated_parameters is None:
                    return JsonResponse({'error': 'test_name and parameters are required'}, status=400)

                updated_parameters_json = json.dumps(updated_parameters)

                result = collection.update_one(
                    {'test_name': test_name},
                    {'$set': {'parameters': updated_parameters_json}}
                )

                if result.matched_count > 0:
                    return JsonResponse({'message': 'Parameters updated successfully'}, status=200)
                else:
                    return JsonResponse({'error': 'Test not found'}, status=404)

            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON data'}, status=400)
   
    except Exception as e:
        print("Error:", e)
        return JsonResponse({'error': 'An error occurred'}, status=500)


@csrf_exempt
def handle_patch_request(request):
    try:
        # MongoDB connection setup inside the function
        password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
        client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

        db = client.Lab  # Database name
        collection = db.labbackend_testdetails  # Collection name

        data = json.loads(request.body.decode('utf-8'))
        test_name = data.get('test_name')
       
        if not test_name:
            return JsonResponse({'error': 'test_name is required'}, status=400)

        # Update fields, excluding 'test_name'
        update_fields = {k: v for k, v in data.items() if k != 'test_name'}
        if update_fields:
            result = collection.update_one({'test_name': test_name}, {'$set': update_fields})
            if result.matched_count > 0:
                return JsonResponse({'message': 'Test details updated successfully'}, status=200)
            else:
                return JsonResponse({'error': 'Test not found'}, status=404)

        return JsonResponse({'message': 'No updates provided'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print("Error:", e)
        return JsonResponse({'error': 'An error occurred while updating data'}, status=500)

   
@csrf_exempt
def get_test_parameters(request, test_name):
    try:
        # MongoDB connection setup
        password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
        client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

        db = client.Lab  # Database name
        collection = db.labbackend_testdetails
        # Fetch the test details based on the test_name
        test = collection.find_one({"test_name": test_name}, {"_id": 0, "parameters": 1})  # Assuming parameters is a field in your document
        if test:
            return JsonResponse({"parameters": test.get("parameters", [])}, status=200)
        else:
            return JsonResponse({"error": "Test not found"}, status=404)
    except Exception as e:
        print("Error fetching parameters:", e)
        return JsonResponse({"error": "Failed to fetch parameters"}, status=500)


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
   
def get_last_referrer_code(request):
    last_clinical = ClinicalName.objects.order_by('-referrerCode').first()
    if last_clinical:
        return JsonResponse({'referrerCode': last_clinical.referrerCode})
    return JsonResponse({'referrerCode': 'SD0000'})
   

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
        collectors = RefBy.objects.all()
        serializer = RefBySerializer(collectors, many=True)
        return Response(serializer.data)


from .models import Patient
def compare_test_details(request):
    # MongoDB connection setup
    password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )
    db = client.Lab  # Database name
    collection = db.labbackend_testdetails  # Collection name
    # Retrieve the date and patient ID from the request
    date = request.GET.get('date')
    patient_id = request.GET.get('patient_id')
    if not date or not patient_id:
        return JsonResponse({'error': 'Date and patient_id parameters are required'}, status=400)
    try:
        # Validate the date format
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
            # Only process if the sample status is 'Received'
            if samplestatus == "Received":
                # Fetch test details directly from MongoDB Testdetails collection
                test_details = collection.find({"test_name": testname})
                for test_detail in test_details:
                    # Extract parameters as JSON from the test detail
                    parameters_json = test_detail.get('parameters')
                    # Parse the parameters JSON string into a Python object if it exists
                    if parameters_json:
                        try:
                            parameters = json.loads(parameters_json)
                        except json.JSONDecodeError:
                            return JsonResponse({'error': 'Invalid parameters JSON format'}, status=400)
                    else:
                        parameters = None  # Handle case where 'parameters' is missing or null
                    # Assuming you want to compare with a specific parameter
                    requested_parameter = request.GET.get('parameter')
                    if requested_parameter and parameters and requested_parameter not in parameters:
                        continue  # Skip if the requested parameter is not found
                    test_info = {
                        "patient_id": sample.patient_id,
                        "patientname": sample.patientname,
                        "testname": test_detail.get('test_name'),  # Use 'test_name' from Testdetails
                        "parameters": parameters,
                        "specimen_type": test_detail.get('specimen_type'),
                        "unit": test_detail.get('unit'),  # Updated key for units
                        "reference_range": test_detail.get('reference_range'),
                        "status": samplestatus
                    }
                    test_data.append(test_info)  # Append each test detail to test_data
    # Return all collected test details in the response
    return JsonResponse({'data': test_data})

from .models import SampleStatus
from .serializers import SampleStatusSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import json

@api_view(['GET'])
def get_samplestatus_testvalue(request):
    try:
        # Get the date from the query parameter
        date_str = request.query_params.get('date', None)
       
        # Ensure the date is provided
        if not date_str:
            return Response({"error": "Date parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
       
        # Convert the date string to a datetime object
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Get the start and end of the selected date range (to compare the datetime portion)
        start_of_day = datetime.combine(selected_date, datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)

        # Get all records from the SampleStatus table for the selected date
        sample_statuses = SampleStatus.objects.filter(date__gte=start_of_day, date__lt=end_of_day)

        filtered_sample_statuses = []

        # Iterate through each record to filter the testdetails array
        for sample_status in sample_statuses:
            # Parse testdetails if it's a string
            try:
                testdetails = json.loads(sample_status.testdetails) if isinstance(sample_status.testdetails, str) else sample_status.testdetails
            except json.JSONDecodeError:
                # If testdetails cannot be parsed, skip this record
                continue

            # Filter tests with samplestatus 'Received' or 'Outsource'
            filtered_tests = [
                test for test in testdetails
                if test.get('samplestatus') in ['Received', 'Outsource']
            ]

            if filtered_tests:
                # If matching tests are found, add the whole record to the filtered list
                sample_status_dict = sample_status.__dict__.copy()  # Make a copy of the sample_status dictionary
                sample_status_dict['testdetails'] = filtered_tests
                filtered_sample_statuses.append(sample_status_dict)

        # Serialize the filtered data
        serializer = SampleStatusSerializer(filtered_sample_statuses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


 

from .serializers import TestValueSerializer
from .models import Patient
@api_view(['GET', 'POST','PATCH'])
def save_test_value(request):
    if request.method == 'GET':
        patient_id = request.GET.get('patient_id')
        date = request.GET.get('date')
        testname = request.GET.get('testname')
        # Validate required parameters
        if not patient_id or not date or not testname:
            return Response({"error": "patient_id, date, and testname are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Fetch the test value record for the patient and date
            test_value_record = TestValue.objects.get(patient_id=patient_id, date=date)
            test_details = test_value_record.testdetails
            # Find the specific test by testname
            test = next((t for t in test_details if t['testname'] == testname), None)
            if not test:
                return Response({"error": "Test not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(test, status=status.HTTP_200_OK)
        except TestValue.DoesNotExist:
            return Response({"error": "No test values found for the given patient and date"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    elif request.method == 'POST':
        payload = request.data
        try:
            patient = Patient.objects.get(patient_id=payload['patient_id'])
            test_details_json = payload.get("testdetails", [])
            print("Received test details:", test_details_json)  # Debugging
            if not isinstance(test_details_json, list) or not test_details_json:
                return Response({"error": "Invalid test details format"}, status=status.HTTP_400_BAD_REQUEST)
            test_value_record, created = TestValue.objects.get_or_create(
                patient_id=patient.patient_id,
                date=payload.get('date'),
                defaults={
                    'patientname': patient.patientname,
                    'age': patient.age,
                    'testdetails': test_details_json,
                }
            )
            existing_test_details = test_value_record.testdetails if not created else []
            for test in test_details_json:
                testname = test.get('testname')
                if not testname:
                    return Response({"error": "Missing testname in test details"}, status=status.HTTP_400_BAD_REQUEST)
                existing_test = next((t for t in existing_test_details if t['testname'] == testname), None)
                if existing_test:
                    if 'parameters' in test and isinstance(test['parameters'], list):
                        if 'parameters' not in existing_test:
                            existing_test['parameters'] = []
                        for param in test['parameters']:
                            existing_param = next(
                                (p for p in existing_test['parameters'] if p['unit'] == param.get('unit')), None
                            )
                            if existing_param:
                                existing_param.update(param)
                            else:
                                existing_test['parameters'].append(param)
                    else:
                        existing_test['value'] = test.get('value', '')
                else:
                    existing_test_details.append(test)
            print("Final test details to save:", existing_test_details)  # Debugging
            test_value_record.testdetails = existing_test_details
            test_value_record.save()
            return Response({"message": "Test details saved successfully."}, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            return Response({"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print("Error in POST method:", str(e))  # Debugging
            return Response({"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    elif request.method == 'PATCH':
            # MongoDB connection
        password = quote_plus('Smrft@2024')
        # MongoDB connection with TLS certificate
        client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )
        db = client.Lab  # Database name
        collection = db.labbackend_testvalue
        # Extract parameters from the request
        patient_id = request.data.get("patient_id")
        date_str = request.data.get("date")  # Date as string
        test_details_json = request.data.get("testdetails", [])
        # Validate required fields
        if not patient_id or not date_str:
            return Response({"error": "patient_id and date are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Convert the date string to a datetime object
            date = datetime.strptime(date_str, "%Y-%m-%d")
            # Find the existing document for the patient and date
            test_value_record = collection.find_one({"patient_id": patient_id, "date": date})
            if not test_value_record:
                return Response(
                    {"error": "No record found for the given patient and date"},
                    status=status.HTTP_404_NOT_FOUND
                )
            # Fetch and deserialize existing test details
            existing_test_details = test_value_record.get("testdetails", "[]")
            if isinstance(existing_test_details, str):
                existing_test_details = json.loads(existing_test_details)
            # Process new test details
            for new_test in test_details_json:
                testname = new_test["testname"]
                # Check if the test already exists in the existing test details
                existing_test = next((t for t in existing_test_details if t["testname"] == testname), None)
                if existing_test:
                    # Update the existing test details
                    if "parameters" in new_test and new_test["parameters"]:
                        for new_param in new_test["parameters"]:
                            param_name = new_param["name"]
                            existing_param = next(
                                (p for p in existing_test.get("parameters", []) if p["name"] == param_name), None
                            )
                            if existing_param:
                                existing_param["value"] = new_param["value"]  # Update existing parameter value
                            else:
                                existing_test.setdefault("parameters", []).append(new_param)  # Add new parameter
                    else:
                        # Update the value and other details for tests without parameters
                        existing_test["value"] = new_test.get("value", existing_test.get("value", ""))
                        existing_test["unit"] = new_test.get("unit", existing_test.get("unit", "N/A"))
                        existing_test["reference_range"] = new_test.get("reference_range", existing_test.get("reference_range", "N/A"))
                        existing_test["specimen_type"] = new_test.get("specimen_type", existing_test.get("specimen_type", "N/A"))
                else:
                    # Add the new test to the test details
                    existing_test_details.append(new_test)
            # Update the document in the database
            collection.update_one(
                {"patient_id": patient_id, "date": date},
                {"$set": {"testdetails": json.dumps(existing_test_details)}}  # Serialize back to string
            )
            return Response({"message": "Test details updated successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
   

@api_view(['PATCH'])
def update_test_value(request):
    # MongoDB connection
    password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

    db = client.Lab  # Database name
    collection = db.labbackend_testvalue
    try:
        payload = request.data
        patient_id = payload.get("patient_id")
        date_str = payload.get("date")  # date coming as string
        test_details = payload.get("testdetails", [])
        if not test_details:
            return Response(
                {"error": "Missing or empty 'testdetails' field."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return Response({"error": "Invalid date format. Expected 'YYYY-MM-DD'."}, status=status.HTTP_400_BAD_REQUEST)
        # Fetch the relevant TestValue entry from MongoDB
        test_entry = collection.find_one({"patient_id": patient_id, "date": date})
        if not test_entry:
            return Response(
                {"error": "Test entry not found for the given patient and date."},
                status=status.HTTP_404_NOT_FOUND
            )
        # Parse the testdetails field if it's a string
        test_entry_details = json.loads(test_entry["testdetails"]) if isinstance(test_entry["testdetails"], str) else test_entry["testdetails"]
        # Update specific test values and remarks in the testdetails field
        for updated_test in test_details:
            for existing_test in test_entry_details:
                if existing_test["testname"] == updated_test["testname"]:
                    existing_test["value"] = updated_test.get("value", existing_test["value"])
                    existing_test["remarks"] = updated_test.get("remarks", existing_test.get("remarks", ""))  # Update remarks field
                    if "rerun" in updated_test:
                        existing_test["rerun"] = updated_test["rerun"]  # Update rerun only if explicitly provided
                    break
        # Update the test details in MongoDB
        collection.update_one(
            {"_id": test_entry["_id"]},
            {"$set": {"testdetails": json.dumps(test_entry_details)}}
        )
        return Response(
            {"message": "Test values updated successfully."},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from datetime import datetime
import pytz
import json
from pymongo import MongoClient
import certifi
from urllib.parse import quote_plus
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# Define IST timezone
TIME_ZONE = 'Asia/Kolkata'
IST = pytz.timezone(TIME_ZONE)

@api_view(['PATCH'])
def update_dispatch_status(request, patient_id):
    # MongoDB connection
    password = quote_plus('Smrft@2024')

    # MongoDB connection with TLS certificate
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
    )

    db = client.Lab  # Database name
    collection = db.labbackend_testvalue

    try:
        # Find the document for the given patient_id
        test_value_record = collection.find_one({"patient_id": patient_id})

        if not test_value_record:
            return Response({"error": "TestValue record not found"}, status=status.HTTP_404_NOT_FOUND)

        # Parse the testdetails field (convert JSON string to a Python list)
        test_details = json.loads(test_value_record.get("testdetails", "[]"))

        # Update dispatch status to true for all tests
        for test in test_details:
            test["dispatch"] = True
            # Only set dispatch_time if dispatch is True
            if test.get("dispatch", False):
                test["dispatch_time"] = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')  # Convert to IST format

        # Convert the updated testdetails back to a JSON string
        updated_test_details = json.dumps(test_details)

        # Update the document in MongoDB
        result = collection.update_one(
            {"patient_id": patient_id},  # Match the document
            {"$set": {"testdetails": updated_test_details}}  # Update the testdetails field
        )

        if result.matched_count == 0:
            return Response({"error": "Failed to update dispatch status"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Dispatch status updated successfully."}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
   

@api_view(['GET'])
def test_values(request):
    # Get the date parameter from the request
    date_str = request.GET.get('date')
    try:
        # Convert the date string to a Python date object
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        # Fetch the TestValue data for the given date
        test_values = TestValue.objects.filter(date=selected_date)
        # Serialize the data
        serializer = TestValueSerializer(test_values, many=True)
        # Return the serialized data in the response
        return Response(serializer.data)
    except ValueError:
        return Response({"error": "Invalid date format"}, status=400)


from datetime import datetime
from django.utils import timezone  # Import Django's timezone module
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus

@csrf_exempt
@require_http_methods(["PATCH"])
def approve_test_detail(request, patient_id, test_index):
    # MongoDB connection
    password = quote_plus('Smrft@2024')

    # MongoDB connection with TLS certificate
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
    )

    db = client.Lab  # Database name
    collection = db.labbackend_testvalue  # Your collection name

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

            # If approve is set to True, update approve_time with formatted timestamp
        if update_data["approve"]:
            # Get the timezone-aware current time
            approve_time = timezone.localtime(timezone.now())  # Convert to local timezone
            # Format the timestamp to the desired format (e.g., '2025-02-14 15:23:45')
            formatted_time = approve_time.strftime('%Y-%m-%d %H:%M:%S')  # Use the same format as your first example
            test_details[test_index]["approve_time"] = formatted_time


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
    # MongoDB connection
    password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

    db = client.Lab  # Database name
    collection = db.labbackend_testvalue  # Your collection name
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
   

@csrf_exempt
@api_view(['PATCH'])
def update_test_detail(request, patient_id):
    # MongoDB connection
    password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

    db = client.Lab  # Database name
    collection = db.labbackend_testvalue  # Your collection name
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



from datetime import datetime, timedelta
from django.http import JsonResponse
from .models import SampleStatus, BarcodeTestDetails
from django.forms.models import model_to_dict
import json
def get_samplepatients_by_date(request):
    date = request.GET.get('date')
    if not date:
        return JsonResponse({'error': 'Date parameter is required.'}, status=400)
    try:
        parsed_date = datetime.fromisoformat(date)
        # Fetch all patients from BarcodeTestDetails within the given date
        barcode_patients = BarcodeTestDetails.objects.filter(
            date__gte=parsed_date, date__lt=parsed_date + timedelta(days=1)
        )
        # Fetch all SampleStatus data within the same date range
        sample_status_data = SampleStatus.objects.filter(
            date__gte=parsed_date, date__lt=parsed_date + timedelta(days=1)
        )
        # Convert SampleStatus into a dictionary { (patient_id, testname) -> samplestatus }
        sample_status_dict = {}
        for sample in sample_status_data:
            test_details = sample.testdetails  # No json.loads()
            if isinstance(test_details, str):  # Convert only if it's a string
                test_details = json.loads(test_details)
            for test in test_details:
                key = (sample.patient_id, test["testname"])
                sample_status_dict[key] = test["samplestatus"]
        # Filter out patients whose tests are already in SampleStatus, except when 'Pending'
        filtered_patients = []
        for patient in barcode_patients:
            patient_tests = patient.tests  # No json.loads()
            if isinstance(patient_tests, str):  # Convert only if it's a string
                patient_tests = json.loads(patient_tests)
            valid_tests = []
            for test in patient_tests:
                key = (patient.patient_id, test["testname"])
                if key not in sample_status_dict or sample_status_dict[key] == "Pending":
                    valid_tests.append(test)  # Include this test
            if valid_tests:  # Only add patients who have at least one valid test
                patient_dict = model_to_dict(patient)
                patient_dict["tests"] = valid_tests  # Attach filtered test details
                filtered_patients.append(patient_dict)
        return JsonResponse({"data": filtered_patients}, safe=False)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DDTHH:MM:SS.'}, status=400)
   

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import SampleStatus
@csrf_exempt
def sample_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            for entry in data:
                patient_id = entry['patient_id']
                patientname = entry['patientname']
                barcode = entry['barcode']
                segment = entry['segment']
                date = entry.get('date', '')
                testdetails = entry.get('testdetails', [])
                # Check if an entry with the same date, patient_id, patientname, and testdetails exists
                existing_entry = SampleStatus.objects.filter(
                    patient_id=patient_id,
                    patientname=patientname,
                    barcode=barcode,
                    segment=segment,
                    date=date,
                    testdetails=testdetails
                ).first()
                if existing_entry:
                    return JsonResponse({'message': 'Data already exists'}, status=409)
                # If no existing entry, save the new one
                patient = SampleStatus(
                    patient_id=patient_id,
                    patientname=patientname,
                    barcode=barcode,
                    segment=segment,
                    date=date,
                    testdetails=testdetails
                )
                patient.save()
            return JsonResponse({'message': 'Data saved successfully'}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request method'}, status=405)

from django.utils import timezone  # Import Django's timezone module
from django.http import JsonResponse
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def update_sample_status(request, patient_id):
    password = quote_plus('Smrft@2024')

    # MongoDB connection with TLS certificate
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
    )

    db = client.Lab  # Database name
    collection = db.labbackend_samplestatus

    if request.method == 'PUT':
        try:
            data = json.loads(request.body)  # Parse the incoming JSON data
            updates = data  # Use updates array directly

            print(f"Received patient_id: {patient_id}, updates: {updates}")

            # Find all patients with the given patient_id in MongoDB
            patients = collection.find({"patient_id": patient_id})

            if not patients:
                return JsonResponse({'error': 'No patients found with the given patient_id'}, status=404)

            update_count = 0

            for patient in patients:
                if isinstance(patient.get('testdetails'), str):
                    try:
                        patient['testdetails'] = json.loads(patient['testdetails'])  # Parse JSON string to list
                    except json.JSONDecodeError:
                        return JsonResponse({'error': 'Invalid test details format'}, status=400)

                updated_testdetails = []
                test_found = False  # Flag to check if the test is found

                for entry in patient['testdetails']:
                    if isinstance(entry, dict) and entry.get('testname') in [update['testname'] for update in updates]:
                        for update in updates:
                            if entry['testname'] == update['testname']:
                                entry['samplestatus'] = update['samplestatus']
                                entry['collectd_by'] = update['collectd_by']

                                # Store collected time in IST with the desired format
                                ist_time = timezone.now().astimezone(timezone.get_current_timezone())

                                # Format the timestamp to the desired format (e.g., '2025-02-14 15:23:45')
                                formatted_time = ist_time.strftime('%Y-%m-%d %H:%M:%S')  # Use the same format as your first example

                                if update['samplestatus'] == "Sample Collected":
                                    entry['samplecollected_time'] = formatted_time

                                test_found = True

                        updated_testdetails.append(entry)

                if not test_found:
                    continue  # Skip if no test found

                # Update the testdetails array in MongoDB
                result = collection.update_one(
                    {"_id": patient['_id']},
                    {"$set": {"testdetails": json.dumps(updated_testdetails)}}
                )

                if result.modified_count > 0:
                    update_count += 1

            if update_count > 0:
                return JsonResponse({'message': f'Successfully updated sample status for {update_count} patients.'}, status=200)
            else:
                return JsonResponse({'error': 'No updates were made'}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)




@csrf_exempt
def get_sample_collected(request):
    if request.method == "GET":
        try:
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
                # Filter test details based on samplestatus only
                for detail in test_details:
                    if detail.get("samplestatus") == "Sample Collected":
                        # If patient is not already in the dictionary, add them
                        if sample.patient_id not in patient_data:
                            patient_data[sample.patient_id] = {
                                "patient_id": sample.patient_id,
                                "patientname": sample.patientname,
                                "segment": sample.segment,
                                "testdetails": []
                            }
                        # Append the test details
                        patient_data[sample.patient_id]["testdetails"].append({
                            "testname": detail.get("testname", "N/A"),
                            "container": detail.get("container", "N/A"),
                            "samplecollector": detail.get("samplecollector", "N/A"),
                            "samplestatus": detail.get("samplestatus", "N/A"),
                            "samplecollected_time": detail.get("samplecollected_time", "N/A"),
                        })
            # Convert the dictionary to a list
            data = list(patient_data.values())
            # Return the filtered data as a response
            return JsonResponse({"data": data}, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

       
from datetime import datetime
from django.utils import timezone  # Import Django's timezone module
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import json
import certifi
from urllib.parse import quote_plus

@csrf_exempt
def update_sample_collected(request, patient_id):
    # MongoDB connection setup
    password = quote_plus('Smrft@2024')

    # MongoDB connection with TLS certificate
    client = MongoClient(
        f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
        tls=True,  # Enable TLS/SSL
        tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
    )

    db = client.Lab  # Database name
    collection = db.labbackend_samplestatus  # Collection name

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

            # Parse testdetails as a Python list
            testdetails = json.loads(patient_sample.get('testdetails', '[]'))

            # Apply updates based on testIndex
            for update in updates:
                testIndex = update.get("testIndex")
                new_status = update.get("samplestatus")
                received_by = update.get("received_by")
                rejected_by = update.get("rejected_by")
                outsourced_by = update.get("oursourced_by")
                remarks = update.get("remarks")  # New field for rejection remarks

                if testIndex is None or new_status is None:
                    return JsonResponse({"error": "samplestatus and testIndex are required"}, status=400)

                # Ensure testIndex is valid
                if testIndex < 0 or testIndex >= len(testdetails):
                    return JsonResponse({"error": "Invalid testIndex"}, status=400)

                test_entry = testdetails[testIndex]

                # Update the sample status and associated fields
                test_entry['samplestatus'] = new_status

                # Get current time in the correct timezone
                current_time = timezone.now().astimezone(timezone.get_current_timezone())
                formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')  # Format the time

                if new_status == "Received":
                    test_entry['received_time'] = formatted_time
                    test_entry['received_by'] = received_by
                elif new_status == "Rejected":
                    test_entry['rejected_time'] = formatted_time
                    test_entry['rejected_by'] = rejected_by
                    test_entry['remarks'] = remarks  # Add rejection remarks
                elif new_status == "Outsource":
                    test_entry['oursourced_time'] = formatted_time
                    test_entry['oursourced_by'] = outsourced_by

            # Save changes back to the database
            collection.update_one(
                {"patient_id": patient_id},
                {"$set": {"testdetails": json.dumps(testdetails)}}  # Re-serialize testdetails as JSON
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

        # Initialize status variables
        status = "Registered"  # Default status
        approval_status = "Not Approved"
        dispatch_status = "Not Dispatched"

        # Check if a SampleStatus record exists for the patient
        try:
            sample_status_record = SampleStatus.objects.get(patient_id=patient_id)
            sample_test_details = sample_status_record.testdetails  # JSON list of tests

            # Flags for sample collection and receiving
            all_collected = all(test.get("samplestatus") == "Sample Collected" for test in sample_test_details)
            partially_collected = any(test.get("samplestatus") == "Sample Collected" for test in sample_test_details)
            all_received = all(test.get("samplestatus") == "Received" for test in sample_test_details)
            partially_received = any(test.get("samplestatus") == "Received" for test in sample_test_details)

            # Check conditions for Collected and Received statuses
            if all_collected:
                status = "Collected"
            elif partially_collected:
                status = "Partially Collected"
            if all_received:
                status = "Received"
            elif partially_received:
                status = "Partially Received"

        except SampleStatus.DoesNotExist:
            pass  # If no sample status exists, proceed to check further statuses

        # Check if a TestValue record exists for the patient
        try:
            test_value_record = TestValue.objects.get(patient_id=patient_id)
            test_value_details = test_value_record.testdetails  # JSON list of tests

            # Flags for testing and approval
            all_tested = all(test.get("value") is not None for test in test_value_details)
            partially_tested = any(test.get("value") is not None for test in test_value_details)
            approve_all = all(test.get("approve", False) for test in test_value_details)
            approve_partial = any(test.get("approve", False) for test in test_value_details)
            dispatch_all = all(test.get("dispatch", False) for test in test_value_details)

            # Check conditions for Tested, Approved, and Dispatched statuses
            if status == "Received" or status == "Partially Received":
                if all_tested:
                    status = "Tested"
                elif partially_tested:
                    status = "Partially Tested"

            if approve_all:
                status = "Approved"
            elif approve_partial:
                status = "Partially Approved"

            if dispatch_all:
                status = "Dispatched"

        except TestValue.DoesNotExist:
            pass  # If no TestValue exists, proceed without modifying the status

        return JsonResponse({
            'patient_id': patient.patient_id,
            'patient_name': patient.patientname,
            'status': status,
            'approval_status': approval_status,
            'dispatch_status': dispatch_status
        })

    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)
   
from .models import Patient  # Adjust the import based on your project structure
def get_barcode_by_date(request):
    date = request.GET.get('date')  # Expecting 'YYYY-MM-DD'
    if date:
        try:
            parsed_date = datetime.strptime(date, '%Y-%m-%d')  # Parse the provided date
            start_of_day = datetime.combine(parsed_date, datetime.min.time())  # 2025-01-23 00:00:00
            end_of_day = datetime.combine(parsed_date, datetime.max.time())  # 2025-01-23 23:59:59.999999
           
            # Query patients with a range filter
            patients = Patient.objects.filter(date__gte=start_of_day, date__lte=end_of_day)
           
            # Serialize the data
            patient_data = [model_to_dict(patient) for patient in patients]
            return JsonResponse({'data': patient_data}, safe=False)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)
    return JsonResponse({'error': 'Date parameter is required.'}, status=400)
def get_patient_test_details(request):
    patient_id = request.GET.get('patient_id')
    if not patient_id:
        return JsonResponse({'error': 'Patient ID is required'}, status=400)
    try:
        # Fetch TestValue, SampleStatus, and BarcodeTestDetails based on patient_id
        test_values = TestValue.objects.filter(patient_id=patient_id)
        sample_status = SampleStatus.objects.filter(patient_id=patient_id)
        barcode_details = BarcodeTestDetails.objects.filter(patient_id=patient_id).first()
       
        # If no test values are found
        if not test_values:
            return JsonResponse({'error': 'Test values not found for the given patient ID'}, status=404)
       
        # Parse barcodes from BarcodeTestDetails
        barcodes = []
        if barcode_details:
            # Ensure `tests` is handled correctly as a string
            if isinstance(barcode_details.tests, str):
                tests = json.loads(barcode_details.tests)  # Deserialize JSON string
            else:
                tests = barcode_details.tests  # Use as is if already a list
           
            barcodes = [test.get("barcode") for test in tests if test.get("barcode")]
       
        # Prepare patient details
        patient_details = {
            "patient_id": test_values[0].patient_id,
            "patientname": test_values[0].patientname,
            "age": test_values[0].age,
            "date": test_values[0].date,
            "barcodes": barcodes,  # Add barcodes to the response
            "testdetails": []
        }
       
        # Extract test details from TestValue and SampleStatus
        for test in test_values[0].testdetails:
            testname = test.get("testname")
            specimen_type = test.get("specimen_type", "N/A")
            unit = test.get("unit", "N/A")
            value = test.get("value", "N/A")
            reference_range = test.get("reference_range", "N/A")
            # Fetch corresponding SampleStatus for this testname
            status = next(
                (status for status in sample_status[0].testdetails if status.get("testname") == testname), None)
            samplecollected_time = status.get("samplecollected_time") if status else None
            received_time = status.get("received_time") if status else None
            patient_details["testdetails"].append({
                "testname": testname,
                "specimen_type": specimen_type,
                "unit": unit,
                "value": value,
                "reference_range": reference_range,
                "samplecollected_time": samplecollected_time,
                "received_time": received_time
            })
        return JsonResponse(patient_details, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
   

from .models import Patient
@csrf_exempt
def overall_report(request):
    if request.method == "GET":
        # Get the selected_date parameter from the request
        selected_date = request.GET.get("selected_date", None)

        if selected_date:
            # Parse the selected_date and filter patients
            try:
                # Parse the selected date (only the date part)
                if 'T' in selected_date:
                    date_filter = datetime.fromisoformat(selected_date).date()  # Handle ISO 8601 format
                else:
                    date_filter = datetime.strptime(selected_date, "%Y-%m-%d").date()  # Handle only date format
               
                # Filter patients by the selected date
                patients = Patient.objects.filter(date__gte=date_filter, date__lt=date_filter + timedelta(days=1))
               
            except ValueError:
                return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        else:
            # If no date is provided, fetch all data
            patients = Patient.objects.all()

        formatted_data = []

        for patient in patients:
            # Format the required fields
            age_combined = f"{patient.age} {patient.age_type}"  # Combine age and age_type
            discount = patient.discount if patient.discount else "0"  # Default discount to 0

            # Extract test names and calculate the count
            test_list = json.loads(patient.testname) if isinstance(patient.testname, str) else patient.testname
            testnames = ", ".join([test["testname"] for test in test_list])  # Extract test names
            no_of_tests = len(test_list)  # Count the number of tests

            # Parse payment method details
            payment_data = json.loads(patient.payment_method) if isinstance(patient.payment_method, str) else patient.payment_method
            paymentmethod = payment_data.get("paymentmethod", "N/A")

            # Handle PartialPayment case
            partial_payment_method = None  # Default to None
            if paymentmethod == "PartialPayment":
                # Parse PartialPayment field
                partial_payment_data = json.loads(patient.PartialPayment) if isinstance(patient.PartialPayment, str) else patient.PartialPayment
                if partial_payment_data:  # Check if partial_payment_data exists
                    partial_payment_method = partial_payment_data.get("method", "N/A")
                else:
                    partial_payment_method = "N/A"

            # Append data to the list
            formatted_data.append({
                "date": patient.date.strftime("%Y-%m-%d"),
                "patient_id": patient.patient_id,
                "patient_name": patient.patientname,
                "gender": patient.gender,
                "age": age_combined,
                "b2b": patient.B2B,
                "sample_collector": patient.sample_collector,
                "sales_representative": patient.sales_representative,
                "total_amount": patient.totalAmount,
                "credit_amount": patient.credit_amount,
                "discount": discount,
                "payment_method": paymentmethod if paymentmethod != "PartialPayment" else f"{partial_payment_method}",
                "test_names": testnames,
                "no_of_tests": no_of_tests,  # Add the count of tests
            })

        # Return the formatted data as JSON
        return JsonResponse(formatted_data, safe=False)
    else:
        return JsonResponse({"error": "Invalid request method. Only GET is allowed."}, status=405)
   

@csrf_exempt
def credit_amount_update(request, patient_id):
    from datetime import datetime
    import json
    from pymongo import MongoClient

    password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

    db = client.Lab  # Database name
    collection = db['labbackend_patient']

    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
           
            # Convert all incoming data to strings (except for the date)
            credit_amount = str(body.get("credit_amount", ""))
            amount_paid = str(body.get("amount_paid", ""))
            paid_date = body.get("paid_date", None)
           
            # Validate required fields
            if not credit_amount:
                return JsonResponse({"error": "Missing required field: credit_amount."}, status=400)

            # Fetch the patient document
            patient = collection.find_one({"patient_id": patient_id})
            if not patient:
                return JsonResponse({"error": "Patient not found."}, status=404)

            # Parse existing credit details or initialize as empty list
            credit_details = patient.get("credit_details", [])

            # Calculate the updated credit amount (as a string)
            current_credit_amount = float(patient.get("credit_amount", 0))
            updated_credit_amount = current_credit_amount - float(amount_paid)

            # Append the new entry to credit_details
            credit_details.append({
                "credit_amount": credit_amount,
                "amount_paid": amount_paid,
                "paid_date": paid_date,
                "remaining_amount": str(updated_credit_amount)
            })

            # Update the database
            collection.update_one(
                {"patient_id": patient_id},
                {
                    "$set": {
                        "credit_amount": str(updated_credit_amount),
                        "credit_details": json.dumps(credit_details)  # Store as JSON string
                    }
                }
            )

            return JsonResponse({
                "message": "Credit amount updated successfully.",
                "credit_details": credit_details
            })
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method. Only PATCH is allowed."}, status=405)



@api_view(['PATCH'])
def update_credit_amount(request, patient_id):
    # MongoDB connection setup
    password = quote_plus('Smrft@2024')

        # MongoDB connection with TLS certificate
    client = MongoClient(
            f'mongodb+srv://shinovalab:{password}@cluster0.xbq9c.mongodb.net/Lab?retryWrites=true&w=majority',
            tls=True,  # Enable TLS/SSL
            tlsCAFile=certifi.where()  # Use certifi's CA certificate bundle
        )

    db = client.Lab  # Database name
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


from django.core.mail import EmailMessage
from django.conf import settings  # To access the settings for DEFAULT_FROM_EMAIL
@api_view(['POST'])
def send_email(request):
    try:
        subject = request.data.get('subject', 'No Subject')
        message = request.data.get('message', 'No Message')
        # Use default recipient if none provided
        recipient_list = request.data.get('recipients', ['parthibansmrft@gmail.com'])  # Default recipient
        # Use default sender if none provided
        from_email = request.data.get('from_email', settings.DEFAULT_FROM_EMAIL)  # Default sender
        signature = 'Contact Us, \n Shanmuga Hospital, \n 24, Saradha College Road,\n Salem-636007 Tamil Nadu,\n \n 6369131631,0427 270 6666,\n info@shanmugahospital.com,\n https://shanmugahospital.com/'
        files = request.FILES.getlist('attachments')
        # Ensure recipient_list is a list
        if isinstance(recipient_list, str):
            recipient_list = [recipient_list]  # Convert string to list if only one email address is provided
        # Ensure at least one recipient is provided
        if not recipient_list:
            return JsonResponse({'status': 'error', 'message': 'At least one recipient is required to send the email.'}, status=400)
        email = EmailMessage(
            subject=subject,
            body=message+"\n\n"+signature,
            from_email=from_email,  # Sender's email
            to=recipient_list,      # List of recipients
        )
        for file in files:
            email.attach(file.name, file.read(), file.content_type)
        email.send()
        return JsonResponse({'status': 'success', 'message': 'Email sent successfully!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
   

from .serializers import SalesVisitLogSerializer
from .models import SalesVisitLog
@csrf_exempt
@api_view(['GET', 'POST'])
def salesvisitlog(request):
    if request.method == 'POST':
        serializer = SalesVisitLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'GET':
        date = request.query_params.get('date', None)
        week = request.query_params.get('week', None)
        month = request.query_params.get('month', None)
        logs = SalesVisitLog.objects.all()
        if date:
            # Filter by specific date
            logs = logs.filter(date=datetime.strptime(date, "%Y-%m-%d").date())
        elif week:
            # Filter by week (start and end date range)
            start_date = datetime.strptime(week, "%Y-%m-%d").date()
            end_date = start_date + timedelta(days=6)
            logs = logs.filter(date__gte=start_date, date__lte=end_date)
        elif month:
            # Filter by month (start and end of the month)
            try:
                year, month = map(int, month.split('-'))
                start_date = datetime(year, month, 1)
                if month == 12:  # Handle December edge case
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month + 1, 1)
                logs = logs.filter(date__gte=start_date, date__lt=end_date)
            except ValueError:
                return Response({"error": "Invalid month format. Use YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SalesVisitLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


from .models import HospitalLab
from .serializers import HospitalLabSerializer
@api_view(['GET', 'POST'])
def hospitallabform(request):
    if request.method == 'GET':
        # Retrieve all HospitalLab objects and serialize them
        hospital_labs = HospitalLab.objects.all()
        serializer = HospitalLabSerializer(hospital_labs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        # Handle the creation of a new HospitalLab object
        serializer = HospitalLabSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Hospital/Lab details saved successfully."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   

from .models import LogisticData
from .serializers import LogisticDataSerializer
@api_view(['POST'])
def save_logistic_data(request):
    if request.method == 'POST':
        serializer = LogisticDataSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Save the logistic data
            return Response({"message": "Data saved successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
   
   
@api_view(['GET'])
def get_logistic_data(request):
    if request.method == 'GET':
        data = LogisticData.objects.all()  # Fetch all logistic data
        serializer = LogisticDataSerializer(data, many=True)
        return Response(serializer.data)
   

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from .models import LogisticTask
from .serializers import LogisticTaskSerializer
@api_view(['POST', 'GET'])
def savesamplecollectordetails(request):
    if request.method == 'POST':
        tasks_data = request.data
        # Ensure tasks_data is a list
        if isinstance(tasks_data, dict):  # If a single dictionary is received, convert it into a list
            tasks_data = [tasks_data]
        for task_data in tasks_data:
            # Check if the task already exists
            existing_task = LogisticTask.objects.filter(
                samplecollectorname=task_data.get("samplecollectorname"),
                date=task_data.get("date"),
                lab_name=task_data.get("lab_name"),
                salesperson=task_data.get("salesperson"),
            ).exists()
            if not existing_task:
                serializer = LogisticTaskSerializer(data=task_data)
                if serializer.is_valid():
                    serializer.save()
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Tasks saved successfully."}, status=status.HTTP_201_CREATED)
    elif request.method == 'GET':
        today_date = datetime.now().date()
        tasks = LogisticTask.objects.filter(date=today_date)
        serializer = LogisticTaskSerializer(tasks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from pymongo import MongoClient
@api_view(['PATCH'])
def update_sample_collector_details(request):
    client = MongoClient("mongodb+srv://shinovalab:Smrft%402024@cluster0.xbq9c.mongodb.net/?retryWrites=true&w=majority")
    db = client["Lab"]
    collection = db["labbackend_logistictask"]
    try:
        data = request.data
        samplecollectorname = data.get("samplecollectorname")
        date = data.get("date")
        lab_name = data.get("lab_name")
        salesperson = data.get("salesperson")
        # Convert string date to datetime format if stored as a Date object
        if date:
            try:
                date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return Response({"message": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        filter_condition = {
            "samplecollectorname": samplecollectorname,
            "date": date,
            "lab_name": lab_name,
            "salesperson": salesperson
        }
        # Debugging: Check if document exists
        existing_doc = collection.find_one(filter_condition)
        if not existing_doc:
            return Response({"message": "No matching document found in the database.", "filter_used": filter_condition}, status=status.HTTP_404_NOT_FOUND)
        # Define the update fields
        update_fields = {}
        if "task" in data:
            update_fields["task"] = data["task"]
        if "remarks" in data:
            update_fields["remarks"] = data["remarks"]
        if not update_fields:
            return Response({"message": "No valid fields provided for update."}, status=status.HTTP_400_BAD_REQUEST)
        # Update the document
        result = collection.update_one(filter_condition, {"$set": update_fields})
        if result.matched_count > 0:
            return Response({"message": "Document updated successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "No matching document found after update attempt.", "filter_used": filter_condition}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
   

def getlogisticdatabydate(request):
    # Get query parameters
    sample_collector = request.GET.get('sampleCollector', None)
    if not sample_collector:
        return JsonResponse({"error": "sampleCollector is required"}, status=400)
    # Filter data by sampleCollector
    data = LogisticData.objects.filter(sampleCollector=sample_collector)
    # Serialize the data
    serializer = LogisticDataSerializer(data, many=True)
    return JsonResponse(serializer.data, safe=False)
   

@csrf_exempt
def get_patient_by_id(request, patient_id):
    """
    API endpoint to fetch patient details based on patient ID.
    """
    if request.method == 'GET':
        try:
            # Fetch the patient using Django ORM
            patient = Patient.objects.get(patient_id=patient_id)
            # Convert the patient object to a dictionary
            patient_data = {
                "patient_id": patient.patient_id,
                "patientname": patient.patientname,
                "phone": patient.phone,
                "gender": patient.gender,
                "email": patient.email,
                "address": patient.address,
                "age": patient.age,
                "age_type": patient.age_type,
                "sample_collector": patient.sample_collector,
                "sales_representative": patient.sales_representative,
                "date": patient.date.strftime('%Y-%m-%d'),  # Format date as string
                "discount": patient.discount,
                "lab_id": patient.lab_id,
                "refby": patient.refby,
                "branch": patient.branch,
                "B2B": patient.B2B,
                "segment": patient.segment,
                "testname": patient.testname,
                "totalAmount": patient.totalAmount,
                "payment_method": patient.payment_method,
                "registeredby": patient.registeredby,
                "bill_no": patient.bill_no,
                "PartialPayment": patient.PartialPayment,
            }
            return JsonResponse(patient_data, safe=False)
        except Patient.DoesNotExist:
            return JsonResponse({"error": "Patient not found"}, status=404)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


from datetime import datetime
import pytz
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Patient, SampleStatus, TestValue
from .serializers import PatientSerializer, SampleStatusSerializer, TestValueSerializer

# Define the timezone for India Standard Time (IST)
IST = pytz.timezone('Asia/Kolkata')

class ConsolidatedDataView(APIView):
    def get(self, request):
        # Default to today's date if no date is provided
        date = request.query_params.get('date', datetime.now().strftime('%Y-%m-%d'))
       
        try:
            # Parse the input date
            input_date = datetime.strptime(date, '%Y-%m-%d').date()

            # Retrieve all patients and filter manually for the date
            patients = Patient.objects.all()
            filtered_patients = [patient for patient in patients if patient.date.date() == input_date]

            response_data = []
            for patient in filtered_patients:
                sample_status = SampleStatus.objects.filter(patient_id=patient.patient_id).first()
                test_value = TestValue.objects.filter(patient_id=patient.patient_id).first()

                if not (sample_status and test_value):
                    continue

                for test in sample_status.testdetails:
                    matching_test = next(
                        (tv for tv in test_value.testdetails if tv['testname'] == test['testname']),
                        None
                    )
                    if matching_test:
                        # Check if the time fields are missing and set them to 'pending'
                        samplecollected_time = test.get('samplecollected_time', 'pending')
                        dispatch_time = matching_test.get('dispatch_time', 'pending')

                        # If either time is 'pending', don't calculate processing time
                        if samplecollected_time == 'pending' or dispatch_time == 'pending':
                            total_processing_time = 'pending'
                        else:
                            try:
                                # Convert datetime strings to aware datetime objects using the IST timezone
                                samplecollected_time_dt = datetime.fromisoformat(samplecollected_time).replace(tzinfo=IST)
                                dispatch_time_dt = datetime.fromisoformat(dispatch_time).replace(tzinfo=IST)
                                total_processing_time = (dispatch_time_dt - samplecollected_time_dt).total_seconds() / 60  # Total time in minutes
                            except ValueError:
                                total_processing_time = 'pending'  # In case of invalid datetime format

                        response_data.append({
                            "patient_id": patient.patient_id,
                            "patient_name": patient.patientname,
                            "age": patient.age,
                            "test_name": test['testname'],
                            "collected_time": samplecollected_time,
                            "received_time": test['received_time'],
                            "approval_time": matching_test['approve_time'],
                            "dispatch_time": dispatch_time,
                            "total_processing_time": total_processing_time
                        })

            return Response(response_data, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
