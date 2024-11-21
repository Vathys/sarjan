from typing import Any, List, Dict
from pathlib import Path
import json

import fs
from fs.base import FS
import networkx as nx
import pandoc

from .utils import recurse_remove_empty
from .schemas import WorkspaceSchema, DocumentSchema, ConnectionSchema


class Workspace:
    """

    Workspace
    =========

    A workspace is a collection of documents in a filesystem. Additionally, the workspace
    stores the documents in a graph, enabling users to create connections between documents.
    Each document is represented as a node in the graph and can have metadata associated with it.
    Documents are connected by edges which are associated with a list of connections. While an
    edge is undirected, the connections are directed and can have metadata associated with them.
    A connection can not only connect two documents, but also two tags within the documents.

    Parameters
    ----------
    workspace : FS
        A filesystem object which represents the workspace
    metadata : dict
        Metadata associated with the workspace

    Attributes
    ----------
    workspace : FS
        A filesystem object which represents the workspace
    graph : nx.Graph
        A graph object which represents the documents and connections in the workspace

    Methods
    -------
    get_or_create_document(doc_path: str) -> Document
        Get or create a document in the workspace

    get_document(doc_path: str) -> Document
        Get a document in the workspace
        raises ValueError if document not found

    create_document(doc_path: str) -> Document
        Create a document in the workspace
        If the file represented by the document does not exist, it is created

    write_document(doc_path: str, content: str)
        Write content to a document in the workspace
        If the document does not exist, it is created.

    update_document(doc_path: str, metadata: dict)
        Update metadata of a document in the workspace
        If the document does not exist, it is created.

    create_connection(source: str, target: str) -> Connection
        Create a connection between two documents in the workspace
        The source and target parameters are of the form "document_path:tag_path"
        To connect a document directly, use "document_path" as the source or target
        If the documents do not exist, they are created

    get_connection(source: str, target: str) -> Connection
        Get a connection between two documents or the tags in documents in the workspace
        raises ValueError if connection not found

    get_connections_with_source(source: str) -> list[Connection]
        Get all connections with the source being the document or tag described by source in the workspace
        raises ValueError if document not found

    get_connections_with_target(target: str) -> list[Connection]
        Get all connections with the target being the document or tag described by target in the workspace
        raises ValueError if document not found

    update_connection(source: str, target: str, metadata: dict)
        Update metadata of a connection in the workspace
        raises ValueError if connection not found

    delete_document(doc_path: str)
        Delete a document in the workspace. Deletes the file in the filesystem if it exists, and removes the document from the graph
        This will also recursively delete empty directories in the filesystem caused by the deletion of the file
        All associated connections with the document and its tags are also deleted
        If the document does not exist, it is ignored

    delete_connection(source: str, target: str)
        Delete a connection in the workspace
        If the connection was the only connection between two documents, the edge is also deleted
        raises ValueError if connection not found

    save()
        Save the workspace to the filesystem in workspace.json

    load()
        Load the workspace from the filesystem from workspace.json

    Example
    -------
    >>> from fs import open_fs
    >>> from api.base import Workspace
    >>> workspace = Workspace(open_fs("osfs://~/test_workspace"))
    >>> workspace.create_document("doc1.md")
    >>> workspace.write_document("doc1.md", "Hello, World!")
    >>> workspace.create_document("doc2.md")
    >>> workspace.create_connection("doc1.md", "doc2.md")
    >>> workspace.get_connections_with_source("doc1.md")
    [Connection("doc1.md", "doc2.md")]
    >>> workspace.get_document("doc1.md").read_content()
    "Hello, World!"
    >>> workspace.save()
    >>> workspace.delete_document("doc1.md")
    >>> workspace.load()
    >>> workspace.get_document("doc1.md")
    Document("doc1.md")
    """

    def __init__(self, workspace: FS | str, metadata: dict = {}):
        if isinstance(workspace, str):
            self.workspace = fs.open_fs(workspace)
        else:
            self.workspace = workspace
        self.graph = nx.Graph(**metadata)
        self.save_file = "workspace.json"

    def update_metadata(self, metadata: dict):
        if metadata:
            for key, value in metadata.items():
                self.graph.graph[key] = value

    def get_or_create_document(self, doc_path: str) -> "Document":
        if doc_path in self.graph.nodes:
            return self.graph.nodes[doc_path]["document"]

        return self.create_document(doc_path)

    def get_document(self, doc_path: str) -> "Document":
        if doc_path in self.graph.nodes:
            return self.graph.nodes[doc_path]["document"]

        raise ValueError(f"Document {doc_path} not found in workspace")

    def create_document(self, doc_path: str) -> "Document":
        # Creates a file in filesystem if it does not exist
        if not self.workspace.isfile(doc_path):
            if not self.workspace.exists(fs.path.dirname(doc_path)):
                self.workspace.makedirs(fs.path.dirname(doc_path))
            if self.workspace.create(doc_path):
                print(f"Created new file at {doc_path}")

        doc = Document(doc_path, self)
        # Add document to graph
        self.graph.add_node(doc_path, document=doc)
        return doc

    def write_document(self, doc_path: str, content: str):
        doc = self.get_or_create_document(doc_path)
        doc.write_content(content)

    def update_document(self, doc_path: str, metadata: dict):
        doc = self.get_document(doc_path)
        doc.update_metadata(metadata)

    def create_connection(self, source: str, target: str) -> "Connection":
        conn = Connection(source, target, self)
        source_doc_path, source_tag = Connection.separate_path(source)
        target_doc_path, target_tag = Connection.separate_path(target)

        # Ensure that documents exist in the graph and filesystem
        source_doc = self.get_or_create_document(source_doc_path)
        target_doc = self.get_or_create_document(target_doc_path)

        # Ensure that the tags exist
        if source_tag and source_tag not in source_doc.metadata.keys():
            source_doc.metadata[source_tag] = ""
        if target_tag and target_tag not in target_doc.metadata.keys():
            target_doc.metadata[target_tag] = ""

        # If edge exists, then add connection to connection list
        # else create a new edge with connection list
        if self.graph.has_edge(source_doc_path, target_doc_path):
            self.graph.edges[source_doc_path, target_doc_path]["connlist"].append(conn)
        else:
            self.graph.add_edge(source_doc_path, target_doc_path, connlist=[conn])

        return conn

    def get_connection(self, source: str, target: str) -> "Connection":
        source_doc_path = Connection.separate_path(source)[0]
        target_doc_path = Connection.separate_path(target)[0]

        # Ensure that edge between documents exists
        if self.graph.has_edge(source_doc_path, target_doc_path):
            connection_list = self.graph.edges[source_doc_path, target_doc_path][
                "connlist"
            ]

            # Find the connection in the connection list
            for conn in connection_list:
                if conn == (source, target):
                    return conn

            raise ValueError(
                f"Connection {source} -> {target} not found in connection list"
            )
        else:
            raise ValueError(f"Connection {source} -> {target} not found in workspace")

    def get_connections_with_source(self, source: str) -> List["Connection"]:
        source_doc_path = Connection.separate_path(source)[0]
        res = []
        if source_doc_path in self.graph_nodes:
            for target_doc_path in self.graph.neighbors(source_doc_path):
                connection_list = self.graph.edges[source_doc_path, target_doc_path][
                    "connlist"
                ]
                for conn in connection_list:
                    if conn.source == source:
                        res.append(conn)
            return res
        else:
            raise ValueError(f"Document {source_doc_path} not found in workspace")

    def get_connections_with_target(self, target: str) -> List["Connection"]:
        target_doc_path = Connection.separate_path(target)[0]
        res = []
        if target_doc_path in self.graph_nodes:
            for source_doc_path in self.graph.neighbors(target_doc_path):
                connection_list = self.graph.edges[source_doc_path, target_doc_path][
                    "connlist"
                ]
                for conn in connection_list:
                    if conn.target == target:
                        res.append(conn)
            return res
        else:
            raise ValueError(f"Document {target_doc_path} not found in workspace")

    def update_connection(self, source: str, target: str, metadata: dict):
        conn = self.get_connection(source, target)
        conn.update_metadata(metadata)

    def delete_document(self, doc_path: str, in_filesystem: bool = True):
        if in_filesystem and self.workspace.exists(doc_path):
            self.workspace.remove(doc_path)
            recurse_remove_empty(self.workspace, fs.path.dirname(doc_path))
        if doc_path in self.graph.nodes:
            self.graph.remove_node(doc_path)

    def delete_connection(self, source: str, target: str) -> "Connection":
        source_doc_path = Connection.separate_path(source)[0]
        target_doc_path = Connection.separate_path(target)[0]

        conn = self.get_connection(source, target)
        connection_list = self.graph.edges[source_doc_path, target_doc_path]["connlist"]
        connection_list.remove(conn)
        if len(connection_list) == 0:
            self.graph.remove_edge(source_doc_path, target_doc_path)

        return conn

    def save(self):
        if not self.workspace.exists(self.save_file):
            self.workspace.touch(self.save_file)
        with self.workspace.open(self.save_file, "w", encoding="utf-8") as f:
            node_link_data = nx.node_link_data(self.graph)
            f.write(json.dumps(node_link_data, cls=_WorkspaceJSONEncoder, indent=4))

    def load(self):
        with self.workspace.open(self.save_file, "r", encoding="utf-8") as f:
            data = json.loads(
                f.read(), object_hook=lambda dct: json_object_hook(dct, self)
            )
            self.graph = nx.node_link_graph(data)

    def get_schema(self) -> WorkspaceSchema:
        return WorkspaceSchema(
            workspace_path=self.workspace.getsyspath("."), meta=self.graph.graph
        )


