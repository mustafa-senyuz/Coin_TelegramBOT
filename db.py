# db.py
import aiosqlite
from datetime import datetime

DB_PATH = "coin_alerts.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS volumes (
                symbol TEXT,
                volume REAL,
                interval TEXT,
                timestamp TEXT
            )
        ''')
        await db.commit()


async def insert_volume_data(data: list[dict]):
    timestamp = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        for entry in data:
            await db.execute(
                '''
                INSERT INTO volumes (symbol, volume, interval, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (entry["symbol"], entry["volume"], entry["interval"],
                  timestamp))
        await db.commit()


async def get_previous_volume_data(interval: str) -> dict:
    """
    Return the most recent volume data (before the latest run) for each symbol.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Get the second most recent timestamp
        cursor = await db.execute(
            "SELECT DISTINCT timestamp FROM volumes WHERE interval = ? ORDER BY timestamp DESC LIMIT 2",
            (interval, ))
        rows = await cursor.fetchall()
        if len(rows) < 2:
            return {}  # No previous data available
        previous_timestamp = rows[1][0]

        cursor = await db.execute(
            "SELECT symbol, volume FROM volumes WHERE interval = ? AND timestamp = ?",
            (interval, previous_timestamp))
        result = await cursor.fetchall()
        return {symbol: volume for symbol, volume in result}
