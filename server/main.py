"""
FastAPI server for NMR spectrum matching.

Endpoints:
  POST /api/upload   — upload zip of Bruker spectrum, get results + plot (base64)
"""

import base64
import os
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException

from model_runner import init as init_model, match
from plotter import plot_comparison

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

app = FastAPI()


@app.on_event("startup")
async def startup():
    init_model()
    os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.post("/api/upload")
async def upload_spectrum(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="Please upload a .zip file")

    job_id = uuid.uuid4().hex
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    zip_path = os.path.join(job_dir, file.filename)
    with open(zip_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)

    extract_dir = os.path.join(job_dir, 'extracted')
    os.makedirs(extract_dir, exist_ok=True)
    shutil.unpack_archive(zip_path, extract_dir)

    inner_dir = extract_dir
    for dirpath, dirs, _ in os.walk(extract_dir):
        if 'pdata' in dirs:
            inner_dir = os.path.dirname(dirpath)
            break

    result = match(inner_dir)

    plot_name = plot_comparison(
        result['query_ppm'], result['query_fid'], result['results']
    )

    # read generated plot as base64
    plot_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static', 'plots', plot_name,
    )
    with open(plot_path, 'rb') as pf:
        plot_b64 = base64.b64encode(pf.read()).decode('ascii')
    os.remove(plot_path)

    light_results = []
    for r in result['results']:
        light_results.append({'name': r['name'], 'probability': r['probability']})
    result['results'] = light_results

    shutil.rmtree(job_dir)

    return {
        'query_name': result['query_name'],
        'results': result['results'],
        'plot_base64': plot_b64,
        'model': {
            'name': 'DeepMID',
            'arch': 'Siamese CNN + Spatial Pyramid Pooling',
            'params': '470K',
            'task': 'NMR mixture component identification',
        },
    }
