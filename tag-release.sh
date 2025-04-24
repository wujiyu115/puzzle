#!/bin/bash

# This script helps create a new version tag and push it to GitHub
# Usage: ./tag-release.sh v1.0.0 "Release message"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <tag> [message]"
    echo "Example: $0 v1.0.0 \"Initial release\""
    exit 1
fi

TAG=$1
MESSAGE=${2:-"Release $TAG"}

echo "Creating tag $TAG with message: $MESSAGE"

# Create an annotated tag
git tag -a "$TAG" -m "$MESSAGE"

# Push the tag to the remote repository
git push origin "$TAG"

echo "Tag $TAG created and pushed to GitHub."
echo "The GitHub Actions workflow should now build and push the Docker image to Docker Hub."
echo "Check the status at: https://github.com/$(git config --get remote.origin.url | sed -e 's/.*github.com[:\/]\(.*\)\.git/\1/')/actions"
