"""
Lisa Voice Agent — Customer Routes
====================================
CRUD for managing agent personas.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)

from customers.store import customer_store
from customers.models import CustomerConfig

logger = logging.getLogger("api.customers")
router = APIRouter(prefix="/api/customers", tags=["customers"])


# -- Models -------------------------------------------------------------------

class CreateCustomerRequest(BaseModel):
    name: str
    agent_name: str = "Lisa"
    agent_type: str = "lisa"
    voice: str = "tara"
    language: str = "en"
    system_prompt: Optional[str] = None
    intro_message: Optional[str] = None
    business_hours: Optional[str] = None
    business_address: Optional[str] = None
    services: List[str] = Field(default_factory=list)


class UpdateCustomerRequest(BaseModel):
    name: Optional[str] = None
    agent_name: Optional[str] = None
    agent_type: Optional[str] = None
    voice: Optional[str] = None
    language: Optional[str] = None
    system_prompt: Optional[str] = None
    intro_message: Optional[str] = None
    business_hours: Optional[str] = None
    business_address: Optional[str] = None
    services: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CustomerResponse(BaseModel):
    id: str
    name: str
    agent_name: str
    agent_type: str
    voice: str
    language: str
    is_active: bool
    created_at: str


class CustomerDetailResponse(CustomerResponse):
    system_prompt: Optional[str]
    intro_message: str
    goodbye_message: str
    business_hours: Optional[str]
    business_address: Optional[str]
    services: List[str]


# -- Endpoints ----------------------------------------------------------------

@router.get("", response_model=List[CustomerResponse])
async def list_customers(active_only: bool = False):
    customers = customer_store.list_active() if active_only else customer_store.list_all()
    return [CustomerResponse(**c.to_dict()) for c in customers]


@router.post("", response_model=CustomerResponse)
async def create_customer(request: CreateCustomerRequest):
    customer = CustomerConfig(
        name=request.name,
        agent_name=request.agent_name,
        agent_type=request.agent_type,
        voice=request.voice,
        language=request.language,
        system_prompt=request.system_prompt or "",
        intro_message=request.intro_message or "Hello {user_name}! I'm {agent_name}. How can I help?",
        business_hours=request.business_hours,
        business_address=request.business_address,
        services=request.services,
    )
    customer = customer_store.create(customer)
    logger.info(f"Created customer: {customer.id} ({customer.name})")
    return CustomerResponse(**customer.to_dict())


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer(customer_id: str):
    customer = customer_store.get(customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    return CustomerDetailResponse(
        **customer.to_dict(),
        system_prompt=customer.system_prompt,
        intro_message=customer.intro_message,
        goodbye_message=customer.goodbye_message,
        business_hours=customer.business_hours,
        business_address=customer.business_address,
        services=customer.services,
    )


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer(customer_id: str, request: UpdateCustomerRequest):
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No updates provided")
    customer = customer_store.update(customer_id, updates)
    if not customer:
        raise HTTPException(404, "Customer not found")
    return CustomerResponse(**customer.to_dict())


@router.delete("/{customer_id}")
async def delete_customer(customer_id: str):
    if customer_id == "demo":
        raise HTTPException(400, "Cannot delete demo customer")
    if not customer_store.delete(customer_id):
        raise HTTPException(404, "Customer not found")
    return {"status": "deleted", "id": customer_id}