from contextlib import asynccontextmanager
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from base.configs import settings

# DEBUGGING = True
DEBUGGING = False


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=DEBUGGING,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True,
    # connect_args={"options": "-c timezone=UTC"}
)


async_session = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


@asynccontextmanager
async def atomic(session: AsyncSession):
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def get_atomic_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        async with atomic(session):
            yield session


AtomicSessionDependency = Annotated[AsyncSession, Depends(get_atomic_session)]


SessionDependency = Annotated[AsyncSession, Depends(get_session)]


if settings.ATOMIC:
    SessionDep = SessionDependency
else:
    SessionDep = AtomicSessionDependency
