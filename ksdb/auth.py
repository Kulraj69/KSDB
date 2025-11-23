"""
Authentication middleware for KSdb Cloud
"""
import os
import secrets
import hashlib
from typing import Optional, Dict
from fastapi import HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy import create_engine, Column, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

Base = declarative_base()

class APIKey(Base):
    __tablename__ = "api_keys"
    
    key = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)  # User-friendly name
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class AuthManager:
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///auth.db")
        self.engine = create_engine(self.db_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
    
    def generate_api_key(self, tenant_id: str, name: str = None) -> str:
        """Generate a new API key for a tenant"""
        # Format: ks_live_<32_random_chars>
        random_part = secrets.token_urlsafe(24)
        api_key = f"ks_live_{random_part}"
        
        session = self.SessionLocal()
        try:
            key_obj = APIKey(
                key=api_key,
                tenant_id=tenant_id,
                name=name
            )
            session.add(key_obj)
            session.commit()
            return api_key
        finally:
            session.close()
    
    def validate_api_key(self, api_key: str) -> Optional[str]:
        """Validate API key and return tenant_id"""
        session = self.SessionLocal()
        try:
            key_obj = session.query(APIKey).filter(
                APIKey.key == api_key,
                APIKey.is_active == True
            ).first()
            
            if key_obj:
                # Update last used
                key_obj.last_used_at = datetime.utcnow()
                session.commit()
                return key_obj.tenant_id
            return None
        finally:
            session.close()
    
    def revoke_api_key(self, api_key: str):
        """Revoke an API key"""
        session = self.SessionLocal()
        try:
            key_obj = session.query(APIKey).filter(APIKey.key == api_key).first()
            if key_obj:
                key_obj.is_active = False
                session.commit()
        finally:
            session.close()
    
    def list_keys(self, tenant_id: str) -> list:
        """List all API keys for a tenant"""
        session = self.SessionLocal()
        try:
            keys = session.query(APIKey).filter(
                APIKey.tenant_id == tenant_id
            ).all()
            return [{
                "key": k.key,
                "name": k.name,
                "created_at": k.created_at,
                "last_used_at": k.last_used_at,
                "is_active": k.is_active
            } for k in keys]
        finally:
            session.close()

# Global auth manager
auth_manager = AuthManager()

async def get_current_tenant(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency to get current tenant from API key
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Please provide X-API-Key header."
        )
    
    tenant_id = auth_manager.validate_api_key(api_key)
    
    if not tenant_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or revoked API key"
        )
    
    return tenant_id
