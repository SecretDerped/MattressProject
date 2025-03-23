FROM python:3.12
RUN uv pip install -r reqirements.txt
COPY . /app
WORKDIR /app
CMD ["python", "main.py"]