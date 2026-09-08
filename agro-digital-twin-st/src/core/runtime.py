"""Execution policy shared by the independent training laboratory.

The laboratory defaults to CPU so a local machine without a supported GPU has
the same deterministic execution path. Set ``AGROTWIN_FORCE_CPU=0`` only when
the operator deliberately wants GPU training.
"""

from __future__ import annotations

import os


def configure_tensorflow_runtime() -> str:
    if os.getenv("AGROTWIN_FORCE_CPU", "1") != "1":
        return "GPU_OR_DEFAULT"
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
    try:
        import tensorflow as tf
        tf.config.set_visible_devices([], "GPU")
    except ImportError:
        return "TENSORFLOW_NOT_INSTALLED"
    except RuntimeError:
        # TensorFlow was already initialized; the environment setting remains
        # the best effort and the caller can still report its actual hardware.
        return "CPU_REQUESTED_AFTER_TF_INIT"
    return "CPU"
