"""Payment endpoints."""

from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_pagination_params
from app.core.jwt import get_current_admin, get_current_user
from app.models.appointment import Appointment
from app.models.payment import Payment, PaymentProvider, PaymentStatus
from app.models.user import User
from app.schemas.payment import (
    PaymentCreate,
    PaymentIntentCreate,
    PaymentIntentResponse,
    PaymentOut,
    PaymentUpdate,
)
from app.services.appointment_service import AppointmentService
from app.services.email_service import EmailService
from app.services.payment.paypal_service import PayPalPaymentService
from app.services.payment.stripe_service import StripePaymentService

router = APIRouter()


@router.get("", response_model=List[PaymentOut])
async def read_payments(
        status: Optional[PaymentStatus] = None,
        appointment_id: Optional[int] = None,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
        skip_limit: tuple = Depends(get_pagination_params),
) -> Any:
    """
    Get list of payments.
    Only accessible by admins.
    """
    skip, limit = skip_limit

    # Build query with filters
    query = select(Payment)

    if status:
        query = query.where(Payment.status == status)

    if appointment_id:
        query = query.where(Payment.appointment_id == appointment_id)

    # Apply pagination and execute
    query = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    payments = result.scalars().all()

    return payments


@router.get("/me", response_model=List[PaymentOut])
async def read_my_payments(
        status: Optional[PaymentStatus] = None,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
        skip_limit: tuple = Depends(get_pagination_params),
) -> Any:
    """
    Get current user's payments.
    """
    skip, limit = skip_limit

    # Build query
    query = select(Payment).where(Payment.user_id == current_user.id)

    if status:
        query = query.where(Payment.status == status)

    # Apply pagination and execute
    query = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    payments = result.scalars().all()

    return payments


@router.post("/intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
        intent_in: PaymentIntentCreate,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a payment intent/order.
    This is the first step in the payment process.
    """
    # Get appointment
    appointment_stmt = select(Appointment).where(Appointment.id == intent_in.appointment_id)
    appointment_result = await db.execute(appointment_stmt)
    appointment = appointment_result.scalar_one_or_none()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {intent_in.appointment_id} not found",
        )

    # Verify that the appointment belongs to the current user
    if appointment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to pay for this appointment",
        )

    # Verify that the appointment is not already paid
    if appointment.is_paid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This appointment has already been paid for",
        )

    # Determine payment amount based on appointment duration
    amount = 50.0  # Default for 30-minute sessions
    if appointment.duration == 60:
        amount = 100.0

    # Create payment record in database
    payment = Payment(
        user_id=current_user.id,
        appointment_id=appointment.id,
        amount=amount,
        currency="EUR",
        provider=intent_in.provider,
        status=PaymentStatus.PENDING,
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    # Create payment intent with the provider
    try:
        # Initialize appropriate payment service
        if intent_in.provider == PaymentProvider.STRIPE:
            payment_service = StripePaymentService()
        elif intent_in.provider == PaymentProvider.PAYPAL:
            payment_service = PayPalPaymentService()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported payment provider: {intent_in.provider}",
            )

        # Create payment with provider
        metadata = {
            "appointment_id": str(appointment.id),
            "user_id": str(current_user.id),
            "payment_id": str(payment.id),
        }

        intent_result = await payment_service.create_payment(
            amount=amount,
            currency="eur",
            description=f"Appointment #{appointment.id} - {appointment.duration} min consultation",
            customer_email=current_user.email,
            customer_name=current_user.full_name,
            metadata=metadata,
        )

        # Update payment with provider details
        payment.provider_payment_id = intent_result.get("provider_payment_id")
        db.add(payment)
        await db.commit()

        # Return intent details
        response = PaymentIntentResponse(
            payment_id=payment.id,
            provider=intent_in.provider,
            provider_payment_id=intent_result.get("provider_payment_id"),
            amount=amount,
            currency="EUR",
            status=intent_result.get("status", "pending"),
        )

        # Add provider-specific fields
        if intent_in.provider == PaymentProvider.STRIPE:
            response.client_secret = intent_result.get("client_secret")
        elif intent_in.provider == PaymentProvider.PAYPAL:
            response.payment_url = intent_result.get("approval_url")

        return response

    except Exception as e:
        # If anything fails, update payment status and re-raise
        payment.status = PaymentStatus.FAILED
        payment.error_message = str(e)
        db.add(payment)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {str(e)}",
        )


@router.get("/{payment_id}", response_model=PaymentOut)
async def read_payment(
        payment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a payment by ID.
    Regular users can only access their own payments.
    """
    # Get payment
    stmt = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found",
        )

    # Check access permissions
    is_admin = hasattr(current_user, "is_superuser")
    if not is_admin and payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return payment


