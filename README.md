# tumai-oai

## Deployment:
[website](https://v0-reinforcement-learning-ideas.vercel.app
)

## How to Run Locally

This project consists of three main parts: a FastAPI backend (teacher), a Python script (student), and a Next.js frontend.

### Environment Variables

You'll need to set up environment variables for the backend and frontend. Create `.env` files in the root directory and the `frontend` directory respectively, based on the examples below.

**Backend (`./.env`):**

```env
# OpenAI API Key for AI functionalities
OPENAI_API_KEY="<your_openai_api_key>"

# AI Model Configuration
DEFAULT_MODEL=gpt-4.1
DEFAULT_TEMPERATURE=1

# Path to local documents (if applicable)
DOCUMENTS_PATH=./documents

# Backend Configuration
FASTAPI_URL=http://127.0.0.1:8000/

# Supabase Credentials for database interaction
NEXT_PUBLIC_SUPABASE_URL="<your_supabase_url>"
NEXT_PUBLIC_SUPABASE_ANON_KEY="<your_supabase_anon_key>"
SUPABASE_SERVICE_ROLE_KEY="<your_supabase_service_role_key>" # Keep this secure!

# Application Identity (Example: Charite)
SELF_NAME="YourAppName"
SELF_URL="http://127.0.0.1:8000/" # Adjust if needed
SELF_LOGO_URL="<your_logo_url>" # Optional: Link to your app's logo
```

**Frontend (`frontend/.env`):**

```env
# OpenAI API Key (can be the same as backend)
OPENAI_API_KEY="<your_openai_api_key>"

# Supabase Credentials (Public)
NEXT_PUBLIC_SUPABASE_URL="<your_supabase_url>"
NEXT_PUBLIC_SUPABASE_ANON_KEY="<your_supabase_anon_key>"

# Configuration for connecting to the backend
FASTAPI_URL="http://127.0.0.1:8000"
```

### Running the Teacher FastAPI Backend

This service exposes the data for the student simulation.

```sh
# Navigate to the backend directory if necessary
# (Assuming your main.py is in the root for uvicorn)
uvicorn app.main:app --reload
```
The backend will be available at `http://127.0.0.1:8000`.

### Running the Student Simulation

This script interacts with the backend to simulate learning internal data.

```sh
# Ensure the backend is running
python ./main.py
```

### Running the Frontend

This provides the user interface.

```sh
cd frontend
pnpm install # If you haven't installed dependencies
pnpm run dev
```
The frontend will be available at `http://localhost:3000` (or another port if specified).

