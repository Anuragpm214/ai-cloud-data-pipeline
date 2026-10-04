#!/usr/bin/env python3
"""Upload both samples and fail clearly if either pipeline does not complete."""
import argparse
import json
import sys
from pathlib import Path
import time
import requests


def run_demo(base_url='http://localhost:8000', timeout=180):
    health = requests.get(f'{base_url}/health', timeout=10)
    health.raise_for_status()
    samples = Path(__file__).resolve().parents[1] / 'data' / 'samples'
    for filename, data_type in [('sample_structured.csv', 'structured'), ('sample_unstructured.txt', 'unstructured')]:
        with (samples / filename).open('rb') as handle:
            response = requests.post(f'{base_url}/api/v1/upload', files={'file': (filename, handle)}, data={'data_type': data_type}, timeout=30)
        response.raise_for_status()
        job_id = response.json()['job_id']
        print(f'{filename}: {job_id}')
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = requests.get(f'{base_url}/api/v1/jobs/{job_id}', timeout=15)
            response.raise_for_status()
            job = response.json()
            print(f"  {job['status']}")
            if job['status'] == 'INFERENCE_COMPLETED':
                print(json.dumps(job, indent=2))
                break
            if job['status'] == 'FAILED':
                raise RuntimeError(job.get('error_message', 'Pipeline failed'))
            time.sleep(2)
        else:
            raise TimeoutError(f'Job {job_id} did not finish within {timeout}s')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://localhost:8000')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    try:
        run_demo(args.base_url.rstrip('/'), args.timeout)
    except requests.ConnectionError:
        print(f"Cannot connect to the pipeline at {args.base_url}. "
              "Start the services with 'docker compose up --build -d --wait' first. "
              "If Docker reports permission denied, run that Docker command with sudo.",
              file=sys.stderr)
        sys.exit(1)
    except (requests.RequestException, RuntimeError, TimeoutError) as exc:
        print(f"Demo failed: {exc}", file=sys.stderr)
        sys.exit(1)
