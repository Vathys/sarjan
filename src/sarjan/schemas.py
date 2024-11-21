from typing import Optional, Dict, List, Any
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path


class WorkspaceSchema(BaseModel):
    workspace_path: Path
    meta: Optional[Dict[str, Any]] = None


class DocumentSchema(BaseModel):
    path: Path
    content: Optional[str] = ""
    meta: Optional[Dict[str, Any]] = None


class ConnectionSchema(BaseModel):
    source: str
    target: str
    meta: Optional[Dict[str, Any]] = None


class EdgeSchema(BaseModel):
    source: str | DocumentSchema
    target: str | DocumentSchema
    connections: List[ConnectionSchema]
