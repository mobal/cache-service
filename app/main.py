import logging

import uvicorn
from fastapi import FastAPI
from mangum import Mangum

from app.config import Configuration

config = Configuration()
logger = logging.getLogger()

app = FastAPI(debug=config.app_stage == 'dev')


@app.get('/')
async def hello_world():
    return 'hello, world!'


handler = Mangum(app)

if __name__ == '__main__':
    uvicorn.run('app.main:app', host='localhost', port=3000, reload=True)
