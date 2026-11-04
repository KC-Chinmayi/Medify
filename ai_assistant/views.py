import os
import json
import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from medicines.models import Medicine
from users.models import Profile
from .models import AILog

# Make sure you set this in your environment or settings
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "AIzaSyDKUeVw1muIhyE45HBAw68Yo3Rtx1Kc96g"))

@csrf_exempt
def get_ai_recommendation(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        symptoms = data.get("symptoms", "")
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not symptoms:
        return JsonResponse({"error": "Please provide symptoms"}, status=400)

    # 1. Fetch user health conditions if they are logged in
    health_context = "No known medical conditions."
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            conditions = []
            if profile.has_diabetes: conditions.append("Diabetes")
            if profile.has_thyroid: conditions.append("Thyroid condition")
            if profile.other_conditions: conditions.append(profile.other_conditions)

            if conditions:
                health_context = "Patient has the following conditions: " + ", ".join(conditions)
        except Profile.DoesNotExist:
            pass

    # 2. Get list of available medicines
    available_meds = Medicine.objects.filter(is_active=True)
    med_catalog = "\n".join([f"ID: {m.id} | Name: {m.name} | Category: {m.category.name} | Desc: {m.description}" for m in available_meds])

    # 3. Construct prompt for Gemini
    prompt = f"""
    You are an AI assistant for a pharmacy app called Medify.
    IMPORTANT SAFETY RULE: You are providing demo decision support, NOT a medical diagnosis or prescription.
    Always add a disclaimer advising the user to consult a doctor.

    The user is reporting the following symptoms: "{symptoms}"
    User Health Profile: {health_context}

    Here is our catalog of available medicines:
    {med_catalog}

    Based strictly on the catalog above, recommend the most appropriate medicines for the symptoms.
    Consider their health profile! If they have diabetes, avoid suggesting sugary syrups if alternative exists, or warn them.

    Return the response strictly in JSON format matching this structure:
    {{
        "disclaimer": "Consult a doctor before taking any medicine...",
        "advice": "Your custom advice based on their symptoms and health profile.",
        "recommended_medicine_ids": [1, 2]
    }}
    Do not return markdown, just raw JSON.
    """

    try:
        # Check if we are in mock mode (no real API key provided)
        api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyDKUeVw1muIhyE45HBAw68Yo3Rtx1Kc96g")

        if api_key == "YOUR_API_KEY_HERE":
            # Mock the AI behavior for the demo
            import time
            time.sleep(1) # simulate network

            mock_meds = []
            advice = "Based on your symptoms, here are some general recommendations. "
            if "cough" in symptoms.lower() or "cold" in symptoms.lower():
                mock_meds = [m for m in available_meds if "Syrup" in m.name or "Vicks" in m.name][:2]
                advice += "Please consider a cough syrup or vaporub for congestion."
            elif "pain" in symptoms.lower() or "headache" in symptoms.lower():
                mock_meds = [m for m in available_meds if "Pain" in m.category.name][:2]
                advice += "Over-the-counter pain relievers can help with headaches and muscle aches."
            elif "alarm" in symptoms.lower():
                advice += "You seem to be setting an alarm or feeling anxious. Consider resting."
            else:
                mock_meds = available_meds[:2] # generic fallback

            med_ids = [m.id for m in mock_meds]
            ai_result = {
                "disclaimer": "Consult a doctor before taking any medicine. This is a demo AI.",
                "advice": advice,
                "recommended_medicine_ids": med_ids
            }
        else:
            # Actual Gemini API Call
            model = genai.GenerativeModel('gemini-flash-lite-latest')
            response = model.generate_content(prompt)
            ai_result = json.loads(response.text.strip().strip('```json').strip('```'))

        # LOG IT TO MYSQL
        AILog.objects.create(symptoms=symptoms, response_advice=ai_result.get("advice", ""))

        # Fetch the actual medicine objects to return to the frontend
        med_ids = ai_result.get("recommended_medicine_ids", [])
        recommended_meds = list(Medicine.objects.filter(id__in=med_ids))

        # Format the result with images
        formatted_meds = []
        for m in recommended_meds:
            img_url = "/static/images/pills.jpg"
            if "Syrup" in m.name or "Liquid" in m.name: img_url = "/static/images/syrup.jpg"
            elif "Cream" in m.name or "Ointment" in m.name: img_url = "/static/images/cream.jpg"
            elif m.category and "First Aid" in m.category.name: img_url = "/static/images/firstaid.jpg"

            formatted_meds.append({
                "id": m.id,
                "name": m.name,
                "price": str(m.price),
                "description": m.description,
                "image": img_url
            })

        return JsonResponse({
            "success": True,
            "disclaimer": ai_result.get("disclaimer"),
            "advice": ai_result.get("advice"),
            "medicines": formatted_meds
        })

    except Exception as e:
        error_msg = str(e)
        print(f"Gemini API Error: {error_msg}")
        return JsonResponse({
            "success": False,
            "error": f"AI Error: {error_msg}"
        }, status=500)
