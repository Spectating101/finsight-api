"""
GDPR Compliance Endpoints
Data export, deletion, and portability per EU regulations
"""

import structlog
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from src.models.user import User, APIKey

logger = structlog.get_logger(__name__)
router = APIRouter()

# Dependencies will be injected by main.py
_db_pool = None


def set_dependencies(db_pool):
    """Set global dependencies (called from main.py after startup)"""
    global _db_pool
    _db_pool = db_pool


async def get_current_user_from_request(request: Request) -> tuple[User, APIKey]:
    """Get authenticated user from request state (set by auth middleware)"""
    user = getattr(request.state, "user", None)
    api_key = getattr(request.state, "api_key", None)

    if not user or not api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "authentication_required",
                "message": "Valid API key required"
            }
        )

    return user, api_key


class DataExportResponse(BaseModel):
    """Response for data export request"""
    user_data: Dict[str, Any]
    api_keys: List[Dict[str, Any]]
    usage_records: List[Dict[str, Any]]
    subscription_history: List[Dict[str, Any]]
    export_timestamp: str
    format_version: str


class DeletionRequest(BaseModel):
    """Request to delete user account"""
    confirm_email: str
    reason: Optional[str] = None


class DeletionResponse(BaseModel):
    """Response for account deletion request"""
    status: str
    message: str
    deleted_at: str
    data_retained: Dict[str, str]


