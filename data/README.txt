Law / regulation reference documents live here.

- Mounted read-write into the backend container at /data
  (config.py: DATA_DIR = <project root>/data).
- Back this folder up together with backend/uploads and offline/ollama
  (setup.md section 7, "Backups").
- The military-law knowledge base currently shipped in the backend is
  compiled into backend/services/military_law_service.py, so an empty
  folder is a valid starting state.
