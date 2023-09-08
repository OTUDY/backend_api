from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from scripts.router.user import router as user_router
from scripts.router.mission import router as mission_router
from scripts.router.classes import router as class_router
from scripts.router.reward import router as reward_router

import uvicorn

app = FastAPI(docs_url='/docs')

origins = [
    "https://otudy.co",  # Replace with your frontend URL,  # Allow localhost with IP
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/', status_code=status.HTTP_200_OK)
def index() -> Response:
    return JSONResponse(status_code=status.HTTP_200_OK, content={'message': 'Accessing main route index.'})

app.include_router(user_router, prefix='/api/v1')
app.include_router(mission_router, prefix='/api/v1')
app.include_router(class_router, prefix="/api/v1")
app.include_router(reward_router, prefix="/api/v1")


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)