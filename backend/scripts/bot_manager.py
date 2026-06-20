import sys
import os
sys.path.insert(0, '/app')

import asyncio
import logging
from app.bot.main import main

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    asyncio.run(main())
