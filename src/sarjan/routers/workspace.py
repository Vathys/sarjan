import os
from typing import Any

from fastapi import APIRouter, Query
from fs.osfs import OSFS

from ..base import Workspace
from ..schemas import WorkspaceSchema
from ..state import current_workspace

workspace = APIRouter()


@workspace.get("/workspace")
async def get_workspace() -> WorkspaceSchema:
    """Get current workspace"""
    return current_workspace.get_schema()


@workspace.put("/workspace")
async def create_workspace(schema: WorkspaceSchema):
    """If workspace exists, set current_workspace as this workspace"""
    if not os.path.exists(schema.workspace_path):
        os.makedirs(schema.workspace_path)

    workspace = Workspace(OSFS(schema.workspace_path))
    if workspace.workspace.exists(workspace.save_file) and workspace.workspace.isfile(
        workspace.save_file
    ):
        workspace.load()

    workspace.update_metadata(schema.meta)
    workspace.save()

    global current_workspace
    current_workspace = workspace

    return workspace.get_schema()


@workspace.post("/workspace/{meta_key}")
async def update_workspace_meta(meta_key: str, value: Any):
    """Update workspace metadata"""
    current_workspace.update_metadata({meta_key: value})


@workspace.post("/workspace/save/")
async def save_workspace():
    """Save workspace"""
    current_workspace.save()
    return {"message": "Workspace saved"}
