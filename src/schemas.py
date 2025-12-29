"""
Data schemas for Formbricks seeder.

Defines Pydantic models for users, surveys, questions, and responses.
These models ensure type safety and provide validation for generated data.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User role in Formbricks."""
    OWNER = "owner"
    MANAGER = "manager"
    MEMBER = "member"


class QuestionType(str, Enum):
    """Supported Formbricks question types."""
    MULTIPLE_CHOICE_SINGLE = "multipleChoiceSingle"
    MULTIPLE_CHOICE_MULTI = "multipleChoiceMulti"
    OPEN_TEXT = "openText"
    RATING = "rating"
    NPS = "nps"
    CTA = "cta"
    CONSENT = "consent"


# ============================================================================
# User Models
# ============================================================================

class User(BaseModel):
    """Represents a Formbricks user."""
    name: str = Field(..., description="Full name of the user")
    email: EmailStr = Field(..., description="Email address (must be unique)")
    role: UserRole = Field(default=UserRole.MEMBER, description="User role")
    
    class Config:
        use_enum_values = True


class UserList(BaseModel):
    """Collection of users."""
    users: List[User]


# ============================================================================
# Survey Models
# ============================================================================

class QuestionChoice(BaseModel):
    """Choice option for multiple choice questions."""
    id: str = Field(..., description="Unique identifier for this choice")
    label: str = Field(..., description="Display text for this choice")


class Question(BaseModel):
    """Represents a survey question."""
    id: str = Field(..., description="Unique identifier for this question")
    type: QuestionType = Field(..., description="Question type")
    headline: str = Field(..., description="Question text/headline")
    subheader: Optional[str] = Field(None, description="Optional subheader text")
    required: bool = Field(default=True, description="Whether response is required")
    
    # Multiple choice specific
    choices: Optional[List[QuestionChoice]] = Field(
        None, 
        description="Choices for multiple choice questions"
    )
    
    # Rating specific
    scale: Optional[str] = Field(
        None,
        description="Rating scale (e.g., 'number' for 1-5, 'smiley' for emoji)"
    )
    range: Optional[int] = Field(
        None,
        description="Rating range (e.g., 5 for 1-5 scale, 10 for NPS)"
    )
    
    # NPS specific
    lowerLabel: Optional[str] = Field(None, description="Label for lower end of scale")
    upperLabel: Optional[str] = Field(None, description="Label for upper end of scale")
    
    class Config:
        use_enum_values = True


class Survey(BaseModel):
    """Represents a complete survey."""
    id: str = Field(..., description="Unique identifier for this survey")
    name: str = Field(..., description="Internal survey name")
    questions: List[Question] = Field(..., description="List of questions")
    status: str = Field(default="draft", description="Survey status (draft, inProgress, completed)")
    type: str = Field(default="link", description="Survey type (link, web, app)")
    
    # Optional metadata
    welcomeCard: Optional[Dict[str, Any]] = Field(
        None,
        description="Welcome screen configuration"
    )
    thankYouCard: Optional[Dict[str, Any]] = Field(
        None,
        description="Thank you screen configuration"
    )


class SurveyList(BaseModel):
    """Collection of surveys."""
    surveys: List[Survey]


# ============================================================================
# Response Models
# ============================================================================

class Answer(BaseModel):
    """Answer to a specific question."""
    question_id: str = Field(..., description="ID of the question being answered")
    
    # Answer can be various types depending on question
    value: Union[str, int, List[str]] = Field(
        ..., 
        description="Answer value (string for text, int for rating, list for multi-choice)"
    )


class Response(BaseModel):
    """Survey response from a user."""
    survey_id: str = Field(..., description="ID of the survey being responded to")
    user_email: str = Field(..., description="Email of responding user")
    answers: List[Answer] = Field(..., description="List of answers")
    finished: bool = Field(default=True, description="Whether response is complete")


class ResponseList(BaseModel):
    """Collection of responses."""
    responses: List[Response]


# ============================================================================
# Generation Request Models (for LLM)
# ============================================================================

class GenerationRequest(BaseModel):
    """Request for LLM to generate survey data."""
    num_users: int = Field(default=10, ge=1, le=100)
    num_surveys: int = Field(default=5, ge=1, le=20)
    min_responses_per_survey: int = Field(default=3, ge=1)
    max_responses_per_survey: int = Field(default=8, ge=1)
    
    def validate_response_range(self) -> None:
        """Ensure min <= max for responses."""
        if self.min_responses_per_survey > self.max_responses_per_survey:
            raise ValueError(
                "min_responses_per_survey must be <= max_responses_per_survey"
            )


# ============================================================================
# API Response Models (for Formbricks API)
# ============================================================================

class FormbricksUser(BaseModel):
    """User as returned by Formbricks API."""
    id: str
    email: str
    name: str
    role: str


class FormbricksSurvey(BaseModel):
    """Survey as returned by Formbricks API."""
    id: str
    name: str
    status: str
    questions: List[Dict[str, Any]]


class FormbricksResponse(BaseModel):
    """Response as returned by Formbricks API."""
    id: str
    surveyId: str
    data: Dict[str, Any]
    finished: bool
