# Puzzle Collection Web App

[![Build and Push Docker Image](https://github.com/username/puzzle/actions/workflows/docker-build-push.yml/badge.svg)](https://github.com/username/puzzle/actions/workflows/docker-build-push.yml)

> **Note:** Replace `username` in the badge URL with your GitHub username after forking/cloning the repository.

A Flask web application for storing and serving riddles, jokes, and idioms with a SQLite database.

## Features

- Store and manage riddles, jokes, and idioms with separate question and answer fields
- Interactive UI with show/hide functionality for answers
- Secure API endpoints with API key authentication
- Web interface for browsing and adding new entries
- API key management for controlling access to API endpoints
- Data deduplication using content hashing
- Modern UI with shadcn UI style

## Setup and Installation

### Local Development

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Initialize the database with sample data:
   ```
   python init_db.py
   ```

   If you're upgrading from a previous version:
   ```
   python migrate_db.py
   ```
4. Run the application:
   ```
   python app.py
   ```
5. Access the application at http://localhost:5000

### Docker Deployment

1. Clone the repository
2. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```
3. (Optional) Edit the `.env` file to customize settings
4. Build and start the Docker container:
   ```
   docker-compose up -d
   ```
   Or use the deployment script:
   ```
   ./deploy.sh
   ```
5. Access the application at http://localhost:5000
6. To stop the container:
   ```
   docker-compose down
   ```

### Using Docker without Docker Compose

1. Build the Docker image:
   ```
   docker build -t puzzle-app .
   ```
2. Run the Docker container:
   ```
   docker run -d -p 5000:5000 -v $(pwd)/data:/app/data --name puzzle-container puzzle-app
   ```
3. Access the application at http://localhost:5000
4. To stop the container:
   ```
   docker stop puzzle-container
   docker rm puzzle-container
   ```

## API Security

This application uses API key authentication to secure API endpoints. Only requests with valid API keys are allowed to access the API.

### Managing API Keys

1. Access the API key management page at http://localhost:5000/api/keys
   - Note: For security reasons, this page is only accessible from localhost (127.0.0.1)

2. Create a new API key by providing an optional description

3. Use the generated API key in your API requests

4. You can deactivate or reactivate keys as needed from the management page

### Using API Keys in Requests

You can provide your API key in one of two ways:

1. **HTTP Header** (recommended):
   ```
   X-API-Key: your_api_key_here
   ```

2. **URL Query Parameter**:
   ```
   ?api_key=your_api_key_here
   ```

#### Examples

**Using curl with header:**
```bash
curl -H "X-API-Key: your_api_key_here" http://localhost:5000/api/random/5
```

**Using URL parameter:**
```
http://localhost:5000/api/random/5?api_key=your_api_key_here
```

## API Endpoints

- `GET /api/random/<count>` - Get random entries (optional query parameter: `category`)
- `POST /api/add` - Add a new entry (JSON body: `{"question": "...", "answer": "...", "category": "..."}`)
  - Also supports legacy format: `{"content": "...", "category": "..."}`

## Project Structure

- `app.py` - Main Flask application
- `init_db.py` - Database initialization script
- `migrate_db.py` - Database migration script for upgrading from previous versions
- `templates/` - HTML templates
  - `base.html` - Base template with shadcn UI style
  - `index.html` - Home page
  - `browse.html` - Browse entries page
  - `add.html` - Add new entry page
- `static/` - Static assets (CSS, JS)
- `Dockerfile` - Docker configuration for containerization
- `docker-compose.yml` - Docker Compose configuration for easy deployment
- `data/` - Directory for SQLite database files (mounted as a volume in Docker)
- `.env.example` - Example environment variables file
- `deploy.sh` - Deployment script for Docker
- `tag-release.sh` - Script for creating and pushing version tags
- `.github/workflows/` - GitHub Actions workflow configurations
  - `docker-build-push.yml` - Workflow for building and pushing Docker images to Docker Hub

## Continuous Integration/Continuous Deployment (CI/CD)

This project includes a GitHub Actions workflow for automatically building and publishing the Docker image to Docker Hub.

### Setting Up GitHub Actions for Docker Hub

1. Fork or clone this repository to your GitHub account
2. Add the following secrets to your GitHub repository:
   - `DOCKERHUB_USERNAME`: Your Docker Hub username
   - `DOCKERHUB_TOKEN`: Your Docker Hub access token (create one at https://hub.docker.com/settings/security)
3. Push changes to the `main` or `master` branch, or create a tag starting with `v` (e.g., `v1.0.0`)
4. The GitHub Actions workflow will automatically:
   - Build the Docker image
   - Push it to Docker Hub under your username
   - Tag it appropriately based on the branch or tag name

### Manually Triggering the Workflow

You can manually trigger the workflow in two ways:

1. From the "Actions" tab in your GitHub repository, click on the "Build and Push Docker Image" workflow, then click "Run workflow".

2. Create a new release tag using the provided script:
   ```
   ./tag-release.sh v1.0.0 "Initial release"
   ```
   This will create and push a new tag, which will trigger the workflow.

## Database Schema

```sql
CREATE TABLE data_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category TEXT CHECK(category IN ('riddle', 'joke', 'idiom')) NOT NULL,
    content_hash TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