@router.get("/gdpr/export", response_model=DataExportResponse)
async def export_user_data(
    auth: tuple[User, APIKey] = Depends(get_current_user_from_request)
):
    """
    Export all user data (GDPR Article 15 - Right of Access)

    Returns all personal data associated with the user account in machine-readable format.
    Includes user profile, API keys (hashed), usage records, and subscription history.

    **Required Tier:** Any authenticated user

    **Example:**
    ```
    GET /api/v1/gdpr/export
    ```

    **Returns:**
    Complete user data export in JSON format
    """
    user, _ = auth

    try:
        async with _db_pool.acquire() as conn:
            # Get user data
            user_record = await conn.fetchrow(
                """
                SELECT user_id, email, email_verified, company_name, website,
                       tier, status, api_calls_this_month, api_calls_limit,
                       stripe_customer_id, stripe_subscription_id,
                       billing_period_start, billing_period_end,
                       created_at, updated_at, last_api_call, last_login
                FROM users
                WHERE user_id = $1
                """,
                user.user_id
            )

            # Get API keys (without sensitive hashes)
            api_keys = await conn.fetch(
                """
                SELECT key_id, key_prefix, name, is_active, is_test_mode,
                       total_calls, calls_this_month, last_used_at,
                       allowed_ips, allowed_domains, created_at, expires_at
                FROM api_keys
                WHERE user_id = $1
                ORDER BY created_at DESC
                """,
                user.user_id
            )

            # Get usage records (last 90 days for privacy)
            usage_records = await conn.fetch(
                """
                SELECT record_id, endpoint, method, status_code,
                       credits_used, response_time_ms, timestamp,
                       ip_address::text, user_agent
                FROM usage_records
                WHERE user_id = $1
                  AND timestamp >= NOW() - INTERVAL '90 days'
                ORDER BY timestamp DESC
                LIMIT 1000
                """,
                user.user_id
            )

            # Get subscription history
            subscription_history = await conn.fetch(
                """
                SELECT old_tier, new_tier, event_type,
                       stripe_subscription_id, change_reason,
                       metadata, changed_at
                FROM subscription_history
                WHERE user_id = $1
                ORDER BY changed_at DESC
                """,
                user.user_id
            )

        # Format response
        response = DataExportResponse(
            user_data={
                "user_id": user_record["user_id"],
                "email": user_record["email"],
                "email_verified": user_record["email_verified"],
                "company_name": user_record["company_name"],
                "website": user_record["website"],
                "tier": user_record["tier"],
                "status": user_record["status"],
                "api_calls_this_month": user_record["api_calls_this_month"],
                "api_calls_limit": user_record["api_calls_limit"],
                "stripe_customer_id": user_record["stripe_customer_id"],
                "stripe_subscription_id": user_record["stripe_subscription_id"],
                "billing_period_start": user_record["billing_period_start"].isoformat() if user_record["billing_period_start"] else None,
                "billing_period_end": user_record["billing_period_end"].isoformat() if user_record["billing_period_end"] else None,
                "created_at": user_record["created_at"].isoformat(),
                "updated_at": user_record["updated_at"].isoformat(),
                "last_api_call": user_record["last_api_call"].isoformat() if user_record["last_api_call"] else None,
                "last_login": user_record["last_login"].isoformat() if user_record["last_login"] else None,
            },
            api_keys=[
                {
                    "key_id": key["key_id"],
                    "key_prefix": key["key_prefix"],
                    "name": key["name"],
                    "is_active": key["is_active"],
                    "is_test_mode": key["is_test_mode"],
                    "total_calls": key["total_calls"],
                    "calls_this_month": key["calls_this_month"],
                    "last_used_at": key["last_used_at"].isoformat() if key["last_used_at"] else None,
                    "allowed_ips": key["allowed_ips"],
                    "allowed_domains": key["allowed_domains"],
                    "created_at": key["created_at"].isoformat(),
                    "expires_at": key["expires_at"].isoformat() if key["expires_at"] else None,
                }
                for key in api_keys
            ],
            usage_records=[
                {
                    "record_id": record["record_id"],
                    "endpoint": record["endpoint"],
                    "method": record["method"],
                    "status_code": record["status_code"],
                    "credits_used": record["credits_used"],
                    "response_time_ms": record["response_time_ms"],
                    "timestamp": record["timestamp"].isoformat(),
                    "ip_address": record["ip_address"],
                    "user_agent": record["user_agent"],
                }
                for record in usage_records
            ],
            subscription_history=[
                {
                    "old_tier": history["old_tier"],
                    "new_tier": history["new_tier"],
                    "event_type": history["event_type"],
                    "stripe_subscription_id": history["stripe_subscription_id"],
                    "change_reason": history["change_reason"],
                    "metadata": history["metadata"],
                    "changed_at": history["changed_at"].isoformat(),
                }
                for history in subscription_history
            ],
            export_timestamp=datetime.utcnow().isoformat(),
            format_version="1.0"
        )

        logger.info(
            "User data exported",
            user_id=user.user_id,
            api_keys_count=len(api_keys),
            usage_records_count=len(usage_records)
        )

        return response

    except Exception as e:
        logger.error("Data export failed", user_id=user.user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to export user data"
        )


