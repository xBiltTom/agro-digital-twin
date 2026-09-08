"""Administrative commands that require operator-supplied credentials."""

import argparse
import asyncio
import getpass

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.migrations import apply_pending_migrations
from app.core.security import hash_password
from app.models.user import Role, User
from app.services.seed_service import bootstrap_mvp_data, bootstrap_system_reference_data


async def create_admin(email: str, full_name: str, password: str) -> None:
    """Create one SUPERADMIN after initializing the structural catalog only."""
    settings.validate_runtime_security()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await apply_pending_migrations(engine)

    async with AsyncSessionLocal() as session:
        await bootstrap_system_reference_data(session)
        if await session.scalar(select(User).where(User.email == email)):
            raise ValueError("A user with that email already exists")
        role = await session.scalar(select(Role).where(Role.name == "SUPERADMIN"))
        if not role:
            raise RuntimeError("SUPERADMIN role is unavailable after RBAC bootstrap")
        session.add(User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            is_active=True,
            is_verified=True,
            roles=[role],
        ))
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="AP-3 administration")
    subcommands = parser.add_subparsers(dest="command", required=True)
    create_admin_parser = subcommands.add_parser("create-admin", help="Create the first administrator")
    create_admin_parser.add_argument("--email", required=True)
    create_admin_parser.add_argument("--full-name", required=True)
    subcommands.add_parser("bootstrap-mvp", help="Idempotently prepare the demonstrable MVP")
    args = parser.parse_args()

    if args.command == "bootstrap-mvp":
        async def bootstrap() -> None:
            try:
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
                await apply_pending_migrations(engine)
                async with AsyncSessionLocal() as session:
                    await bootstrap_system_reference_data(session)
                    await bootstrap_mvp_data(session)
            finally:
                await engine.dispose()
        try:
            asyncio.run(bootstrap())
        finally:
            pass
        print("MVP bootstrap complete")
    elif args.command == "create-admin":
        password = getpass.getpass("Administrator password: ")
        confirmation = getpass.getpass("Confirm administrator password: ")
        if not password:
            parser.error("The administrator password cannot be empty")
        if password != confirmation:
            parser.error("Passwords do not match")
        try:
            asyncio.run(create_admin(args.email, args.full_name, password))
        finally:
            asyncio.run(engine.dispose())
        print(f"Administrator created for {args.email}")


if __name__ == "__main__":
    main()
