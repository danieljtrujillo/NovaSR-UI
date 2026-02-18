# Contributing to NovaSR

Thank you for your interest in contributing to NovaSR!

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ysharma3501/NovaSR.git
   cd NovaSR
   ```

2. **Install in editable mode:**
   ```bash
   pip install -e .
   ```
   
   Or install development dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation:**
   ```bash
   python -c "from NovaSR import FastSR; print('NovaSR installed successfully')"
   ```

## System Requirements

- **Python:** 3.9 or newer
- **OS:** Cross-platform (Windows, macOS, Linux)
  - Context menu integration is Windows-only
- **GPU (optional):** NVIDIA GPU with CUDA for faster processing
  - CPU mode works fine with `half=False`

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to public functions and classes
- Keep functions focused and concise

## Testing

Before submitting changes:

1. **Test on multiple Python versions** (3.9, 3.10, 3.11, 3.12)
2. **Test with and without GPU** if modifying core inference code
3. **Test audio loading/saving** with different formats (.wav, .mp3, .flac, etc.)
4. **Run the GUI** to ensure no regressions:
   ```bash
   python novasr_gui.py
   ```

## Common Development Tasks

### Running the GUI
```bash
python novasr_gui.py
```

### Testing Context Menu (Windows only)
```bash
# Install
python install_context_menu.py --install

# Uninstall
python install_context_menu.py --uninstall
```

### Using the Python API
```python
from NovaSR import FastSR
import torchaudio

# Initialize model
upsampler = FastSR(half=False)  # Use half=True for GPU

# Process audio
lowres = upsampler.load_audio("input.wav")
highres = upsampler.infer(lowres).cpu()
torchaudio.save("output_48kHz.wav", highres, 48000)
```

## Reporting Issues

When reporting bugs, please include:
- Python version (`python --version`)
- PyTorch version (`python -c "import torch; print(torch.__version__)"`)
- Operating system
- CUDA availability (`python -c "import torch; print(torch.cuda.is_available())"`)
- Full error traceback
- Steps to reproduce

## Pull Request Guidelines

1. **Create a feature branch** from `main`
2. **Make focused commits** with clear messages
3. **Test your changes** thoroughly
4. **Update documentation** if adding features
5. **Keep PRs small** and focused on a single issue/feature

## Questions?

Feel free to open an issue for questions or clarifications!

Email: yatharthsharma3501@gmail.com
