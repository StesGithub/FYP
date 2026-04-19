FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.12

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY lambda_function.py .

CMD ["lambda_function.lambda_handler"]