class Document:

    class ProtectedMetadata(dict):
        def __init__(self, parent, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.parent: Document = parent

        def _delete_connections(self, key):
            source_conn_list = self.parent.workspace.get_connections_with_source(
                f"{self.parent.path}:{key}"
            )
            target_conn_list = self.parent.workspace.get_connections_with_target(
                f"{self.parent.path}:{key}"
            )

            for conn in source_conn_list:
                self.parent.workspace.delete_connection(conn.source, conn.target)
            for conn in target_conn_list:
                self.parent.workspace.delete_connection(conn.source, conn.target)

        def __delitem__(self, key):
            self._delete_connections(key)
            super().__delitem__(key)

        def pop(self, key, default=None):
            self._delete_connections(key)
            return super().pop(key, default)

    def __init__(self, path: str, workspace: Workspace):
        self.path = path
        self.workspace = workspace
        # To initialize the Document.ProtectedMetadata with an initial dictionary, do
        # self.metadata = Document.ProtectedMetadata(self, **metadata)
        self.metadata = Document.ProtectedMetadata(self)

    def read_content(self) -> str:
        with self.workspace.workspace.open(self.path, "r", encoding="utf-8") as f:
            return f.read()

    def get_html(self) -> str:
        content = self.read_content()
        pandoc_object = pandoc.read(content, format="markdown")
        html = pandoc.write(pandoc_object, format="html")

        return html

    def write_content(self, content: str):
        with self.workspace.workspace.open(self.path, "w", encoding="utf-8") as f:
            f.write(content)

    def update_metadata(self, metadata: Dict[str, Any]):
        if metadata:
            for key, value in metadata.items():
                self.metadata[key] = value

    def __repr__(self):
        return f"Document({self.path})"

    def __str__(self):
        return self.path

    def get_schema(self) -> DocumentSchema:
        return DocumentSchema(path=self.path, meta=self.metadata)


class Connection:
    def __init__(self, source: str, target: str, workspace: Workspace):
        self.source = source
        self.target = target
        self.workspace = workspace
        self.metadata = {}

    def update_metadata(self, metadata: str):
        if metadata:
            for key, value in metadata.items():
                self.metadata[key] = value

    def get_source_value(self):
        doc_path, tag = Connection.separate_path(self.source)
        doc = self.workspace.get_document(doc_path)
        if tag:
            if tag in doc.metadata.keys():
                return doc.metadata[tag]
            else:
                raise ValueError(f"Tag {tag} not found in document {doc_path}")
        else:
            raise ValueError(f"Source {self.source} is not a tag")

    def get_target_value(self):
        doc_path, tag = Connection.separate_path(self.target)
        doc = self.workspace.get_document(doc_path)
        if tag:
            if tag in doc.metadata.keys():
                return doc.metadata[tag]
            else:
                raise ValueError(f"Tag {tag} not found in document {doc_path}")
        else:
            raise ValueError(f"Target {self.target} is not a tag")

    def __eq__(self, other):
        if isinstance(other, Connection):
            return self.source == other.source and self.target == other.target
        elif isinstance(other, tuple[str, str]):
            return self.source == other[0] and self.target == other[1]
        else:
            raise ValueError(f"Cannot compare Connection with {type(other)}")

    def __repr__(self):
        return f"Connection({self.source}, {self.target})"

    def __str__(self):
        return f"{self.source} -> {self.target}"

    def get_schema(self) -> ConnectionSchema:
        return ConnectionSchema(
            source=self.source, target=self.target, meta=self.metadata
        )

    @classmethod
    def separate_path(cls, path: str):
        # The path in a component is structured as
        # document_path:tag_path
        comp = path.split(":")
        if len(comp) == 2:
            return Path(comp[0]), comp[1]
        elif len(comp) == 1:
            return Path(comp[0]), None
        else:
            raise ValueError(f"Invalid path {path}")


class _WorkspaceJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Document):
            return {"document.path": obj.path, "document.metadata": obj.metadata}
        elif isinstance(obj, Connection):
            return {
                "connection.source": obj.source,
                "connection.target": obj.target,
                "connection.metadata": obj.metadata,
            }
        else:
            return super().default(obj)


def json_object_hook(dct, workspace):
    if "document.path" in dct and "document.metadata" in dct:
        doc = Document(dct["document.path"], workspace)
        doc.update_metadata(dct["document.metadata"])
        return doc
    elif (
        "connection.source" in dct
        and "connection.target" in dct
        and "connection.metadata" in dct
    ):
        conn = Connection(dct["connection.source"], dct["connection.target"], workspace)
        conn.update_metadata(dct["connection.metadata"])
        return conn
    else:
        return dct
