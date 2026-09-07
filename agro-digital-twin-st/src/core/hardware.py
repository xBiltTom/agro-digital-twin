"""
Hardware & Compute Device Detection Module for AgroTwin-AI.
Detects CPU, GPU (TensorFlow/CUDA), and RAM resources.
Ensures CPU execution is always supported and GPU is used opportunistically.
"""

import os
import platform
from typing import Dict, Any, List


def detect_compute_device() -> Dict[str, Any]:
    """
    Detects available compute devices (CPU, GPU) and framework backends.
    Does not crash if CUDA or GPU is absent.
    """
    # 1. CPU Information
    cpu_model = platform.processor() or "CPU x86_64"
    if os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass

    cpu_count_logical = os.cpu_count() or 1

    # 2. RAM Information
    ram_gb = 0.0
    ram_available_gb = 0.0
    if os.path.exists("/proc/meminfo"):
        try:
            with open("/proc/meminfo", "r") as f:
                mem_total = 0
                mem_avail = 0
                for line in f:
                    if "MemTotal" in line:
                        mem_total = int(line.split()[1])
                    elif "MemAvailable" in line:
                        mem_avail = int(line.split()[1])
                ram_gb = round(mem_total / (1024 ** 2), 2)
                ram_available_gb = round(mem_avail / (1024 ** 2), 2)
        except Exception:
            pass

    # 3. TensorFlow & GPU Detection
    tf_version = None
    tf_gpu_available = False
    gpus: List[Dict[str, str]] = []
    
    try:
        import tensorflow as tf
        tf_version = tf.__version__
        gpu_devices = tf.config.list_physical_devices("GPU")
        if gpu_devices:
            tf_gpu_available = True
            for d in gpu_devices:
                gpus.append({
                    "name": d.name,
                    "device_type": d.device_type
                })
    except Exception as e:
        tf_version = f"Error: {e}"

    # Summary
    device_mode = "GPU" if tf_gpu_available else "CPU"
    
    return {
        "device_mode": device_mode,
        "cpu": {
            "model": cpu_model,
            "cores": cpu_count_logical,
            "architecture": platform.machine()
        },
        "ram": {
            "total_gb": ram_gb,
            "available_gb": ram_available_gb
        },
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "python_version": platform.python_version()
        },
        "tensorflow": {
            "version": tf_version,
            "gpu_available": tf_gpu_available,
            "gpus": gpus
        }
    }
