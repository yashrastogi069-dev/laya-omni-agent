"""
Base Contract Model
===================
Provides shared Pydantic configuration for all canonical LAYA contracts:
- Strict rejection of unknown/extra fields (extra="forbid")
- Automatic validation on assignment (validate_assignment=True)
"""

from pydantic import BaseModel, ConfigDict


class BaseContractModel(BaseModel):
    """Base class for all strongly typed LAYA contract models."""
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
    )