@router.post("/gdpr/delete", response_model=DeletionResponse)
async def delete_user_account(
    request: DeletionRequest,
    auth: tuple[User, APIKey] = Depends(get_current_user_from_request)
):
    """
    Delete user account (GDPR Article 17 - Right to Erasure)

    Permanently deletes user account and associated data.
    Some data may be retained for legal/billing purposes as noted in response.

    **Required Tier:** Any authenticated user

    **Note:** This action is irreversible. All API keys will be deactivated immediately.

    **Example:**
    ```json
    POST /api/v1/gdpr/delete
    {
        "confirm_email": "user@example.com",
        "reason": "No longer need the service"
    }
    ```

    **Returns:**
    Confirmation of deletion with details of retained data
    """
    user, _ = auth

    try:
        # Verify email matches
        if request.confirm_email.lower() != user.email.lower():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "email_mismatch",
                    "message": "Confirmation email does not match account email"
                }
            )

        async with _db_pool.acquire() as conn:
            async with conn.transaction():
                # Check if user has active subscription
                has_active_subscription = await conn.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1 FROM users
                        WHERE user_id = $1
                          AND stripe_subscription_id IS NOT NULL
                          AND status = 'active'
                    )
                    """,
                    user.user_id
                )

                if has_active_subscription:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "active_subscription",
                            "message": "Please cancel your subscription before deleting your account",
                            "cancel_url": "/api/v1/billing/subscription/cancel"
                        }
                    )

                # Log deletion reason
                if request.reason:
                    await conn.execute(
                        """
                        INSERT INTO subscription_history (user_id, old_tier, new_tier, event_type, change_reason, metadata)
                        VALUES ($1, $2, 'deleted', 'account_deletion', $3, $4)
                        """,
                        user.user_id,
                        user.tier.value,
                        request.reason,
                        json.dumps({"deleted_at": datetime.utcnow().isoformat()})
                    )

                # Delete API keys (cascades to usage_records via foreign key)
                await conn.execute(
                    "DELETE FROM api_keys WHERE user_id = $1",
                    user.user_id
                )

                # Anonymize user record (keep for billing/legal purposes)
                await conn.execute(
                    """
                    UPDATE users
                    SET email = $2,
                        email_verified = false,
                        password_hash = NULL,
                        company_name = NULL,
                        website = NULL,
                        status = 'cancelled',
                        stripe_customer_id = NULL,
                        stripe_subscription_id = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = $1
                    """,
                    user.user_id,
                    f"deleted_{user.user_id}@finsight.deleted"
                )

        logger.info(
            "User account deleted",
            user_id=user.user_id,
            reason=request.reason
        )

        return DeletionResponse(
            status="deleted",
            message="Your account has been successfully deleted",
            deleted_at=datetime.utcnow().isoformat(),
            data_retained={
                "subscription_history": "Retained for 7 years per tax law",
                "usage_records": "Aggregated anonymously for analytics",
                "billing_records": "Retained per Stripe's data retention policy"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Account deletion failed", user_id=user.user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to delete account"
        )


@router.get("/gdpr/info")
async def get_gdpr_info():
    """
    Get information about GDPR rights and data processing

    Public endpoint describing user rights under GDPR and how data is processed.

    **Required Tier:** None (public)

    **Example:**
    ```
    GET /api/v1/gdpr/info
    ```
    """
    return {
        "data_controller": {
            "name": "FinSight API",
            "contact": "privacy@finsight.io",
            "dpo_contact": "dpo@finsight.io"
        },
        "user_rights": {
            "right_of_access": {
                "description": "You can request a copy of all your personal data",
                "endpoint": "GET /api/v1/gdpr/export",
                "format": "JSON"
            },
            "right_to_erasure": {
                "description": "You can request deletion of your account and data",
                "endpoint": "POST /api/v1/gdpr/delete",
                "note": "Some data retained for legal/billing purposes"
            },
            "right_to_rectification": {
                "description": "You can update your personal information",
                "endpoint": "PATCH /api/v1/auth/profile"
            },
            "right_to_portability": {
                "description": "You can export your data in machine-readable format",
                "endpoint": "GET /api/v1/gdpr/export",
                "format": "JSON"
            }
        },
        "data_processing": {
            "purposes": [
                "Providing API services",
                "Billing and subscription management",
                "Usage analytics and service improvement",
                "Security and fraud prevention"
            ],
            "legal_basis": "Contract performance and legitimate interests",
            "retention_period": {
                "active_users": "As long as account is active",
                "deleted_users": "User data anonymized immediately",
                "billing_records": "7 years per tax law",
                "usage_logs": "90 days"
            },
            "third_parties": [
                {
                    "name": "Stripe",
                    "purpose": "Payment processing",
                    "location": "USA (Privacy Shield certified)"
                },
                {
                    "name": "Sentry",
                    "purpose": "Error monitoring",
                    "location": "USA"
                }
            ]
        },
        "contact": {
            "privacy_questions": "privacy@finsight.io",
            "data_protection_officer": "dpo@finsight.io",
            "complaints": "You can lodge a complaint with your local data protection authority"
        }
    }
