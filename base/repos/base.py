import logging
from collections.abc import Sequence
from typing import Any, Dict, Generic, List, Optional, Protocol, Type, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)

logger = logging.getLogger(__name__)


class SQLAlchemyBaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        logger.info(f"Creating new {self.model.__name__} with available data")
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    # async def get(self, id: Any, load_options=None) -> Optional[ModelType] | None:
    #     logger.info(f"Getting {self.model.__name__} with id {id}")
    #     result = await self.session.execute(
    #         select(self.model).filter(self.model.id == id)
    #     )
    #     instance = result.scalar_one_or_none()
    #     if instance is None:
    #         logger.info(f"{self.model.__name__} with id {id} not found")
    #     return instance

    async def get(self, id: Any, *, load_options=None):
        logger.info(f"Getting {self.model.__name__} with id {id}")

        stmt = select(self.model).where(
            self.model.id == id, self.model.deleted_at.is_(None)
        )

        if load_options:
            stmt = stmt.options(*load_options)

        result = await self.session.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance is None:
            logger.warning(f"{self.model.__name__} with id {id} not found")
        return instance

    async def get_all(self) -> List[ModelType]:
        logger.info(f"Getting all instances of {self.model.__name__}")
        result = await self.session.execute(
            select(self.model).where(self.model.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    async def update_instance(
        self, db_obj: ModelType, obj_in: Dict[str, Any]
    ) -> ModelType:
        logger.info(f"Updating {self.model.__name__} with id {db_obj.id}")
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def update_by_id(self, id: Any, obj_in: Dict[str, Any]) -> ModelType:
        db_obj = await self.get(id)
        if not db_obj:
            raise ValueError(f"{self.model.__name__} with id {id} not found")
        return await self.update_instance(db_obj, obj_in)

    async def delete(self, db_obj: ModelType) -> None:
        logger.info(f"Deleting {self.model.__name__} with id {db_obj.id}")
        await self.session.delete(db_obj)
        await self.session.commit()

    async def soft_delete(self, db_obj: ModelType) -> None:
        logger.info(f"Soft deleting {self.model.__name__} with id {db_obj.id}")
        if hasattr(db_obj, "deleted_at"):
            from datetime import datetime

            setattr(db_obj, "deleted_at", datetime.now())
            self.session.add(db_obj)
            await self.session.commit()
        else:
            logger.error(
                f"{self.model.__name__} does not have 'deleted_at' attribute for soft delete"
            )
            raise AttributeError(f"{self.model.__name__} does not support soft delete")


class RepositoryProto(Protocol[ModelType]):
    async def get(self, id: int) -> ModelType | None:
        """Get instance by ID."""
        ...

    async def list(self, **filters) -> Sequence[ModelType]:
        """List all instances with optional filters."""
        ...

    async def add(self, instance: ModelType) -> ModelType:
        """Add new instance."""
        ...

    async def update(self, instance: ModelType) -> ModelType:
        """Update existing instance."""
        ...

    async def delete(self, id: int) -> None:
        """Delete instance by ID."""
        ...
