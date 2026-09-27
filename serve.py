#!/usr/bin/env python3
"""
Ashu AI Companion - Local HTTP Bridge with NVIDIA NIM Support.

This bridge connects the Android app / Web PWA to Ashu's brain.
Supports: Local GGUF models, NVIDIA NIM (free tier), Google Gemini, OpenAI-compatible.

Usage:
    python serve.py --nim                    # Use NVIDIA NIM (free tier)
    python serve.py --nim --nim-model meta/llama-3.1-8b-instruct
    python serve.py --nim --model-path ~/models/qwen3-4b.gguf  # Hybrid: local + NIM fallback
    python serve.py --cloud                  # Use Gemini/OpenAI
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Add python/ directory to Python path so imports work
PROJECT_ROOT = Path(__file__).parent
PYTHON_ROOT = PROJECT_ROOT / "python"
sys.path.insert(0, str(PYTHON_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# Free NIM model options (pick one):
# - "nvidia/nemotron-3-ultra-550b-a55b"  # Nemotron 3 Ultra - WORKING (free tier)
# - "meta/llama-3.1-8b-instruct"        # EOL (retired)
# - "mistralai/mixtral-8x7b-instruct-v0.1"  # EOL (retired)
# - "google/gemma-2-9b-it"               # Not accessible with this API key
# - "nvidia/nemotron-3-ultra"            # May not be deployed
NIM_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"

# NIM endpoint (standard)
NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


def setup_environment(
    use_nim: bool = False,
    nim_key: str = "",
    nim_model: str = NIM_MODEL,
    use_cloud: bool = False,
    cloud_provider: str = "gemini",
):
    """Set up environment variables for cloud providers."""
    if use_nim:
        # Use environment variable for API key (never hardcode!)
        api_key = os.environ.get("NVIDIA_NIM_API_KEY") or nim_key
        if not api_key:
            print("[NIM] Warning: No API key provided. Set NVIDIA_NIM_API_KEY environment variable or use --nim-key")
        else:
            os.environ["NVIDIA_NIM_API_KEY"] = api_key
        os.environ["NIM_MODEL"] = nim_model
        os.environ["NIM_BASE_URL"] = NIM_BASE_URL
        print(f"[NIM] NVIDIA NIM configured: {nim_model}")
    elif use_cloud:
        if cloud_provider == "gemini":
            # Uses GOOGLE_AI_API_KEY from env
            print("[Cloud] Google Gemini fallback enabled")
        else:
            # Uses ASHU_CLOUD_API_KEY from env
            print("[Cloud] OpenAI-compatible fallback enabled")
    else:
        print("[Local] Local-only mode (offline fallback if no local model)")


def main():
    parser = argparse.ArgumentParser(description="Run Ashu's local HTTP bridge")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8765, help="Port")
    parser.add_argument("--db", default="ashu_memory.db", help="SQLite DB path")
    
    # Model options
    parser.add_argument("--model-path", help="Path to local GGUF model")
    parser.add_argument("--model-type", default="llama_cpp", choices=["llama_cpp", "onnx"])
    
    # NVIDIA NIM options (free tier)
    parser.add_argument("--nim", action="store_true", help="Use NVIDIA NIM (free tier)")
    parser.add_argument("--nim-model", default=NIM_MODEL, help="NIM model to use")
    parser.add_argument("--nim-key", default="", help="NIM API key (or set NVIDIA_NIM_API_KEY env var)")
    
    # Generic cloud options
    parser.add_argument("--cloud", action="store_true", help="Use cloud fallback (Gemini/OpenAI)")
    parser.add_argument("--cloud-provider", choices=["gemini", "openai"], default="gemini")
    
    args = parser.parse_args()

    # Setup environment for cloud providers
    setup_environment(
        use_nim=args.nim,
        nim_key=args.nim_key,
        nim_model=args.nim_model,
        use_cloud=args.cloud,
        cloud_provider=args.cloud_provider,
    )

    # Import and run server
    from python.protocols.local_server import run_server
    from brain.inference import CloudConfig
    
    # Build cloud config for the agent factory
    cloud_config = None
    if args.nim:
        cloud_config = CloudConfig(
            enabled=True,
            provider="nim",
            base_url=NIM_BASE_URL,
            model=args.nim_model,
            api_key_env="NVIDIA_NIM_API_KEY",  # Reads from env we just set
            temperature=0.7,
            max_tokens=768,
            timeout=60,
        )
    elif args.cloud:
        if args.cloud_provider == "gemini":
            cloud_config = CloudConfig.gemini(enabled=True)
        else:
            cloud_config = CloudConfig(
                enabled=True,
                provider="openai",
                base_url=os.getenv("ASHU_CLOUD_BASE_URL", "https://api.openai.com/v1"),
                model=os.getenv("ASHU_CLOUD_MODEL", "gpt-4o-mini"),
                api_key_env="ASHU_CLOUD_API_KEY",
            )

    print(f"\n[Ashu] Bridge starting...")
    print(f"   Host: {args.host}:{args.port}")
    print(f"   DB: {args.db}")
    
    from brain.model_manager import ModelManager
    model_mgr = ModelManager()
    status = model_mgr.status()
    if status.usable:
        print(f"   Local model: {status.name} ({status.size_mb:.0f} MB)")
    else:
        print(f"   Local model: Not installed ({status.reason})")
    
    if cloud_config and cloud_config.enabled:
        print(f"   Cloud: {cloud_config.provider} / {cloud_config.model} [OK]")
    else:
        print(f"   Cloud: Not configured")
    
    print(f"\n[Endpoints]")
    print(f"   GET  http://{args.host}:{args.port}/v1/health")
    print(f"   POST http://{args.host}:{args.port}/v1/chat")
    print(f"   GET  http://{args.host}:{args.port}/v1/memory")
    print(f"   POST http://{args.host}:{args.port}/v1/setup")
    
    print(f"\n[Android] Set bridge URL to http://<YOUR_LAN_IP>:8765")
    print(f"[Web] Open web/ashu_prototype.html and connect to bridge\n")

    run_server(
        host=args.host,
        port=args.port,
        db_path=args.db,
        cloud=cloud_config,
    )


if __name__ == "__main__":
    main()