from django.http import JsonResponse
from .models import Medicine

def medicine_search(request):
    query = request.GET.get("q", "")

    from django.db.models import Q
    from .models import SearchLog

    if query:
        # LOG IT TO MYSQL
        SearchLog.objects.create(query=query)

        medicines = Medicine.objects.filter(
            Q(name__icontains=query) | Q(category__name__icontains=query),
            is_active=True
        )
    else:
        medicines = Medicine.objects.filter(is_active=True)

    data = []
    for medicine in medicines:
        cat_name = medicine.category.name if medicine.category else ""
        img_url = "/static/images/pills.jpg"
        if "Syrup" in medicine.name or "Liquid" in medicine.name: img_url = "/static/images/syrup.jpg"
        elif "Cream" in medicine.name or "Ointment" in medicine.name: img_url = "/static/images/cream.jpg"
        elif "First Aid" in cat_name: img_url = "/static/images/firstaid.jpg"

        data.append({
            "id": medicine.id,
            "name": medicine.name,
            "price": str(medicine.price),
            "description": medicine.description,
            "category": cat_name,
            "image": img_url
        })

    return JsonResponse({
        "success": True,
        "medicines": data
    })
