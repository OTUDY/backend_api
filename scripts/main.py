from fastapi import FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from .router.user import router as user_router
from .router.mission import router as mission_router
from .router.classes import router as class_router
from .router.reward import router as reward_router

from mangum import Mangum
#import ssl

#import uvicorn

app = FastAPI(docs_url='/docs')
handler = Mangum(app)

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain('cert.pem', keyfile='key.pem')

origins = [
    "*",
    'http://localhost:5173'  # Replace with your frontend URL,  # Allow localhost with IP
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#app.add_middleware(HTTPSRedirectMiddleware)

@app.get('/', status_code=status.HTTP_200_OK)
async def index() -> Response:
    return JSONResponse(status_code=status.HTTP_200_OK, content={'message': 'Accessing main route index.'})

@app.get('/test-pull')
async def root() -> Response:
    return "Successfully accessed to pulled version"

# def catch_all(path: str, request: Request) -> HTMLResponse:
#     return HTM('/', request)

app.include_router(user_router, prefix='/api/v1')
app.include_router(mission_router, prefix='/api/v1')
app.include_router(class_router, prefix="/api/v1")
app.include_router(reward_router, prefix="/api/v1")
