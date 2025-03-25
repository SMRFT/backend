import gridfs
from django.http import JsonResponse
from django.core.files.storage import default_storage
from pymongo import MongoClient
from bson.objectid import ObjectId
from django.views.decorators.csrf import csrf_exempt
# MongoDB Connection
client = MongoClient("mongodb://admin:ifS2nTs6vm@103.205.141.208:27017/Lab?authSource=admin")
db = client["Lab"]
fs = gridfs.GridFS(db)
@csrf_exempt
def upload_pdf_to_gridfs(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        file_id = fs.put(file, filename=file.name)  # Upload to GridFS
        file_url = f"http://127.0.0.1:8000/get-file/{str(file_id)}"  # Generate URL
        return JsonResponse({"file_id": str(file_id), "file_url": file_url})
    return JsonResponse({"error": "No file uploaded"}, status=400)
from django.http import HttpResponse
from bson import ObjectId

@csrf_exempt
def get_pdf_from_gridfs(request, file_id):
    try:
        file = fs.get(ObjectId(file_id))
        response = HttpResponse(file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{file.filename}"'
        return response
    except:
        return JsonResponse({"error": "File not found"}, status=404)


import json
from twilio.rest import Client
from django.http import JsonResponse
import os

TWILIO_ACCOUNT_SID = "ACe1d37f2342c44648499add958166abe2"
TWILIO_AUTH_TOKEN = "5ca7ffa9ca23cf7849cc94f752717d7d"
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox Number
@csrf_exempt
def send_whatsapp_message(request):
    if request.method == "POST":
        data = json.loads(request.body)
        phone = data.get("phone")
        message = data.get("message")

        if not phone or not message:
            return JsonResponse({"error": "Phone and message are required"}, status=400)

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        try:
            msg = client.messages.create(
                body=message,
                from_=TWILIO_WHATSAPP_NUMBER,
                to=f"whatsapp:{phone}",
            )
            return JsonResponse({"message": "WhatsApp message sent!", "sid": msg.sid})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)

