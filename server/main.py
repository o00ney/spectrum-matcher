"""
FastAPI server for NMR spectrum matching.

Endpoints:
  POST /api/upload   — upload a zip of Bruker spectrum, get match results + plot
  GET  /api/plot/{id} — retrieve a generated comparison plot image
"""

import os
import shutil
import tempfile
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from model_runner import init as init_model, match
from plotter import plot_comparison, PLOT_DIR

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

    # find the Bruker spectrum directory by scanning for pdata/
    # read_bruker_h_base expects nmr_path/1/pdata/1, so return the
    # parent of the directory that contains 'pdata' (i.e. parent of '1/')
    inner_dir = extract_dir
    for dirpath, dirs, _ in os.walk(extract_dir):
        if 'pdata' in dirs:
            inner_dir = os.path.dirname(dirpath)
            break

    result = match(inner_dir)

    plot_name = plot_comparison(
        result['query_ppm'], result['query_fid'], result['results']
    )

    # strip heavy spectrum data from response; client gets plot via /api/plot
    light_results = []
    for r in result['results']:
        light_results.append({'name': r['name'], 'probability': r['probability']})
    result['results'] = light_results

    # cleanup temp files
    shutil.rmtree(job_dir)

    return {
        'query_name': result['query_name'],
        'results': result['results'],
        'plot_id': plot_name.replace('.png', ''),
        'model': {
            'name': 'DeepMID',
            'arch': 'Siamese CNN + Spatial Pyramid Pooling',
            'params': '470K',
            'task': 'NMR mixture component identification',
        },
    }


@app.get("/api/plot/{plot_id}")
async def get_plot(plot_id: str):
    plot_path = os.path.join(PLOT_DIR, f"{plot_id}.png")
    if not os.path.exists(plot_path):
        raise HTTPException(status_code=404, detail="Plot not found")
    return FileResponse(plot_path, media_type="image/png")
