FROM python:3.11-slim
WORKDIR /app
COPY server/server.py .
COPY server/content/ ./content/
EXPOSE 8080
CMD ["python", "server.py", "./content"]