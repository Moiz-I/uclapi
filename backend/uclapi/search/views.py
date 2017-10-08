from rest_framework.decorators import api_view
from django.http import JsonResponse

from roombookings.decorators import does_token_exist, log_api_call, throttle

import os
import requests


@api_view(['GET'])
@does_token_exist
@throttle
@log_api_call
def people(request):
    if "query" not in request.GET:
        response = JsonResponse({
            "ok": False,
            "error": "No query provided."
        })
        response.status_code = 400
        return response

    query = request.GET["query"]

    url = (
        "{}?{}={}"
        .format(
            os.environ["SEARCH_API_URL"],
            os.environ["SEARCH_API_QUERY_PARAMS"],
            query,
        )
    )

    r = requests.get(url)

    results = r.json()["response"]["resultPacket"]["results"][:20]

    def serialize_person(person):
        return {
            "name": person["title"],
            "department": person["metaData"].get("7", ""),
            "email": person["metaData"].get("E", ""),
            "status": person["metaData"].get("g", ""),
        }

    people = [serialize_person(person) for person in results]

    return JsonResponse({
        "ok": True,
        "people": people
    })