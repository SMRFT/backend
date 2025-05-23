#urls.py
from django.urls import path
from . import views
from .views import generate_invoice, get_invoices,update_invoice,delete_invoice
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import whatsapp
urlpatterns = [
    path('registration/', views.registration, name='registration'),
    path('login/', views.login, name='login'),
    path('patient/create/', views.create_patient, name='create_patient'),
    path('latest-patient-id/', views.get_latest_patient_id, name='get_latest_patient_id'),
    path("patient/update/<str:patient_id>/", views.update_patient, name="update_patient"),
    path('patients_get_barcode/', views.get_barcode_by_date, name='get_barcode_by_date'),
    path('get-max-barcode/', views.get_max_barcode, name='get_max_barcode'),
    path('save-barcodes/', views.save_barcodes, name='save_barcodes'),
    path('latest-bill-no/', views.get_latest_bill_no, name='get_latest_bill_no'),
    path('get-existing-barcode/', views.get_existing_barcode, name='get_latest_bill_no'),
    path('patient-get/', views.get_patient_details, name='sample_status'),
    path('patients/', views.get_patients_by_date, name='get_patients_by_date'),
    path('patients/<str:patient_id>/', views.get_patients_by_date, name='get_patients_by_date'),
    path('get_received_samples/', views.get_received_samples, name='get_received_samples'),
    path('patient_report/', views.patient_report, name='patient_report'),
    path('test_details/', views.get_test_details, name='get_test_details'),
    path('test_details_test/', views.handle_patch_request, name='get_test_details'),
    path('test_parameters/<str:test_name>/', views.get_test_parameters, name='get_test_parameters'),
    path('compare_test_details/', views.compare_test_details, name='compare_test_details'),
    path('get_patient_test_details/', views.get_patient_test_details, name='get_patient_test_details'),
    path('test-value/save/', views.save_test_value, name='save_test_value'),
    path('test-value/update/', views.update_test_value, name='update_test_value'),
    path('update_dispatch_status/<str:patient_id>/', views.update_dispatch_status, name='update_dispatch_status'),
    path('sample-collector/', views.sample_collector, name='create_sample_collector'),
    path('refby/', views.refby, name='refby'),
    path('clinical_name/', views.clinical_name, name='create_organisation'),
    path('clinical_name/last/', views.get_last_referrer_code, name='get_last_referrer_code'),
    path('test-report/', views.get_test_report, name='get_test_report'),
    path('test-values/', views.get_test_values, name='get_test_values'),
    path('test-values/<str:patient_id>/<int:test_index>/approve/', views.approve_test_detail, name='approve_test_detail'),
    path('test-values/<str:patient_id>/<int:test_index>/rerun/', views.rerun_test_detail, name='rerun_test_detail'),
    path('update-test-detail/<str:patient_id>/', views.update_test_detail, name='update_test_detail'),
    path("get_sample_collected/", views.get_sample_collected, name="get_sample_collected"),
    path("update_sample_collected/<str:patient_id>/", views.update_sample_collected, name="update_sample_collected"),
    path('sample_patient/', views.get_samplepatients_by_date, name='get_samplepatients_by_date'),
    path('sample_status/', views.sample_status, name='sample_status'),
    path('testvalue/', views.test_values, name='get_test_values'),
    path('update_sample_status/<str:patient_id>/', views.update_sample_status, name='update_sample_status'),
    path('samplestatus-testvalue/', views.get_samplestatus_testvalue, name='sample-status-list'),
    path('patient_overview/', views.patient_overview, name='patient_overview'),
    path('patient_test_status/', views.patient_test_status, name='patient_test_status'),
    path('all-patients/', views.get_all_patients, name='get_all_patients'),
    path('overall_report/', views.overall_report, name='overall_report'),
    path('patient_test_sorting/', views.patient_test_sorting, name='patient_test_sorting'),
    path('credit_amount/<str:patient_id>/', views.credit_amount_update, name='credit_amount_update'),
    path('update-credit/<str:patient_id>/', views.update_credit_amount, name='update_credit_amount'),
    path('send-email/', views.send_email, name='send_email'),
    path('SalesVisitLog/', views.salesvisitlog, name='salesvisitlog'),
    path('SalesVisitLogReport/', views.get_sales_log, name='sales-visit-log-report'),
    path('hospitallabform/', views.hospitallabform, name='hospitallabform'),
    path('save-logistic-data/', views.save_logistic_data, name='save-logistic-data'),
    path('get_logistic_data/', views.get_logistic_data, name='get_logistic_data'),
    path('patient/get/<str:patient_id>/', views.get_patient_by_id, name='get_patient_by_id'),
    path('getlogisticdata/', views.getlogisticdatabydate, name='getlogisticdatabydate'),
    path('check-barcode/', views.check_barcode, name='check-barcode'),
    # path('getsamplecollectordetails/', views.getsamplecollectordetails, name='getsamplecollectordetails'),
    path('savesamplecollector/', views.savesamplecollectordetails, name='savesamplecollectordetails'),
    path('updatesamplecollectordetails/', views.update_sample_collector_details, name='update_sample_collector_details'),
    path('patient/get/<str:patient_id>/', views.get_patient_by_id, name='get_patient_by_id'),
    path('consolidated-data/', views.ConsolidatedDataView.as_view(), name='consolidated_data'),
    path("generate-invoice/", generate_invoice, name="generate-invoice"),
    path("get-invoices/", get_invoices, name="get-invoices"),
    path("update-invoice/<str:invoice_number>/", update_invoice, name="update-invoice"),
    path("delete-invoice/<str:invoice_id>/", delete_invoice, name="delete-invoice"),
    path('salesdashboard/', views.salesdashboard, name='salesdashboard'),
    path('getsalesmapping/',views.getsalesmapping, name='getsalesmapping'),
    path('logisticdashboard/', views.logisticdashboard, name='logisticdashboard'),
    path('search_refund/', views.search_refund, name='search_refund'),
    path('verify_and_process_refund/', views.verify_and_process_refund, name='verify_and_process_refund'),
    path('search_cancellation/', views.search_cancellation, name='search_cancellation'),
    path("upload-pdf/", whatsapp.upload_pdf_to_gridfs, name="upload_pdf"),
    path("get-file/<str:file_id>/", whatsapp.get_pdf_from_gridfs, name="get_pdf"),
    path("send-whatsapp/", whatsapp.send_whatsapp_message, name="send_whatsapp"),
    path('get_patients/', views.get_patients, name='get_patients'),
    path('patient/update_billing/<str:patient_id>/', views.update_billing, name='update_billing'),
    path('patient/tests/<str:patient_id>/<str:date>/', views.get_patient_tests, name='get_patient_tests'),
    path('clinical_name/', views.clinical_name, name='create_organisation'),
    path('clinical_name/last/', views.get_last_referrer_code, name='get_last_referrer_code'),
    path('clinical-names/', views.ClinicalNameViewSet.as_view({'get': 'list'}), name='clinical-names-list'),
    path('clinical-names/<str:referrerCode>/', views.ClinicalNameViewSet.as_view({'get': 'retrieve'}), name='clinical-name-detail'),
    path('clinical-names/<str:referrerCode>/first_approve/', views.ClinicalNameViewSet.as_view({'patch': 'first_approve'}), name='clinical-name-first-approve'),
    path('clinical-names/<str:referrerCode>/final_approve/', views.ClinicalNameViewSet.as_view({'patch': 'final_approve'}), name='clinical-name-final-approve'),
    path('search_refund/', views.search_refund, name='search_refund'),
    path('verify_and_process_refund/', views.verify_and_process_refund, name='verify_and_process_refund'),
    path('generate_otp_refund/', views.generate_otp_refund, name='generate_otp_refund'),
    path('generate_otp_cancellation/', views.generate_otp_cancellation, name='generate_otp_cancellation'),
    path('search_cancellation/', views.search_cancellation, name='search_cancellation'),
    path('verify_and_process_cancellation/', views.verify_and_process_cancellation, name='verify_and_process_cancellation'),
    path('refund_cancellation_logs/', views.logs_api, name='refund_cancellation_logs'),
    path('mou-preview/<str:file_id>/',views.preview_mou_file, name='preview_mou_file'),
    path('dashboard-data/', views.dashboard_data, name='dashboard_data'),

]
