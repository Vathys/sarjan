from datetime import datetime

major = 0
minor = 1

__version__ = datetime.now().strftime(f"v{major}.{minor}.%Y%m%d")

__all__ = ["__version__"]
