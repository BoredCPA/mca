# app/models/__init__.py
from app.models.merchant import Merchant
from app.models.offer import Offer
from app.models.principal import Principal

__all__ = ["Merchant", "Offer", "Principal"]