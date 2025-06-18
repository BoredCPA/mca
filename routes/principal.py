# app/routes/principal.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.schemas.principal import (
    Principal, PrincipalCreate, PrincipalUpdate, PrincipalListResponse
)
from app.crud import principal as principal_crud
from app.crud.principal import (
    DuplicateSSNError, OwnershipExceededError, PrincipalCRUDError
)
from app.database import get_db
from typing import List, Optional
import logging

router = APIRouter(
    prefix="/api/v1",
    tags=["principals"]
)

logger = logging.getLogger(__name__)


@router.post("/principals/", response_model=Principal, status_code=status.HTTP_201_CREATED)
def create_principal(
        principal: PrincipalCreate,
        db: Session = Depends(get_db)
):
    """
    Create a new principal for a merchant

    - **merchant_id**: ID of the merchant this principal belongs to
    - **ownership_percentage**: Must not cause total to exceed 100%
    - **ssn**: Must be unique within the merchant
    - **is_primary_contact**: Only one principal can be primary per merchant
    """
    try:
        return principal_crud.create_principal(db, principal)
    except DuplicateSSNError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except OwnershipExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PrincipalCRUDError as e:
        logger.error(f"Error creating principal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/principals/{principal_id}", response_model=Principal)
def read_principal(
        principal_id: int,
        db: Session = Depends(get_db)
):
    """Get a specific principal by ID"""
    try:
        principal = principal_crud.get_principal(db, principal_id=principal_id)
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Principal not found"
            )
        return principal
    except PrincipalCRUDError as e:
        logger.error(f"Error fetching principal {principal_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch principal"
        )


@router.get("/merchants/{merchant_id}/principals/", response_model=PrincipalListResponse)
def read_merchant_principals(
        merchant_id: int,
        only_guarantors: bool = Query(False, description="Filter only guarantors"),
        db: Session = Depends(get_db)
):
    """Get all principals for a specific merchant"""
    try:
        principals = principal_crud.get_principals_by_merchant(
            db,
            merchant_id=merchant_id,
            only_guarantors=only_guarantors
        )
        return PrincipalListResponse(
            principals=principals,
            total=len(principals),
            merchant_id=merchant_id
        )
    except PrincipalCRUDError as e:
        logger.error(f"Error fetching principals for merchant {merchant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch principals"
        )


@router.get("/merchants/{merchant_id}/principals/ownership-summary")
def read_merchant_ownership_summary(
        merchant_id: int,
        db: Session = Depends(get_db)
):
    """Get ownership summary for a merchant"""
    try:
        return principal_crud.get_merchant_ownership_summary(db, merchant_id)
    except PrincipalCRUDError as e:
        logger.error(f"Error getting ownership summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ownership summary"
        )


@router.get("/principals/search/by-ssn", response_model=List[Principal])
def search_principals_by_ssn(
        ssn: str = Query(..., regex="^\\d{3}-\\d{2}-\\d{4}$"),
        db: Session = Depends(get_db)
):
    """
    Search for principals by SSN across all merchants

    Note: Returns partial SSN in response for security
    """
    try:
        principals = principal_crud.get_principals_by_ssn(db, ssn)
        # Mask SSN in response for security
        for principal in principals:
            if principal.ssn:
                principal.ssn = f"{principal.ssn[:3]}-XX-XXXX"
        return principals
    except PrincipalCRUDError as e:
        logger.error(f"Error searching principals by SSN: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search principals"
        )


# @router.put("/principals/{principal_id}", response_model=Principal)
# def update_principal(
#         principal_id: int,
#         principal_update: PrincipalUpdate,
#         db: Session = Depends(get_db)
# ):
#     """Update a principal"""
#     try:
#         principal = principal_crud.update_principal(
#             db,
#             principal_id=principal_id,
#             principal_update=principal_update
#         )
#         if principal is None:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Principal not found"
#             )
#         return principal
#     except