"""
Initial setup script for the application.
This script creates the first admin user and sets up the database.
"""

import asyncio
import logging
import os
from typing import Optional

import click
from sqlalchemy import select

from app.config import settings
from app.core.security import get_password_hash
from app.database import SessionLocal, get_db, init_db
from app.models.admin import Admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_admin_sync(
        email: str,
        password: str,
        full_name: str = "Admin User",
        is_superuser: bool = True,
) -> Optional[Admin]:
    """
    Create an admin user synchronously.

    Args:
        email: Admin email.
        password: Admin password.
        full_name: Admin full name.
        is_superuser: Whether the admin is a superuser.

    Returns:
        Created admin user or None if already exists.
    """
    db = SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(Admin).filter(Admin.email == email).first()
        if admin:
            logger.info(f"Admin user {email} already exists.")
            return None

        # Create admin
        hashed_password = get_password_hash(password)
        admin = Admin(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            is_superuser=is_superuser,
            is_active=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)
        logger.info(f"Created admin user: {email}")
        return admin
    finally:
        db.close()


async def create_initial_admin() -> None:
    """Create the initial admin user from environment variables."""
    admin_email = settings.ADMIN_EMAIL
    admin_password = settings.ADMIN_PASSWORD

    if not admin_email or not admin_password:
        logger.warning(
            "ADMIN_EMAIL or ADMIN_PASSWORD not set. "
            "Skipping initial admin creation."
        )
        return

    # Create admin user
    admin = create_admin_sync(
        email=admin_email,
        password=admin_password,
        full_name="Admin User",
        is_superuser=True,
    )

    if admin:
        logger.info(f"Created initial admin user: {admin_email}")
    else:
        logger.info(f"Admin user {admin_email} already exists.")


@click.command()
@click.option("--email", prompt="Admin email", help="Email for the admin user")
@click.option(
    "--password", prompt=True, hide_input=True, help="Password for the admin user"
)
@click.option("--name", prompt="Full name", help="Full name for the admin user")
def create_admin(email: str, password: str, name: str) -> None:
    """Create an admin user from command line."""
    # Initialize database
    init_db()

    # Create admin user
    admin = create_admin_sync(
        email=email,
        password=password,
        full_name=name,
        is_superuser=True,
    )

    if admin:
        click.echo(f"Created admin user: {email}")
    else:
        click.echo(f"Admin user {email} already exists.")


@click.group()
def cli() -> None:
    """TODOenBALANCE backend management commands."""
    pass


cli.add_command(create_admin)


@cli.command()
def initialize() -> None:
    """
    Initialize the application.

    This runs all initialization steps:
    - Create initial admin user from environment variables
    """
    # Initialize database
    init_db()

    # Create initial admin user
    asyncio.run(create_initial_admin())

    click.echo("Initialization complete.")


if __name__ == "__main__":
    cli()