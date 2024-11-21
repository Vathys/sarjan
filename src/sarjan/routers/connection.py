from typing import List

from fastapi import APIRouter, HTTPException

from ..schemas import ConnectionSchema, EdgeSchema
from ..state import current_workspace

connections = APIRouter()


@connections.put("/connections/{source}/{target}", tags=["Connections"])
async def new(source: str, target: str) -> ConnectionSchema:
    """Create a new connection between two documents or tags"""
    conn = current_workspace.create_connection(source, target)
    return conn.get_schema()


@connections.get("/connections/from/{source}", tags=["Connections"])
async def get_outgoing(source: str) -> List[ConnectionSchema]:
    """Get all outgoing connections from a document or tag"""
    return [
        conn.get_schema()
        for conn in current_workspace.get_connections_with_source(source)
    ]


@connections.get("/connections/to/{target}", tags=["Connections"])
async def get_incoming(target: str) -> List[ConnectionSchema]:
    """Get all incoming connections to a document or tag"""
    return [
        conn.get_schema()
        for conn in current_workspace.get_connections_with_target(target)
    ]


@connections.get("/connections/{source}/{target}", tags=["Connections"])
async def get(source: str, target: str) -> List[ConnectionSchema]:
    """Get all connections between two documents or tags"""
    try:
        return current_workspace.get_connection(source, target).get_schema()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@connections.delete("/connections/{source}/{target}", tags=["Connections"])
async def delete(source: str, target: str) -> ConnectionSchema:
    """Delete a connection between two documents or tags"""
    try:
        conn = current_workspace.delete_connection(source, target)
        return conn.get_schema()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@connections.get("/edges/{source}/{target}", tags=["Edges"])
async def get_edge(source: str, target: str) -> EdgeSchema:
    """Get edge by source and target document paths"""
    if current_workspace.graph.has_edge(source, target):
        return EdgeSchema(
            current_workspace.graph.nodes[source]["document"].get_schema(),
            current_workspace.graph.nodes[target]["document"].get_schema(),
            [
                conn.get_schema()
                for conn in current_workspace.graph[source, target]["connlist"]
            ],
        )
    else:
        raise HTTPException(
            status_code=404, detail=f"Edge from {source} to {target} not found"
        )


@connections.get("/edges/from/{source}", tags=["Edges"])
async def get_outgoing_edges(source: str) -> List[ConnectionSchema]:
    """Get all outgoing connections from all tags in a document"""
    res = []
    if not current_workspace.graph.has_node(source):
        raise HTTPException(status_code=404, detail=f"Node {source} not found")
    for target in current_workspace.graph[source]:
        for connlist in current_workspace.graph[source, target]["connlist"]:
            res.extend([conn.get_schema() for conn in connlist])

    return res


@connections.get("/edges/to/{target}", tags=["Edges"])
async def get_incoming_edges(target: str) -> List[ConnectionSchema]:
    """Get all incoming connections to all tags in a document"""
    res = []
    if not current_workspace.graph.has_node(target):
        raise HTTPException(status_code=404, detail=f"Node {target} not found")
    for source in current_workspace.graph:
        if current_workspace.graph.has_edge(source, target):
            for connlist in current_workspace.graph[source, target]["connlist"]:
                res.extend([conn.get_schema() for conn in connlist])

    return res