@router.post("/{payment_id}/confirm", response_model=PaymentOut)
async def confirm_payment(
        payment_id: int,
        provider_payment_id: Optional[str] = None,
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Confirm a payment.
    This is typically called after the client has completed the payment process.
    """
    # Get payment
    stmt = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found",
        )

    # Check access permissions
    is_admin = hasattr(current_user, "is_superuser")
    if not is_admin and payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Initialize appropriate payment service
    if payment.provider == PaymentProvider.STRIPE:
        payment_service = StripePaymentService()
    elif payment.provider == PaymentProvider.PAYPAL:
        payment_service = PayPalPaymentService()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported payment provider: {payment.provider}",
        )

    try:
        # Use provided payment ID or the one from the database
        provider_id = provider_payment_id or payment.provider_payment_id

        if not provider_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No provider payment ID available",
            )

        # Confirm payment with provider
        confirm_result = await payment_service.confirm_payment(provider_id)

        # Update payment status
        payment = await payment_service.update_payment_model(payment, confirm_result)

        # Update appointment status if payment is completed
        if payment.status == PaymentStatus.COMPLETED:
            appointment_service = AppointmentService(db, EmailService())
            await appointment_service.update_appointment_payment_status(
                payment.appointment_id,
                payment.id,
                payment.status,
                background_tasks,
            )

        # Save changes
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        return payment

    except Exception as e:
        # If anything fails, update payment status and re-raise
        payment.status = PaymentStatus.FAILED
        payment.error_message = str(e)
        db.add(payment)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm payment: {str(e)}",
        )


@router.post("/{payment_id}/cancel", response_model=PaymentOut)
async def cancel_payment(
        payment_id: int,
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Cancel a payment.
    This can only be done for pending payments.
    """
    # Get payment
    stmt = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found",
        )

    # Check access permissions
    is_admin = hasattr(current_user, "is_superuser")
    if not is_admin and payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Check if payment can be cancelled
    if payment.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel payment with status {payment.status}",
        )

    # Initialize appropriate payment service
    if payment.provider == PaymentProvider.STRIPE:
        payment_service = StripePaymentService()
    elif payment.provider == PaymentProvider.PAYPAL:
        payment_service = PayPalPaymentService()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported payment provider: {payment.provider}",
        )

    try:
        # Cancel payment with provider
        if payment.provider_payment_id:
            cancel_result = await payment_service.cancel_payment(payment.provider_payment_id)
            payment = await payment_service.update_payment_model(payment, cancel_result)
        else:
            # If there's no provider ID, just mark as cancelled locally
            payment.status = PaymentStatus.CANCELLED

        # Save changes
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        # Update appointment status
        appointment_service = AppointmentService(db, EmailService())
        await appointment_service.update_appointment_payment_status(
            payment.appointment_id,
            payment.id,
            payment.status,
            background_tasks,
        )

        return payment

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel payment: {str(e)}",
        )


@router.post("/{payment_id}/refund", response_model=PaymentOut)
async def refund_payment(
        payment_id: int,
        amount: Optional[float] = None,
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Refund a payment.
    Only accessible by admins.
    """
    # Get payment
    stmt = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found",
        )

    # Check if payment can be refunded
    if payment.status != PaymentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot refund payment with status {payment.status}",
        )

    # Initialize appropriate payment service
    if payment.provider == PaymentProvider.STRIPE:
        payment_service = StripePaymentService()
    elif payment.provider == PaymentProvider.PAYPAL:
        payment_service = PayPalPaymentService()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported payment provider: {payment.provider}",
        )

    try:
        # Refund payment with provider
        if not payment.provider_transaction_id and not payment.provider_payment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No provider transaction ID available for refund",
            )

        refund_result = await payment_service.refund_payment(
            payment.provider_transaction_id or payment.provider_payment_id,
            amount,
        )

        # Update payment status
        payment.status = PaymentStatus.REFUNDED
        payment.refunded_at = datetime.utcnow()

        # Save changes
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        # Update appointment status
        appointment_service = AppointmentService(db, EmailService())
        await appointment_service.update_appointment_payment_status(
            payment.appointment_id,
            payment.id,
            payment.status,
            background_tasks,
        )

        return payment

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refund payment: {str(e)}",
        )