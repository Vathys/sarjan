from typing import Optional, Any, List, Dict
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..schemas import DocumentSchema
from ..state import current_workspace

document = APIRouter()


@document.get("/documents", tags=["Documents"])
async def get_documents(query: Optional[str] = None) -> List[DocumentSchema]:
    """Get all documents or all documents fulfilling a query"""
    if query is None:
        nodes = current_workspace.graph.nodes
        return [nodes[node]["document"].get_schema() for node in nodes]
    else:
        raise NotImplementedError("Querying documents is not yet implemented")


@document.get("/documents/{path}", tags=["Documents"])
async def get_document(path: Path) -> DocumentSchema:
    """Get a document by id"""
    try:
        print(f"Finding path {path}")
        return current_workspace.get_document(f"./{path}").get_schema()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@document.post("/documents", tags=["Documents"])
async def new(data: DocumentSchema) -> DocumentSchema:
    """Create a new document"""
    doc = current_workspace.get_or_create_document(data.path)
    doc.write_content(data.content)
    doc.update_metadata(data.meta)
    return doc.get_schema()


@document.get("/documents/{path}/meta", tags=["Documents"])
async def meta(path: Path) -> Dict[str, Any]:
    """Get document metadata"""
    try:
        doc = current_workspace.get_document(f"./{path}")
        return doc.metadata
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@document.get("/documents/{path}/meta/keys", tags=["Documents"])
async def get_meta_keys(path: Path) -> Optional[List[str]]:
    """Get document metadata keys"""
    try:
        doc = current_workspace.get_document(f"./{path}")
        return list(doc.metadata.keys())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@document.get("/documents/{path}/meta/{key}", tags=["Documents"])
async def get_metadata_value(path: Path, key: str) -> Any:
    """Get document metadata value for a key"""
    try:
        doc = current_workspace.get_document(f"./{path}")
        return doc.metadata[key]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@document.post("/documents/{path}/meta", tags=["Documents"])
async def update_metadata(path: Path, meta: Dict[str, Any]) -> DocumentSchema:
    """Update the metadata for a dict"""
    try:
        doc = current_workspace.get_document(f"./{path}")
        doc.update_metadata(meta)
        return doc.get_schema()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@document.delete("/documents/{path}", tags=["Documents"])
async def delete_document(path: Path, in_filesystem: Optional[bool] = False):
    """Delete a document"""
    try:
        current_workspace.delete_document(path, in_filesystem)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@document.delete("/documents/{path}/meta/{key}", tags=["Documents"])
async def delete_metadata_key(path: Path, key: str):
    """Delete a metadata key"""
    try:
        doc = current_workspace.get_document(f"./{path}")
        del doc.metadata[key]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
