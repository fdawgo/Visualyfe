FROM python:3.12.2-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy .kaggle folder
COPY ./.kaggle /root/.kaggle

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY ./instance /app/inctance
COPY ./main.py /app/main.py
COPY ./visulyfe /app/visulyfe

# Expose port 5000 for Flask
EXPOSE 5000

ENTRYPOINT [ "python" ]

CMD [ "./main.py" ]