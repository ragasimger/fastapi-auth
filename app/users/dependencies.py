from typing import Annotated

from fastapi import Depends

from app.users.services.user import UserServiceRepository
from db.session import SessionDep

from .proto import UserProto


async def get_user_service(
    session: SessionDep,
) -> UserProto:
    """
    Dependency to get the UserServiceRepository instance.
    """
    return UserServiceRepository(session)


UserServiceDependency = Annotated[UserProto, Depends(get_user_service)]
