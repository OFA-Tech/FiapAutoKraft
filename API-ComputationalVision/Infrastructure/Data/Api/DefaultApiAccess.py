import httpx
from urllib.parse import urlencode
from typing import Dict, Any

from dependency_injector.wiring import inject, Provide

from Domain.Models.ApplicationConfigurationModels.ApiModels.RestApiRequestModel import RestApiRequestModel
from Domain.Utils import Utils


class DefaultApiAccess:
    @inject
    def __init__(self, utils: Utils = Provide["AppContainer.utils"]):
        self._utils = utils

    @staticmethod
    async def rest_api_request(request: RestApiRequestModel) -> httpx.Response:
        method = request.Method.value.upper()
        timeout = request.Timeout or 30

        # Build full URL with query parameters
        url = request.URL
        if request.QueryParameters:
            query_string = urlencode(request.QueryParameters)
            url = f"{url}?{query_string}"

        headers: Dict[str, str] = request.Headers or {}
        if request.Authentication:
            headers["Authorization"] = f"{request.Authentication.Type} {request.Authentication.Authorization}"
        headers["Accept"] = "application/json"

        # Prepare request body
        content: Any = None
        if request.Body:
            headers["Content-Type"] = "application/json"
            content = request.Body

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, http2=True) as client:
            try:
                response = await client.request(method, url, headers=headers, content=content)
                response.raise_for_status()
                return response
            except httpx.HTTPError as ex:
                raise RuntimeError(f"HTTP request failed: {str(ex)}")