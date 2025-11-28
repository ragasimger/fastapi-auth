import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session

"""
import asyncio
from db.repl_utils import get_repl_session
session = get_repl_session()

from app.users.views.users import retrieve_user_detail
asyncio.run(retrieve_user_detail(session, 1))
"""


def get_repl_session() -> AsyncSession:
    """
    Returns a real AsyncSession for REPL usage.
    Usage:
        session = get_repl_session()
    """

    async def _get():
        async for session in get_session():
            return session

    return asyncio.run(_get())
