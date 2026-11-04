from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Order, OrderItem
from medicines.models import Medicine
import json

@csrf_exempt
def create_order(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            med_id = data.get("medicine_id")
            patient_name = data.get("patient_name", "Guest")
            amount = data.get("amount")
            payment_id = data.get("payment_id")

            med = Medicine.objects.get(id=med_id)
            order = Order.objects.create(
                patient_name=patient_name,
                total_amount=amount,
                razorpay_payment_id=payment_id,
                is_paid=True
            )
            OrderItem.objects.create(
                order=order,
                medicine=med,
                quantity=1,
                price=amount
            )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"error": "POST only"}, status=405)
