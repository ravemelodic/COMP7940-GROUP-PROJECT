"""
Celery worker entry point
"""
import os
import sys

if __name__ == '__main__':
    worker_type = os.getenv('WORKER_TYPE', 'all')
    
    print(f"Starting Celery worker (type: {worker_type})")
    
    # Build celery worker command arguments
    argv = ['celery', '-A', 'tasks', 'worker', '--loglevel=INFO']
    
    # Configure which tasks this worker should handle
    if worker_type == 'video':
        argv.extend(['--queues=video', '--concurrency=2'])
    elif worker_type == 'ocr':
        argv.extend(['--queues=ocr', '--concurrency=1'])
    
    # Replace current process with celery worker
    os.execvp('celery', argv)
