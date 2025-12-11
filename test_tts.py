#!/usr/bin/env python3
"""
Test script for ComfyUI ChatterBox TTS integration.
Run with: python test_tts.py "Your text here"
"""

import asyncio
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from comfyui_tts_service import create_tts_service

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("test_tts")

async def test_tts(text: str):
    """Test TTS synthesis and playback."""
    log.info(f"Testing TTS with text: {text}")
    
    # Create TTS service
    tts = create_tts_service()
    
    log.info(f"TTS Service Configuration:")
    log.info(f"  - Base URL: {tts.base_url}")
    log.info(f"  - Workflow: {tts.workflow_path}")
    log.info(f"  - Output Dir: {tts.output_dir}")
    log.info(f"  - Available: {tts.is_available}")
    
    if not tts.is_available:
        log.error("TTS service not available. Check COMFYUI_URL in .env")
        return
    
    # Check connection
    log.info("Checking connection to ComfyUI server...")
    connected = await tts.check_connection()
    if not connected:
        log.error(f"Cannot connect to ComfyUI at {tts.base_url}")
        return
    log.info("✅ Connected to ComfyUI server")
    
    # Load and verify workflow
    log.info("Loading workflow...")
    workflow = tts.load_workflow()
    if not workflow:
        log.error("Failed to load workflow")
        return
    log.info(f"✅ Workflow loaded: {len(workflow)} nodes")
    
    # Show workflow structure
    for node_id, node_data in workflow.items():
        class_type = node_data.get("class_type", "Unknown")
        inputs = list(node_data.get("inputs", {}).keys())
        log.info(f"  Node {node_id}: {class_type} -> inputs: {inputs}")
    
    # Test workflow preparation
    log.info("Preparing workflow with test text...")
    prepared = tts._prepare_workflow(text)
    if prepared is None:
        log.error("Workflow preparation failed")
        return
    
    prompt_data = prepared.get("prompt", {})
    log.info(f"✅ Workflow prepared with {len(prompt_data)} nodes")
    
    # Show the injected text
    for node_id, node_data in prompt_data.items():
        if "TTS" in node_data.get("class_type", "") or "Chatterbox" in node_data.get("class_type", ""):
            text_value = node_data.get("inputs", {}).get("text", "")
            log.info(f"  ChatterboxTTS text: {text_value[:100]}...")
    
    # Synthesize speech
    log.info("Synthesizing speech...")
    audio_path = await tts.synthesize_speech(text)
    
    if audio_path:
        log.info(f"✅ Audio generated: {audio_path}")
        
        # Verify file exists
        if os.path.exists(audio_path):
            size = os.path.getsize(audio_path)
            log.info(f"  File size: {size} bytes")
            
            # Play audio
            log.info("Playing audio...")
            if tts.play_audio_ephemeral(audio_path):
                await tts.wait_for_playback(timeout=30)
                log.info("✅ Playback complete")
            else:
                log.error("Failed to play audio")
        else:
            log.error(f"Audio file not found at: {audio_path}")
    else:
        log.error("❌ Speech synthesis failed")
    
    await tts.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = "Hi there! I'm Lass, and I'm exploring the world of Pokemon!"
    
    asyncio.run(test_tts(text))
