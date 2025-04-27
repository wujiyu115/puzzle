FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a volume for the database
VOLUME /app/data

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV SQLALCHEMY_DATABASE_URI=sqlite:///data/puzzle_data.db

# LLM API Keys (可以在运行容器时通过环境变量覆盖)
# ENV DEEPSEEK_API_KEY=your-deepseek-api-key
# ENV OPENROUTER_API_KEY=your-openrouter-api-key
# ENV QIANWEN_API_KEY=your-qianwen-api-key

# Initialize the database
RUN mkdir -p /app/data /app/logs
RUN python init_db.py

# Expose the port
EXPOSE 5000

# Run the application
CMD ["python", "run.py"]
