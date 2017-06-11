from .models import OAuthToken
from django.core.exceptions import ObjectDoesNotExist
from roombookings.helpers import PrettyJsonResponse as JsonResponse

import base64
import hashlib
import hmac


def oauth_token_check(required_scopes=None):
    def oauth_token_and_scope(view_func):
        def wrapped(request, *args, **kwargs):
            try:
                client_secret_proof = request.GET.get('client_secret_proof')
            except KeyError:
                response = JsonResponse({
                    "ok": False,
                    "error": "No Client Secret Proof provided"
                })
                response.status_code = 400
                return response
                
            try:
                token_code = request.GET.get("token")
            except KeyError:
                response = JsonResponse({
                    "ok": False,
                    "error": "No token provided via GET."
                })
                response.status_code = 400
                return response
            
            try:
                token = OAuthToken.objects.get(api_token=token_code)
            except ObjectDoesNotExist:
                response = JsonResponse({
                    "ok": False,
                    "error": "Token does not exist"
                })
                response.status_code = 400
                return response

            app = token.app
            hmac_digest = hmac.new(app.client_secret, msg=token_code, digestmod=hashlib.sha256).digest()
            hmac_b64 = base64.b64encode(hmac_digest).decode()
            if client_secret_proof != hmac_b64:
                 response = JsonResponse({
                    "ok": False,
                    "error": "Client secret HMAC verification failed."
                })
                response.status_code = 400
                return response

            scope = token.scope

            scope_map = {
                "roombookings": scope.private_roombookings,
                "timetable": scope.private_timetable,
                "uclu": scope.private_uclu
            }

            for s in required_scopes:
                if not scope_map[s]:
                    response = JsonResponse({
                        "ok": False,
                        "error": "No permission to access this data"
                    })
                    response.status_code = 400
                    return response

            if not scope_map[scope_name]:
                response = JsonResponse({
                    "ok": False,
                    "error": "No permission to access this data"
                })
                response.status_code = 400
                return response

            kwargs['user'] = token.user

            return view_func(request, *args, **kwargs)
        return wrapped
    return oauth_token_and_scope
