from prisma import Prisma

db = Prisma()


async def connect_db():
    """Connect to database."""
    if not db.is_connected():
        await db.connect()


async def disconnect_db():
    """Disconnect from database."""
    if db.is_connected():
        await db.disconnect()
