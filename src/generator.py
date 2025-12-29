"""
LLM-based data generator for realistic Formbricks survey data.

Uses Ollama to generate believable users, surveys, questions, and responses.
Focuses on strong prompt engineering for consistent, high-quality output.
"""

import json
import random
from typing import Any, Dict, List

import ollama
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import config
from .schemas import (
    Answer,
    Question,
    QuestionChoice,
    QuestionType,
    Response,
    ResponseList,
    Survey,
    SurveyList,
    User,
    UserList,
    UserRole,
)

console = Console()


class DataGenerator:
    """Generates realistic survey data using LLM."""
    
    def __init__(self, model: str = None, host: str = None):
        """
        Initialize generator.
        
        Args:
            model: Ollama model to use (defaults to config)
            host: Ollama host (defaults to config)
        """
        self.model = model or config.OLLAMA_MODEL
        self.host = host or config.OLLAMA_HOST
        
        # Always configure Ollama client with explicit host
        import os
        os.environ["OLLAMA_HOST"] = self.host
        
        # Also create client with explicit host
        self.client = ollama.Client(host=self.host)
    
    def check_ollama_available(self) -> bool:
        """
        Check if Ollama is available and model is pulled.
        
        Returns:
            True if ready, False otherwise
        """
        console.print(f"🔍 Checking Ollama at {self.host}...", style="cyan")
        
        # First try using the ollama python client with explicit client
        try:
            models_resp = self.client.list()
            console.print(f"   📋 Got response from Ollama", style="dim")

            # Handle different response types
            model_names = []
            
            # Check if it's an Ollama ListResponse object with models attribute
            if hasattr(models_resp, 'models'):
                models_list = models_resp.models
                for m in models_list:
                    # Model objects have 'model' attribute, not 'name'
                    if hasattr(m, 'model'):
                        model_names.append(m.model)
                    elif hasattr(m, 'name'):
                        model_names.append(m.name)
                    elif isinstance(m, dict):
                        model_names.append(m.get('model') or m.get('name'))
            # Handle dict with 'models' key
            elif isinstance(models_resp, dict) and "models" in models_resp:
                model_names = [m.get("model") or m.get("name") for m in models_resp.get("models", []) if isinstance(m, dict)]
            # Handle list
            elif isinstance(models_resp, list):
                for item in models_resp:
                    if isinstance(item, str):
                        model_names.append(item)
                    elif hasattr(item, 'model'):
                        model_names.append(item.model)
                    elif hasattr(item, 'name'):
                        model_names.append(item.name)
                    elif isinstance(item, dict):
                        model_names.append(item.get('model') or item.get("name"))

            console.print(f"   📦 Available models: {model_names}", style="dim")

            # Model names might have tags like "llama2:latest"
            available = any(
                (name and (self.model in name or name.startswith(self.model + ":")))
                for name in model_names
            )

            if available:
                console.print(f"   ✓ Found model '{self.model}'", style="green")
                return True
            else:
                console.print(f"   ⚠️  Model '{self.model}' not in available models", style="yellow")

            # Not found via client; try HTTP fallback
        except Exception as e:
            console.print(f"   ⚠️  Ollama client check failed: {e}", style="yellow")

        # HTTP fallback: try known endpoints
        try:
            host = self.host.rstrip("/")
            candidates = ["/api/models", "/api/tags", "/api/list"]
            for path in candidates:
                url = f"{host}{path}"
                try:
                    r = requests.get(url, timeout=3)
                except Exception:
                    continue
                if r.status_code == 200:
                    # Try to parse model names
                    try:
                        data = r.json()
                        names = []
                        if isinstance(data, dict) and "models" in data:
                            names = [m.get("name") for m in data.get("models", []) if isinstance(m, dict)]
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, str):
                                    names.append(item)
                                elif isinstance(item, dict) and "name" in item:
                                    names.append(item.get("name"))

                        for name in names:
                            if name and (self.model in name or name.startswith(self.model + ":")):
                                return True
                    except Exception:
                        # Not JSON or unexpected format
                        pass

        except Exception as e:
            console.print(f"⚠️  Ollama HTTP check error: {e}", style="yellow")

        console.print(
            f"❌ Ollama is not available or model '{self.model}' not found.\n"
            "Make sure Ollama is running (container or local) and the model is pulled.",
            style="red"
        )
        console.print(f"   Expected host: {self.host}", style="yellow")
        console.print(f"   Try: docker ps | grep ollama  or docker logs formbricks-ollama", style="yellow")
        console.print(f"   To pull manually: docker exec formbricks-ollama ollama pull {self.model}", style="yellow")
        return False
    
    def _generate_with_llm(self, prompt: str, system: str = None) -> str:
        """
        Generate text using Ollama.
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            
        Returns:
            Generated text
        """
        messages = []
        
        if system:
            messages.append({"role": "system", "content": system})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": 0.8,  # Some creativity
                "top_p": 0.9,
            }
        )
        
        return response["message"]["content"]
    
    def generate_users(self, num_users: int = 10) -> UserList:
        """
        Generate realistic user data.
        
        Args:
            num_users: Number of users to generate
            
        Returns:
            UserList with generated users
        """
        console.print(f"👥 Generating {num_users} users...", style="bold blue")
        
        system_prompt = """You are a data generator for a SaaS company. Generate realistic employee profiles.
Focus on diversity in names, departments, and roles. Make them feel like real people."""
        
        user_prompt = f"""Generate exactly {num_users} realistic employee profiles in JSON format.

Requirements:
- Mix of managers (2-3) and regular members
- Realistic full names (diverse backgrounds)
- Professional email addresses based on names
- Each person should feel unique and believable

Output ONLY valid JSON matching this exact structure:
{{
  "users": [
    {{
      "name": "Full Name",
      "email": "firstname.lastname@company.com",
      "role": "manager" or "member"
    }}
  ]
}}

Generate {num_users} users now:"""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Thinking...", total=None)
            
            response = self._generate_with_llm(user_prompt, system_prompt)
            
            progress.update(task, completed=True)
        
        # Extract JSON from response
        json_str = self._extract_json(response)
        data = json.loads(json_str)
        
        # Validate and return
        user_list = UserList(**data)
        console.print(f"✅ Generated {len(user_list.users)} users", style="green")
        
        return user_list
    
    def generate_surveys(self, num_surveys: int = 5) -> SurveyList:
        """
        Generate realistic survey data with questions.
        
        Args:
            num_surveys: Number of surveys to generate
            
        Returns:
            SurveyList with generated surveys
        """
        console.print(f"📋 Generating {num_surveys} surveys...", style="bold blue")
        
        system_prompt = """You are a product manager creating customer feedback surveys.
Generate realistic, professional surveys that a SaaS company would actually use.
Mix different question types appropriately."""
        
        user_prompt = f"""Generate exactly {num_surveys} realistic customer feedback surveys in JSON format.

Requirements:
- Each survey should have 3-6 questions
- Mix question types: rating, NPS, multiple choice, open text
- Questions should flow logically
- Professional, clear language
- Realistic choices for multiple choice questions

Question type specifications:
- "rating": Use scale "number", range 5, include lowerlabel and upperLabel
- "nps": Use range 10, lowerLabel "Not likely", upperLabel "Very likely"
- "multipleChoiceSingle": Include 3-5 choices with id and label
- "multipleChoiceMulti": Include 3-5 choices with id and label
- "openText": No extra fields needed

Output ONLY valid JSON matching this exact structure:
{{
  "surveys": [
    {{
      "id": "survey-1",
      "name": "Survey Name",
      "questions": [
        {{
          "id": "q1",
          "type": "rating",
          "headline": "Question text?",
          "required": true,
          "scale": "number",
          "range": 5,
          "lowerLabel": "Not satisfied",
          "upperLabel": "Very satisfied"
        }},
        {{
          "id": "q2",
          "type": "multipleChoiceSingle",
          "headline": "Question text?",
          "required": true,
          "choices": [
            {{"id": "choice-1", "label": "Option 1"}},
            {{"id": "choice-2", "label": "Option 2"}}
          ]
        }},
        {{
          "id": "q3",
          "type": "openText",
          "headline": "Question text?",
          "required": false
        }}
      ],
      "status": "inProgress",
      "type": "link"
    }}
  ]
}}

Generate {num_surveys} diverse surveys now:"""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Thinking...", total=None)
            
            response = self._generate_with_llm(user_prompt, system_prompt)
            
            progress.update(task, completed=True)
        
        # Extract JSON from response
        json_str = self._extract_json(response)
        data = json.loads(json_str)
        
        # Validate and return
        survey_list = SurveyList(**data)
        
        total_questions = sum(len(s.questions) for s in survey_list.surveys)
        console.print(
            f"✅ Generated {len(survey_list.surveys)} surveys with {total_questions} questions",
            style="green"
        )
        
        return survey_list
    
    def generate_responses(
        self,
        surveys: SurveyList,
        users: UserList,
        min_per_survey: int = 3,
        max_per_survey: int = 8,
    ) -> ResponseList:
        """
        Generate realistic survey responses.
        
        Args:
            surveys: Surveys to generate responses for
            users: Users who will respond
            min_per_survey: Minimum responses per survey
            max_per_survey: Maximum responses per survey
            
        Returns:
            ResponseList with generated responses
        """
        console.print("💬 Generating survey responses...", style="bold blue")
        
        all_responses = []
        
        for survey in surveys.surveys:
            num_responses = random.randint(min_per_survey, max_per_survey)
            
            # Sample random users for this survey
            responding_users = random.sample(
                users.users,
                min(num_responses, len(users.users))
            )
            
            console.print(
                f"  📝 {survey.name}: {len(responding_users)} responses",
                style="cyan"
            )
            
            for user in responding_users:
                # Generate answers for each question
                answers = []
                
                for question in survey.questions:
                    answer_value = self._generate_answer_for_question(question)
                    
                    answers.append(
                        Answer(
                            question_id=question.id,
                            value=answer_value
                        )
                    )
                
                all_responses.append(
                    Response(
                        survey_id=survey.id,
                        user_email=user.email,
                        answers=answers,
                        finished=True
                    )
                )
        
        response_list = ResponseList(responses=all_responses)
        console.print(
            f"✅ Generated {len(response_list.responses)} total responses",
            style="green"
        )
        
        return response_list
    
    def _generate_answer_for_question(self, question: Question) -> Any:
        """
        Generate a realistic answer for a specific question type.
        
        Args:
            question: Question to answer
            
        Returns:
            Answer value (type depends on question type)
        """
        if question.type == QuestionType.RATING:
            # Rating: return number in range
            return random.randint(1, question.range or 5)
        
        elif question.type == QuestionType.NPS:
            # NPS: return 0-10
            return random.randint(0, 10)
        
        elif question.type == QuestionType.MULTIPLE_CHOICE_SINGLE:
            # Single choice: return one choice ID
            if question.choices:
                return random.choice(question.choices).id
            return "choice-1"
        
        elif question.type == QuestionType.MULTIPLE_CHOICE_MULTI:
            # Multi choice: return list of choice IDs
            if question.choices:
                num_selected = random.randint(1, min(3, len(question.choices)))
                selected = random.sample(question.choices, num_selected)
                return [c.id for c in selected]
            return ["choice-1"]
        
        elif question.type == QuestionType.OPEN_TEXT:
            # Open text: generate realistic text response
            return self._generate_text_response(question.headline)
        
        else:
            # Default: return "Yes" for other types
            return "Yes"
    
    def _generate_text_response(self, question_text: str) -> str:
        """
        Generate realistic text response to an open-ended question.
        
        Args:
            question_text: The question being answered
            
        Returns:
            Realistic text response
        """
        # Simplified: return believable short responses
        # In production, could use LLM for more variety
        responses = [
            "The product works well overall, but could use some improvements in the UI.",
            "Very satisfied with the service. Support team is responsive and helpful.",
            "It meets our needs, though the learning curve was steep initially.",
            "Great tool! Has saved us a lot of time in our workflow.",
            "Works as expected. Would appreciate more integration options.",
            "Solid product. The recent updates have been particularly useful.",
            "Good value for money. Some features could be more intuitive.",
            "Excellent experience so far. Looking forward to upcoming features.",
            "It's okay. Does the job but nothing exceptional.",
            "Really impressed with the performance and reliability.",
        ]
        
        return random.choice(responses)
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from LLM response that might have extra text.
        
        Args:
            text: Raw LLM response
            
        Returns:
            Clean JSON string
        """
        # Find JSON object/array bounds
        start = text.find("{")
        if start == -1:
            start = text.find("[")
        
        # Find matching closing bracket
        if start != -1:
            # Simple approach: find last } or ]
            end = text.rfind("}")
            if end == -1:
                end = text.rfind("]")
            
            if end != -1:
                return text[start:end + 1]
        
        # If no JSON found, return as-is and let it fail validation
        return text
    
    def generate_all(self) -> None:
        """
        Generate complete dataset and save to files.
        
        Generates users, surveys, and responses, then saves to data/ directory.
        """
        if not self.check_ollama_available():
            raise RuntimeError(
                "Ollama is not available or model not found. "
                f"Please ensure Ollama is running and '{self.model}' is pulled."
            )
        
        config.ensure_data_dir()
        
        console.print("\n🎲 Starting data generation...\n", style="bold magenta")
        
        # Generate users
        users = self.generate_users(config.NUM_USERS)
        self._save_json(users.dict(), "users.json")
        
        console.print()
        
        # Generate surveys
        surveys = self.generate_surveys(config.NUM_SURVEYS)
        self._save_json(surveys.dict(), "surveys.json")
        
        console.print()
        
        # Generate responses
        responses = self.generate_responses(
            surveys,
            users,
            config.MIN_RESPONSES_PER_SURVEY,
            config.MAX_RESPONSES_PER_SURVEY,
        )
        self._save_json(responses.dict(), "responses.json")
        
        console.print("\n✨ Data generation complete!", style="bold green")
        console.print(f"📁 Files saved to: {config.DATA_DIR}", style="cyan")
    
    def _save_json(self, data: Dict[str, Any], filename: str) -> None:
        """
        Save data to JSON file.
        
        Args:
            data: Data to save
            filename: Filename in data directory
        """
        filepath = config.get_data_file(filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        console.print(f"💾 Saved: {filename}", style="dim")
