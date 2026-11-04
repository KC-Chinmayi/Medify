
import json
import logging

from decouple import config
from google import genai
from google.genai import types

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from medicines.models import Medicine
from users.models import Profile
from .models import AILog


logger = logging.getLogger(__name__)


def get_mock_recommendation(symptoms, available_meds):
    """Provide demo recommendations when no Gemini API key is configured."""

    mock_meds = []
    advice = (
        "These are general demo suggestions based on the symptoms provided. "
        "Please consult a qualified doctor."
    )

    if "cough" in symptoms.lower() or "cold" in symptoms.lower():
        mock_meds = [
            medicine for medicine in available_meds
            if "syrup" in medicine.name.lower()
            or "vicks" in medicine.name.lower()
        ][:2]

    elif "pain" in symptoms.lower() or "headache" in symptoms.lower():
        mock_meds = [
            medicine for medicine in available_meds
            if medicine.category
            and "pain" in medicine.category.name.lower()
        ][:2]

    else:
        mock_meds = list(available_meds[:2])

    return {
        "disclaimer": (
            "This is a demo AI response, not a medical diagnosis "
            "or prescription. Consult a doctor before taking medicine."
        ),
        "advice": advice,
        "recommended_medicine_ids": [medicine.id for medicine in mock_meds]
    }


@csrf_exempt
def get_ai_recommendation(request):

    if request.method != "POST":
        return JsonResponse(
            {"error": "Only POST allowed"},
            status=405
        )

    # 1. Read and validate the request
    try:
        data = json.loads(request.body)
        symptoms = data.get("symptoms", "").strip()

    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid JSON"},
            status=400
        )

    if not symptoms:
        return JsonResponse(
            {"error": "Please provide symptoms"},
            status=400
        )

    # 2. Get user health conditions
    health_context = "No known medical conditions."

    if request.user.is_authenticated:
        try:
            profile = request.user.profile

            conditions = []

            if profile.has_diabetes:
                conditions.append("Diabetes")

            if profile.has_thyroid:
                conditions.append("Thyroid condition")

            if profile.other_conditions:
                conditions.append(profile.other_conditions)

            if conditions:
                health_context = (
                    "Patient has the following conditions: "
                    + ", ".join(conditions)
                )

        except Profile.DoesNotExist:
            pass

    # 3. Fetch available medicines
    available_meds = Medicine.objects.filter(is_active=True).select_related(
        "category"
    )

    med_catalog = "\n".join(
        [
            (
                f"ID: {medicine.id} | "
                f"Name: {medicine.name} | "
                f"Category: "
                f"{medicine.category.name if medicine.category else 'Uncategorized'} | "
                f"Description: {medicine.description}"
            )
            for medicine in available_meds
        ]
    )

    # 4. Construct the Gemini prompt
    prompt = f"""
You are an AI assistant for a pharmacy application called Medify.

IMPORTANT SAFETY RULES:
- You are providing demo decision support, NOT a medical diagnosis.
- Do not prescribe medicines or claim that a medicine will cure a condition.
- Always advise the user to consult a qualified doctor.
- Consider the user's existing health conditions.
- Never recommend a medicine that is not present in the catalogue.
- Use only medicine IDs that appear in the catalogue.
- If no suitable medicine is available, return an empty list.

User symptoms:
{symptoms}

User health profile:
{health_context}

Available medicine catalogue:
{med_catalog}

Return valid JSON only, matching this structure:

{{
    "disclaimer": "Consult a doctor before taking any medicine.",
    "advice": "General safety advice based on the symptoms.",
    "recommended_medicine_ids": [1, 2]
}}
"""

    try:
        # 5. Read the API key from the .env file
        api_key = config("GEMINI_API_KEY", default="").strip()

        # 6. Use mock mode if no API key is configured
        if not api_key:

            ai_result = get_mock_recommendation(
                symptoms,
                available_meds
            )

        else:
            # 7. Connect to Gemini using the new Google GenAI SDK
            client = genai.Client(api_key=api_key)

            response = client.models.generate_content(
                model="gemini-flash-lite-latest",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )

            # 8. Parse Gemini's JSON response
            response_text = response.text

            if not response_text:
                raise ValueError("Gemini returned an empty response.")

            ai_result = json.loads(response_text)

            if not isinstance(ai_result, dict):
                raise ValueError("Gemini returned an invalid JSON structure.")

            if not isinstance(ai_result.get("recommended_medicine_ids"), list):
                ai_result["recommended_medicine_ids"] = []

            if not isinstance(ai_result.get("advice"), str):
                ai_result["advice"] = (
                    "Please consult a qualified doctor for medical advice."
                )

            if not isinstance(ai_result.get("disclaimer"), str):
                ai_result["disclaimer"] = (
                    "Consult a doctor before taking any medicine."
                )

        # 9. Validate medicine IDs against the actual database
        med_ids = ai_result.get("recommended_medicine_ids", [])

        valid_ids = []

        for medicine_id in med_ids:
            if isinstance(medicine_id, int) and medicine_id not in valid_ids:
                valid_ids.append(medicine_id)

        recommended_meds = list(
            Medicine.objects.filter(
                id__in=valid_ids,
                is_active=True
            ).select_related("category")
        )

        # 10. Save the AI response in the database
        AILog.objects.create(
            symptoms=symptoms,
            response_advice=ai_result.get("advice", "")
        )

        # 11. Format medicine details and images
        formatted_meds = []

        for medicine in recommended_meds:

            image_url = "/static/images/pills.jpg"

            if (
                "syrup" in medicine.name.lower()
                or "liquid" in medicine.name.lower()
            ):
                image_url = "/static/images/syrup.jpg"

            elif (
                "cream" in medicine.name.lower()
                or "ointment" in medicine.name.lower()
            ):
                image_url = "/static/images/cream.jpg"

            elif (
                medicine.category
                and "first aid" in medicine.category.name.lower()
            ):
                image_url = "/static/images/firstaid.jpg"

            formatted_meds.append({
                "id": medicine.id,
                "name": medicine.name,
                "price": str(medicine.price),
                "description": medicine.description,
                "image": image_url
            })

        # 12. Return the final response
        return JsonResponse({
            "success": True,
            "disclaimer": ai_result.get("disclaimer"),
            "advice": ai_result.get("advice"),
            "medicines": formatted_meds
        })

    except Exception:
        logger.exception("Gemini API error in get_ai_recommendation")

        return JsonResponse({
            "success": False,
            "error": (
                "Unable to generate AI recommendations right now. "
                "Please try again later."
            )
        }, status=500)
