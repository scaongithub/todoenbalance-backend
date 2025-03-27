"""Webhook endpoints for payment providers and external services."""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db
from app.config import settings
from app.models.payment import Payment, PaymentProvider, PaymentStatus
from app.services.appointment_service import AppointmentService
from app.services.email_service import EmailService
from app.services.payment.paypal_service import PayPalPaymentService
from app.services.payment.stripe_service import StripePaymentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(
        request: Request,
        stripe_signature: str = Header(None),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Webhook endpoint for Stripe events.
    This endpoint processes payment notifications from Stripe.
    """
    # Read request body
    payload = await request.body()
    payload_json = json.loads(payload)

    try:
        # Initialize Stripe payment service
        payment_service = StripePaymentService()

        # Process webhook
        webhook_data = await payment_service.handle_webhook(
            payload_json,
            stripe_signature,
        )

        # Find associated payment
        provider_payment_id = webhook_data.get("provider_payment_id")

        if not provider_payment_id:
            return {"status": "error", "message": "No payment ID in webhook data"}

        stmt = select(Payment).where(
            Payment.provider_payment_id == provider_payment_id
        )
        result = await db.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            logger.warning(f"Payment not found for Stripe payment ID: {provider_payment_id}")
            return {"status": "success", "message": "No matching payment found"}

        # Update payment with webhook data
        payment = await payment_service.update_payment_model(payment, webhook_data)

        # Save changes
        db.add(payment)
        await db.commit()

        # If payment status changed to completed or failed, update appointment
        if payment.status in [PaymentStatus.COMPLETED, PaymentStatus.FAILED]:
            appointment_service = AppointmentService(db, EmailService())
            await appointment_service.update_appointment_payment_status(
                payment.appointment_id,
                payment.id,
                payment.status,
                background_tasks,
            )

        return {"status": "success", "message": "Webhook processed successfully"}

    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {str(e)}")
        # Return 200 to acknowledge receipt (per Stripe recommendations)
        return {"status": "error", "message": str(e)}


@router.post("/paypal")
async def paypal_webhook(
        request: Request,
        paypal_transmission_id: str = Header(None, alias="paypal-transmission-id"),
        paypal_transmission_time: str = Header(None, alias="paypal-transmission-time"),
        paypal_transmission_sig: str = Header(None, alias="paypal-transmission-sig"),
        paypal_cert_url: str = Header(None, alias="paypal-cert-url"),
        paypal_auth_algo: str = Header(None, alias="paypal-auth-algo"),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Webhook endpoint for PayPal events.
    This endpoint processes payment notifications from PayPal.
    """
    # Read request body
    payload = await request.body()
    payload_json = json.loads(payload)

    try:
        # Initialize PayPal payment service
        payment_service = PayPalPaymentService()

        # Combine headers for verification
        webhook_signature = {
            "transmission_id": paypal_transmission_id,
            "transmission_time": paypal_transmission_time,
            "transmission_sig": paypal_transmission_sig,
            "cert_url": paypal_cert_url,
            "auth_algo": paypal_auth_algo,
        }

        # Process webhook
        webhook_data = await payment_service.handle_webhook(
            payload_json,
            webhook_signature,
        )

        # Find associated payment using custom ID or transaction ID
        metadata = webhook_data.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        payment_id = metadata.get("payment_id")
        provider_transaction_id = webhook_data.get("provider_transaction_id")
        provider_payment_id = webhook_data.get("provider_payment_id")

        payment = None

        # Try to find by payment ID in metadata
        if payment_id:
            stmt = select(Payment).where(Payment.id == int(payment_id))
            result = await db.execute(stmt)
            payment = result.scalar_one_or_none()

        # If not found, try by provider payment ID
        if not payment and provider_payment_id:
            stmt = select(Payment).where(
                Payment.provider_payment_id == provider_payment_id
            )
            result = await db.execute(stmt)
            payment = result.scalar_one_or_none()

        # If still not found, try by transaction ID
        if not payment and provider_transaction_id:
            stmt = select(Payment).where(
                Payment.provider_transaction_id == provider_transaction_id
            )
            result = await db.execute(stmt)
            payment = result.scalar_one_or_none()

        if not payment:
            logger.warning(f"Payment not found for PayPal webhook: {provider_payment_id}")
            return {"status": "success", "message": "No matching payment found"}

        # Update payment with webhook data
        payment = await payment_service.update_payment_model(payment, webhook_data)

        # Save changes
        db.add(payment)
        await db.commit()

        # If payment status changed to completed or failed, update appointment
        if payment.status in [PaymentStatus.COMPLETED, PaymentStatus.FAILED]:
            appointment_service = AppointmentService(db, EmailService())
            await appointment_service.update_appointment_payment_status(
                payment.appointment_id,
                payment.id,
                payment.status,
                background_tasks,
            )

        return {"status": "success", "message": "Webhook processed successfully"}

    except Exception as e:
        logger.error(f"Error processing PayPal webhook: {str(e)}")
        # Return 200 to acknowledge receipt (per PayPal recommendations)
        return {"status": "error", "message": str(e)}


@router.post("/sendgrid")
async def sendgrid_webhook(
        request: Request,
        db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Webhook endpoint for SendGrid email events.
    This endpoint processes email delivery notifications from SendGrid.
    """
    # Read request body
    payload = await request.body()
    events = json.loads(payload)

    # Process each event
    processed_count = 0

    for event in events:
        try:
            event_type = event.get("event")
            message_id = event.get("sg_message_id")

            if not message_id:
                continue

            # Find the email log
            from app.models.email_log import EmailLog, EmailStatus

            stmt = select(EmailLog).where(
                EmailLog.provider_message_id == message_id
            )
            result = await db.execute(stmt)
            email_log = result.scalar_one_or_none()

            if not email_log:
                continue

            # Update email log status based on event type
            if event_type == "delivered":
                email_log.status = EmailStatus.DELIVERED
                email_log.delivered_at = datetime.utcnow()
            elif event_type == "open":
                email_log.status = EmailStatus.OPENED
                email_log.opened_at = datetime.utcnow()
            elif event_type == "click":
                email_log.status = EmailStatus.CLICKED
                email_log.clicked_at = datetime.utcnow()
            elif event_type in ["bounce", "dropped", "deferred", "blocked"]:
                email_log.status = EmailStatus.FAILED
                email_log.error_message = event.get("reason", event_type)

            db.add(email_log)
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing SendGrid event: {str(e)}")

    # Commit changes
    if processed_count > 0:
        await db.commit()

    return {"status": "success", "processed": processed_count}