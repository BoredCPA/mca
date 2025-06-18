# app/routes/merchant.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.schemas.merchant import (
    Merchant, MerchantCreate, MerchantUpdate, MerchantListResponse
)
from app.crud import merchant as merchant_crud
from app.crud.merchant import DuplicateFEINError, MerchantCRUDError
from app.database import get_db
from typing import List, Optional
import logging

router = APIRouter(
    prefix="/api/v1",
    tags=["merchants"]
)

logger = logging.getLogger(__name__)


@router.post("/merchants/", response_model=Merchant, status_code=status.HTTP_201_CREATED)
def create_merchant(
        merchant: MerchantCreate,
        db: Session = Depends(get_db)
):
    """
    Create a new merchant with full validation
    """
    try:
        return merchant_crud.create_merchant(db, merchant)
    except DuplicateFEINError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except MerchantCRUDError as e:
        logger.error(f"Error creating merchant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating merchant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/merchants/", response_model=MerchantListResponse)
def read_merchants(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
        status: Optional[str] = Query(None, regex="^(lead|prospect|applicant|approved|declined|funded|closed)$"),
        search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search term"),
        sort_by: str = Query("created_at", regex="^(company_name|status|created_at|updated_at)$"),
        sort_order: str = Query("desc", regex="^(asc|desc)$"),
        db: Session = Depends(get_db)
):
    """
    Get merchants with pagination, filtering, and sorting
    """
    try:
        merchants = merchant_crud.get_merchants(
            db,
            skip=skip,
            limit=limit,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )

        total = merchant_crud.count_merchants(db, status=status, search=search)

        return MerchantListResponse(
            merchants=merchants,
            total=total,
            page=skip // limit + 1,
            per_page=limit
        )
    except MerchantCRUDError as e:
        logger.error(f"Error fetching merchants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch merchants"
        )


@router.get("/merchants/{merchant_id}", response_model=Merchant)
def read_merchant(
        merchant_id: int,
        db: Session = Depends(get_db)
):
    """
    Get a specific merchant by ID
    """
    try:
        merchant = merchant_crud.get_merchant(db, merchant_id=merchant_id)
        if merchant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )
        return merchant
    except MerchantCRUDError as e:
        logger.error(f"Error fetching merchant {merchant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch merchant"
        )


@router.get("/merchants/fein/{fein}", response_model=Merchant)
def read_merchant_by_fein(
        fein: str,
        db: Session = Depends(get_db)
):
    """
    Get a merchant by FEIN
    """
    try:
        merchant = merchant_crud.get_merchant_by_fein(db, fein=fein)
        if merchant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )
        return merchant
    except MerchantCRUDError as e:
        logger.error(f"Error fetching merchant by FEIN {fein}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch merchant"
        )


@router.put("/merchants/{merchant_id}", response_model=Merchant)
def update_merchant(
        merchant_id: int,
        merchant_update: MerchantUpdate,
        db: Session = Depends(get_db)
):
    """
    Update a merchant
    """
    try:
        merchant = merchant_crud.update_merchant(
            db,
            merchant_id=merchant_id,
            merchant_update=merchant_update
        )
        if merchant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )
        return merchant
    except DuplicateFEINError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except MerchantCRUDError as e:
        logger.error(f"Error updating merchant {merchant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/merchants/{merchant_id}/status", response_model=Merchant)
def update_merchant_status(
        merchant_id: int,
        status: str = Query(..., regex="^(lead|prospect|applicant|approved|declined|funded|closed)$"),
        db: Session = Depends(get_db)
):
    """
    Update only the merchant status
    """
    try:
        merchant_update = MerchantUpdate(status=status)
        merchant = merchant_crud.update_merchant(
            db,
            merchant_id=merchant_id,
            merchant_update=merchant_update
        )
        if merchant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )
        return merchant
    except MerchantCRUDError as e:
        logger.error(f"Error updating merchant status {merchant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/merchants/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_merchant(
        merchant_id: int,
        db: Session = Depends(get_db)
):
    """
    Delete a merchant (soft delete)
    """
    try:
        success = merchant_crud.delete_merchant(db, merchant_id=merchant_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merchant not found"
            )
    except MerchantCRUDError as e:
        logger.error(f"Error deleting merchant {merchant_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/merchants/stats/summary")
def get_merchant_statistics(db: Session = Depends(get_db)):
    """
    Get merchant statistics summary
    """
    try:
        stats = merchant_crud.get_merchant_stats(db)
        return stats
    except MerchantCRUDError as e:
        logger.error(f"Error getting merchant stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get merchant statistics"
        )