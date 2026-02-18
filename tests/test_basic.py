"""
Basic tests for NovaSR package
Run with: pytest tests/
"""
import os
import tempfile
import torch
import pytest


def test_import():
    """Test that NovaSR can be imported successfully."""
    from NovaSR import FastSR
    assert FastSR is not None


def test_audio_loading_helper():
    """Test the internal audio loading helper function."""
    from NovaSR import _safe_load_audio
    
    # Create a simple test audio file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
    
    try:
        # Create a simple audio tensor
        test_audio = torch.randn(1, 16000)
        import torchaudio
        torchaudio.save(temp_path, test_audio, 16000)
        
        # Test loading
        audio, sr = _safe_load_audio(temp_path)
        assert audio is not None
        assert sr == 16000
        assert audio.shape[1] == 16000
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_fastsr_initialization():
    """Test FastSR initialization without loading model weights."""
    # This test would require model weights to be available
    # Skip for now if no internet connection
    pytest.skip("Requires model weights download - integration test")


def test_supported_extensions():
    """Test that the supported extensions list is defined correctly."""
    import novasr_gui
    
    assert hasattr(novasr_gui, 'SUPPORTED_EXTENSIONS')
    extensions = novasr_gui.SUPPORTED_EXTENSIONS
    
    # Check that common formats are supported
    assert '.wav' in extensions
    assert '.mp3' in extensions
    assert '.flac' in extensions


def test_is_audio_file():
    """Test the is_audio_file helper function."""
    from novasr_gui import is_audio_file
    
    assert is_audio_file("test.wav") is True
    assert is_audio_file("test.mp3") is True
    assert is_audio_file("test.txt") is False
    assert is_audio_file("test.WAV") is True  # Case insensitive


def test_short_exc_helper():
    """Test the exception formatting helper."""
    from novasr_gui import _short_exc
    
    exc = ValueError("Test error message")
    result = _short_exc(exc)
    assert "ValueError" in result
    assert "Test error message" in result


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
