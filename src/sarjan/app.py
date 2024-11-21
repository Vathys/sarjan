import os
import importlib
import pkgutil

from fastapi import FastAPI, APIRouter

from . import __version__

from .routers import workspace, document, connections


description = """
## Testing API Documentation for Sarjan

Goals
- Build a minimum working test workspace (probably take some articles from AdasiWiki or Wikipedia)
- Build a minimum front end to serve the backend.
- Brainstorm Warden integration
- Implement search within documents
"""

app = FastAPI(
    title="Sarjan API",
    description=description,
    version=__version__,
)


app.include_router(workspace)
app.include_router(document)
app.include_router(connections)


@app.get("/")
async def root():
    return {"message": "Hello World"}
