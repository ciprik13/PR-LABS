FROM python:3.11-slim
WORKDIR /app
COPY server/server_single_threaded.py .
COPY server/server_multi_threaded.py .
COPY server/content/ ./content/
EXPOSE 8080

CMD ["python", "server_multi_threaded.py", "./content"]