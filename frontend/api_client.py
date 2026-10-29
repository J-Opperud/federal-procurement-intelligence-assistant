import httpx

class APIError(Exception):
    def __init__(self, response, message: str = None):
        self.response = response
        if message:
            self.user_message = message
        elif response is not None:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            self.user_message = f"API Error ({response.status_code}): {detail}"
        else:
            self.user_message = "An unknown API error occurred."
        super().__init__(self.user_message)


class ScoutAPI:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout_seconds: float = 180.0,
    ) -> None:
        cleaned_url = base_url.strip().rstrip("/")
        if not cleaned_url:
            raise ValueError("The API base URL cannot be empty.")
        self.base_url = cleaned_url
        self.token = token
        self.timeout = httpx.Timeout(timeout_seconds, connect=5.0)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def get_current_user(self):
        if not self.token:
            raise APIError("Please sign in to continue.")
    

    def register(self, username: str, password: str) -> dict:
        """Register a new user account."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/auth/register",
                    json={"username": username, "password": password},
                )
        except httpx.RequestError as e:
            raise APIError(None, message=f"Connection error to backend at {self.base_url}: {e}")

        # Matches the 201 Created status code from your backend schema
        if response.status_code != 201:
            raise APIError(response)
            
        return response.json() # Returns {"id": int, "username": str, "is_active": bool, "created_at": str}

    
    def login(self, username: str, password: str) -> dict:
        """Authenticate user and return access token."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/auth/token",
                    json={"username": username, "password": password}, # Changed from data= to json=
                )
        except httpx.RequestError as e:
            raise APIError(None, message=f"Connection error to backend at {self.base_url}: {e}")

        if response.status_code != 200:
            raise APIError(response)
        return response.json()

    def get_current_user(self) -> dict:
        """Get current authenticated user info."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/auth/me", headers=self._headers())
        except httpx.RequestError as e:
            raise APIError(None, message=f"Connection error: {e}")

        if response.status_code != 200:
            raise APIError(response)
        return response.json()

    def ask(self, question: str) -> dict:
        """Submit query to the RAG intelligence engine."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/ask",
                    json={"question": question},
                    headers=self._headers(),
                )
        except httpx.RequestError as e:
            raise APIError(None, message=f"Connection error: {e}")

        if response.status_code != 200:
            raise APIError(response)
        return response.json()

    def get_research_queries(self, limit: int = 10, offset: int = 0) -> list:
        """Fetch past research queries."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(
                    f"{self.base_url}/research/queries",
                    params={"limit": limit, "offset": offset},
                    headers=self._headers(),
                )
        except httpx.RequestError as e:
            raise APIError(None, message=f"Connection error: {e}")

        if response.status_code != 200:
            raise APIError(response)
        return response.json()

    def sync_notices(self, posted_from: str, posted_to: str, notice_type: str, limit: int) -> dict:
        """Trigger sync of SAM.gov notices."""
        payload = {
            "posted_from": posted_from,
            "posted_to": posted_to if posted_to else None,
            "notice_type": notice_type if notice_type else None,
            "limit": limit,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/documents/sync",
                    json=payload,
                    headers=self._headers(),
                )
        except httpx.RequestError as e:
            raise APIError(None, message=f"Connection error: {e}")

        if response.status_code != 200:
            raise APIError(response)
        return response.json()

    def search_documents(self, keyword: str = None, notice_type: str = None, posted_from: str = None, posted_to: str = None, page: int = 1, page_size: int = 20) -> dict:
        """Searches locally stored notices with full backend parameter support."""
        params = {"page": page, "page_size": page_size}
        if keyword:
            params["keyword"] = keyword
        if notice_type:
            params["notice_type"] = notice_type
        if posted_from:
            params["posted_from"] = posted_from
        if posted_to:
            params["posted_to"] = posted_to
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/documents", params=params, headers=self._headers())
        except httpx.RequestError as e:
            raise APIError(None, message=f"Connection error to backend at {self.base_url}: {e}")

        if response.status_code != 200:
            raise APIError(response)
        return response.json()

    def search_documents(self, keyword: str = None, notice_type: str = None, posted_from: str = None, posted_to: str = None, page: int = 1, page_size: int = 20) -> dict:
        """Searches locally stored notices without calling SAM.gov."""
        params = {"page": page, "page_size": page_size}
        if keyword:
            params["keyword"] = keyword
        if notice_type:
            params["notice_type"] = notice_type
        if posted_from:
            params["posted_from"] = posted_from
        if posted_to:
            params["posted_to"] = posted_to
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/documents", params=params, headers=self._headers())
        except httpx.RequestError as e:
            raise APIError(None, message=f"Connection error to backend at {self.base_url}: {e}")

        if response.status_code != 200:
            raise APIError(response)
        return response.json()

    def get_document_detail(self, sam_notice_id: str) -> dict:
        """Retrieves a specific local notice by its SAM notice ID."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(f"{self.base_url}/documents/{sam_notice_id}", headers=self._headers())
        except httpx.RequestError as e:
            raise APIError(None, message=f"Connection error to backend at {self.base_url}: {e}")

        if response.status_code != 200:
            raise APIError(response)
        return response.json()