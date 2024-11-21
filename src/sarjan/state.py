import os
from fs.osfs import OSFS
from .base import Workspace

rel_path = "../test_workspace"

if not os.path.exists(rel_path):
    os.makedirs(rel_path)

current_workspace = Workspace(OSFS(rel_path))

if current_workspace.workspace.exists("./workspace.json"):
    current_workspace.load()
