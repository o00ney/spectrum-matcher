FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade -i https://pypi.tuna.tsinghua.edu.cn/simple pip setuptools wheel

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    numpy matplotlib scipy scikit-learn pandas tqdm nmrglue

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    tensorflow

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    nvidia-cudnn-cu12 nvidia-cublas-cu12 nvidia-cuda-runtime-cu12

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    fastapi uvicorn python-multipart

WORKDIR /app
COPY . .

RUN mkdir -p uploads static/plots

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
