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
from fastapi.middleware.gzip import GZipMiddleware

from downsample import downsample
from model_runner import init as init_model, match, get_config
from plotter import plot_comparison

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=500)


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

    # downsample spectrum data for client-side rendering
    ds_query_ppm = downsample(result['query_ppm'])
    ds_query_fid = downsample(result['query_fid'])
    for r in result['results']:
        if 'ppm' in r and 'fid' in r:
            r['ppm_ds'] = downsample(r['ppm'])
            r['fid_ds'] = downsample(r['fid'])

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
        entry = {'name': r['name'], 'probability': r['probability']}
        if 'ppm_ds' in r:
            entry['ppm_ds'] = r['ppm_ds']
            entry['fid_ds'] = r['fid_ds']
        light_results.append(entry)
    result['results'] = light_results

    shutil.rmtree(job_dir)

    return {
        'query_name': result['query_name'],
        'query_ppm': ds_query_ppm,
        'query_fid': ds_query_fid,
        'results': result['results'],
        'plot_base64': plot_b64,
        'model': dict(get_config()),
    }
