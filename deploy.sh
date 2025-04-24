#!/bin/bash

# Stop any running containers
echo "Stopping any running containers..."
docker-compose down

# Build and start the containers
echo "Building and starting containers..."
docker-compose up -d --build

# Check if the container is running
echo "Checking container status..."
docker-compose ps

echo "Deployment complete! Access the application at http://localhost:5000"
