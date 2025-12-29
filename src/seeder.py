"""
Formbricks API seeder.

Seeds generated data into Formbricks using only public APIs.
Uses Management API for users/surveys and Client API for responses.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib3

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .config import config
from .schemas import Response, ResponseList, Survey, SurveyList, User, UserList

# Disable SSL warnings for self-signed certificates in local dev
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console()


class FormbricksSeeder:
    """Seeds data into Formbricks via APIs."""
    
    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        environment_id: str = None,
    ):
        """
        Initialize seeder.
        
        Args:
            base_url: Formbricks base URL (defaults to config)
            api_key: API key for Management API (defaults to config)
            environment_id: Environment ID (defaults to config)
        """
        self.base_url = (base_url or config.FORMBRICKS_URL).rstrip("/")
        self.api_key = api_key or config.FORMBRICKS_API_KEY
        self.environment_id = environment_id or config.FORMBRICKS_ENVIRONMENT_ID
        
        # API endpoints
        self.management_api = f"{self.base_url}"
        self.client_api = f"{self.base_url}/client"
        
        # Track created resources for dependency resolution
        self.created_users: Dict[str, str] = {}  # email -> id
        self.created_surveys: Dict[str, str] = {}  # local_id -> api_id
    
    def _check_connection(self) -> bool:
        """
        Check if Formbricks is accessible.
        
        Returns:
            True if accessible, False otherwise
        """
        try:
            response = requests.get(
                self.base_url,
                timeout=5,
                verify=False
            )
            return response.status_code < 500
        except requests.exceptions.RequestException:
            return False
    
    def _management_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make authenticated request to Management API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to management API base)
            data: Request body (for POST/PUT)
            params: Query parameters
            
        Returns:
            Response object
        """
        url = f"{self.management_api}/{endpoint.lstrip('/')}"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            params=params,
            timeout=30,
            verify=False  # Disable SSL verification for self-signed certs in local dev
        )
        
        response.raise_for_status()
        return response
    
    def _client_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make request to Client API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body
            
        Returns:
            Response object
        """
        url = f"{self.client_api}/{endpoint.lstrip('/')}"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            timeout=30,
            verify=False  # Disable SSL verification for self-signed certs in local dev
        )
        
        response.raise_for_status()
        return response
    
    def seed_users(self, users: UserList) -> None:
        """
        Seed users via Management API.
        
        Note: Formbricks might not have a direct "create user" API.
        This is a placeholder - actual implementation depends on API availability.
        May need to use team invitations or other mechanisms.
        
        Args:
            users: Users to create
        """
        console.print("\n👥 Seeding users...", style="bold blue")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Creating users...", total=len(users.users))
            
            for user in users.users:
                try:
                    # Note: This endpoint is a placeholder
                    # Actual Formbricks API might use different approach
                    # (e.g., team invitations, organization members, etc.)
                    
                    # Attempt to create via team members endpoint
                    response = self._management_request(
                        "POST",
                        f"environments/{self.environment_id}/members",
                        data={
                            "email": user.email,
                            "name": user.name,
                            "role": user.role,
                        }
                    )
                    
                    user_data = response.json()
                    self.created_users[user.email] = user_data.get("id", user.email)
                    
                    progress.console.print(
                        f"  ✓ {user.name} ({user.email})",
                        style="green"
                    )
                    
                except requests.exceptions.HTTPError as e:
                    # User might already exist or endpoint not available
                    # Store email as fallback ID
                    self.created_users[user.email] = user.email
                    
                    progress.console.print(
                        f"  ⚠ {user.name}: {e.response.status_code}",
                        style="yellow"
                    )
                
                progress.advance(task)
                time.sleep(0.5)  # Rate limiting
        
        console.print(f"✅ User seeding complete", style="green")
    
    def seed_surveys(self, surveys: SurveyList) -> None:
        """
        Seed surveys via Management API.
        
        Args:
            surveys: Surveys to create
        """
        console.print("\n📋 Seeding surveys...", style="bold blue")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Creating surveys...", total=len(surveys.surveys))
            
            for survey in surveys.surveys:
                try:
                    # Create survey via API
                    survey_data = self._prepare_survey_payload(survey)
                    
                    response = self._management_request(
                        "POST",
                        f"environments/{self.environment_id}/surveys",
                        data=survey_data
                    )
                    
                    created = response.json()
                    api_survey_id = created.get("id")
                    
                    # Store mapping
                    self.created_surveys[survey.id] = api_survey_id
                    
                    progress.console.print(
                        f"  ✓ {survey.name} ({len(survey.questions)} questions)",
                        style="green"
                    )
                    
                except requests.exceptions.HTTPError as e:
                    progress.console.print(
                        f"  ✗ {survey.name}: {e}",
                        style="red"
                    )
                    # Try to print the error response body for debugging
                    try:
                        error_detail = e.response.json()
                        progress.console.print(
                            f"     Error details: {error_detail}",
                            style="dim red"
                        )
                    except:
                        pass
                    # Store original ID as fallback
                    self.created_surveys[survey.id] = survey.id
                
                progress.advance(task)
                time.sleep(0.5)
        
        console.print(f"✅ Survey seeding complete", style="green")
    
    def seed_responses(self, responses: ResponseList) -> None:
        """
        Seed survey responses via Client API.
        
        Args:
            responses: Responses to submit
        """
        console.print("\n💬 Seeding responses...", style="bold blue")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "Submitting responses...",
                total=len(responses.responses)
            )
            
            for response in responses.responses:
                try:
                    # Map local survey ID to API survey ID
                    api_survey_id = self.created_surveys.get(
                        response.survey_id,
                        response.survey_id
                    )
                    
                    # Prepare response payload
                    response_data = self._prepare_response_payload(response, api_survey_id)
                    
                    # Submit via Client API
                    self._client_request(
                        "POST",
                        f"{self.environment_id}/displays/{api_survey_id}/responses",
                        data=response_data
                    )
                    
                except requests.exceptions.HTTPError as e:
                    progress.console.print(
                        f"  ⚠ Response failed: {e.response.status_code}",
                        style="yellow"
                    )
                
                progress.advance(task)
                time.sleep(0.3)  # Rate limiting
        
        console.print(f"✅ Response seeding complete", style="green")
    
    def _prepare_survey_payload(self, survey: Survey) -> Dict[str, Any]:
        """
        Convert Survey model to Formbricks API format.
        
        Args:
            survey: Survey to convert
            
        Returns:
            API-compatible payload
        """
        return {
            "name": survey.name,
            "type": survey.type,
            "status": survey.status,
            "questions": [
                self._prepare_question_payload(q)
                for q in survey.questions
            ],
            # Optional cards
            "welcomeCard": survey.welcomeCard or {
                "enabled": False
            },
            "thankYouCard": survey.thankYouCard or {
                "enabled": True,
                "headline": "Thank you!",
                "subheader": "We appreciate your feedback."
            }
        }
    
    def _prepare_question_payload(self, question) -> Dict[str, Any]:
        """
        Convert Question model to API format.
        
        Args:
            question: Question to convert
            
        Returns:
            API-compatible question
        """
        payload = {
            "id": question.id,
            "type": question.type,
            "headline": question.headline,
            "required": question.required,
        }
        
        # Add optional fields if present
        if question.subheader:
            payload["subheader"] = question.subheader
        
        if question.choices:
            payload["choices"] = [
                {"id": c.id, "label": c.label}
                for c in question.choices
            ]
        
        if question.scale:
            payload["scale"] = question.scale
        
        if question.range:
            payload["range"] = question.range
        
        if question.lowerLabel:
            payload["lowerLabel"] = question.lowerLabel
        
        if question.upperLabel:
            payload["upperLabel"] = question.upperLabel
        
        return payload
    
    def _prepare_response_payload(
        self,
        response: Response,
        survey_id: str
    ) -> Dict[str, Any]:
        """
        Convert Response model to API format.
        
        Args:
            response: Response to convert
            survey_id: API survey ID
            
        Returns:
            API-compatible response payload
        """
        # Convert answers to data dict
        data = {}
        for answer in response.answers:
            data[answer.question_id] = answer.value
        
        return {
            "surveyId": survey_id,
            "finished": response.finished,
            "data": data,
        }
    
    def seed_all(self) -> None:
        """
        Seed all data from JSON files.
        
        Reads users, surveys, and responses from data/ directory
        and seeds them in correct dependency order.
        """
        # Validate configuration
        if not self.api_key:
            raise ValueError(
                "FORMBRICKS_API_KEY is required. Please update your .env file."
            )
        
        if not self.environment_id:
            raise ValueError(
                "FORMBRICKS_ENVIRONMENT_ID is required. Please update your .env file."
            )
        
        # Check connection
        console.print("🔍 Checking Formbricks connection...", style="bold blue")
        if not self._check_connection():
            raise ConnectionError(
                f"Cannot connect to Formbricks at {self.base_url}. "
                "Please ensure it's running with 'python main.py formbricks up'"
            )
        console.print("✓ Connected to Formbricks", style="green")
        
        # Load data files
        console.print("\n📂 Loading data files...", style="bold blue")
        users = self._load_json_file("users.json", UserList)
        surveys = self._load_json_file("surveys.json", SurveyList)
        responses = self._load_json_file("responses.json", ResponseList)
        
        console.print(
            f"  ✓ Loaded: {len(users.users)} users, "
            f"{len(surveys.surveys)} surveys, "
            f"{len(responses.responses)} responses",
            style="green"
        )
        
        # Seed in dependency order
        console.print("\n🌱 Starting seeding process...\n", style="bold magenta")
        
        # 1. Seed users (optional - might not be supported)
        try:
            self.seed_users(users)
        except Exception as e:
            console.print(
                f"⚠️  User seeding not fully supported: {e}",
                style="yellow"
            )
        
        # 2. Seed surveys (required)
        self.seed_surveys(surveys)
        
        # 3. Seed responses (requires surveys)
        self.seed_responses(responses)
        
        console.print("\n✨ Seeding complete!", style="bold green")
        console.print(
            f"🌐 View your data at: {self.base_url}",
            style="cyan"
        )
    
    def _load_json_file(self, filename: str, model_class):
        """
        Load and validate JSON file.
        
        Args:
            filename: Name of file in data directory
            model_class: Pydantic model class for validation
            
        Returns:
            Validated model instance
        """
        filepath = config.get_data_file(filename)
        
        if not filepath.exists():
            raise FileNotFoundError(
                f"Data file not found: {filepath}\n"
                "Please run 'python main.py formbricks generate' first."
            )
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return model_class(**data)
