"""Pydantic schemas for authentication and authorization."""

from pydantic import BaseModel, Field


class LoginInput(BaseModel):
    """Administrator login request payload."""

    email: str = Field(min_length=1, description="Administrator login")
    password: str = Field(min_length=1, description="Administrator password")


class AdminSession(BaseModel):
    """The signed-in administrator.

    The access token itself never appears in a response body: it travels only
    in the httpOnly session cookie, out of reach of page scripts.
    """

    email: str = Field(description="Login of the signed-in administrator")
