FROM tensorflow/tensorflow:2.5.0

RUN pip install --upgrade -i https://pypi.tuna.tsinghua.edu.cn/simple pip setuptools wheel

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    fastapi \
    uvicorn \
    python-multipart \
    matplotlib \
    nmrglue \
    scikit-learn \
    pandas \
    tqdm

WORKDIR /app
COPY . .

RUN mkdir -p uploads static/plots

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
