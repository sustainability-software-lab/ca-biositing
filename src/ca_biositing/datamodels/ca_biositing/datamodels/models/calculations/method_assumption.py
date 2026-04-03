from typing import Optional

from sqlmodel import Field, SQLModel


class MethodAssumption(SQLModel, table=True):
    __tablename__ = "method_assumption"

    id: Optional[int] = Field(default=None, primary_key=True, description="Auto-increment primary key")
    method_id: int = Field(description="Reference to method")
    # foreign_key="method.id" (commented out per repo convention)
    technical_assumption_id: int = Field(description="Reference to technical assumption")
    # foreign_key="technical_assumption.id" (commented out per repo convention)
