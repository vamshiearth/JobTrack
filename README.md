# JobTrack

Intelligent Job Application Tracking System.

JobTrack is a full-stack application designed to organize job applications and eventually track recruitment progress through authorized Gmail integration.

## Technology Stack

### Frontend
- React
- TypeScript
- Vite

### Backend
- Python
- FastAPI
- Pydantic

### Planned integrations
- PostgreSQL
- SQLAlchemy
- Alembic
- Google OAuth 2.0
- Gmail API
- Background synchronization worker

## Current Features

- FastAPI backend foundation
- Backend health endpoint
- React frontend foundation
- Centralized frontend API client
- Backend connection status indicator
- Local development CORS
- Automated backend tests

## Project Structure

- `backend/` - FastAPI application
- `frontend/` - React application
- `docs/phase-1-architecture.md` - Approved architecture

## Run Backend

From the backend directory:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

## Run Frontend

From the frontend directory:

```powershell
npm install
npm run dev
```

Frontend: http://localhost:5173

## Run Tests

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend:

```powershell
npm run build
npm run lint
```

## Development Status

Phase 1 - Architecture: Complete

Phase 2 - Project Setup: Complete after final validation

Phase 3 - PostgreSQL implementation: Next

## Security

Do not commit `.env` files, OAuth credentials, database passwords, or virtual environments.

Gmail integration has not been implemented yet.
