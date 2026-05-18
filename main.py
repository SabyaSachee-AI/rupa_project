"""Root entry point for Streamlit Cloud (use main file path: ``main.py``).

Delegates to the application in ``app/main.py``. Keeps ``from app.*`` imports working
when Cloud sets the working directory to the repository root.
"""

from __future__ import annotations

from app.main import main

if __name__ == "__main__":
    main()
