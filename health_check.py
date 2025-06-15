#!/usr/bin/env python3
import sys
import asyncio
import asyncpg
import os
from datetime import datetime

async def health_check():
    try:
        # Проверка подключения к БД
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST', 'postgres'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('DB_USER', 'festival_user'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'festival_bot'),
            timeout=5
        )
        await conn.fetchval('SELECT 1')
        await conn.close()

        print(f"✅ Health check passed at {datetime.now()}")
        return 0
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(health_check()))