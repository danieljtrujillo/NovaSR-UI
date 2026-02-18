## NovaSR: Pushing the Limits of Extreme Efficiency in Audio Super-Resolution

<p align="center">
  <a href="https://huggingface.co/YatharthS/NovaSR">
    <img src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Model-FFD21E" alt="Hugging Face Model">
  </a>
  &nbsp;
  <a href="https://huggingface.co/spaces/YatharthS/NovaSR">
    <img src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Space-blue" alt="Hugging Face Space">
  </a>
  &nbsp;
  <a href="https://www.kaggle.com/code/yatharthsharma888/novasr-training">
    <img src="https://img.shields.io/badge/Kaggle-Training%20Notebook-20BEFF?logo=kaggle&logoColor=white" alt="Kaggle Notebook">
  </a>
</p>

NovaSR is a tiny ~52 KB audio upsampling model that upscales muffled 16 kHz audio into clear, crisp 48 kHz audio at speeds over 3,500x real-time. It includes a **desktop GUI** and **Windows right-click integration** for one-click audio upscaling.

https://github.com/user-attachments/assets/c81f87eb-f6de-4bf9-85bd-dfc9a223a865

---

### Key Benefits

- **Speed** — Up to 3,600x real-time on a single A100 GPU.
- **Quality** — On par with models 5,000x larger.
- **Size** — Just ~52 KB, several thousand times smaller than most.

### Why Is This Useful?

- **Enhancing TTS models** — Boost output quality with nearly zero computational cost.
- **Real-time enhancement** — On-device upscaling of calls, streams, and low-quality audio with minimal memory.
- **Restoring datasets** — Bulk-improve audio quality across entire datasets.

### Comparisons

Benchmarks on A100 GPU. Higher real-time factor = faster.

| Model      | Speed (Real-Time) | Model Size |
| :--------- | :---------------- | :--------- |
| **NovaSR** | **3,600x**        | **~52 KB** |
| FlowHigh   | 20x               | ~450 MB    |
| FlashSR    | 14x               | ~1,000 MB  |
| AudioSR    | 0.6x              | ~2,000 MB  |

### Examples

Check the [Hugging Face model page](https://huggingface.co/YatharthS/NovaSR) for audio samples, or try it live on [Hugging Face Spaces](https://huggingface.co/spaces/YatharthS/NovaSR).

---

## Prerequisites

| Requirement | Details |
| :---------- | :------ |
| **OS** | Windows 10/11 (context-menu feature is Windows-only; GUI and Python API work cross-platform) |
| **Python** | 3.9 or newer — [download here](https://www.python.org/downloads/). Make sure "Add Python to PATH" is checked during install. |
| **pip** | Comes with Python. Verify with `pip --version`. |
| **Git** | Needed only if installing from GitHub. [Download here](https://git-scm.com/downloads). |
| **GPU (optional)** | NVIDIA GPU with CUDA for maximum speed. CPU works fine — just pass `half=False`. |

---

## Installation

### Option A — One-Click Setup (Windows)

1. Clone or download this repository.
2. Double-click **`install.bat`** inside the repo folder.

This will:
- Install NovaSR and all Python dependencies.
- Register **"Upscale with NovaSR"** in the Windows right-click context menu for audio files.
- Launch the GUI.

### Option B — pip Install (All Platforms)

```bash
pip install git+https://github.com/ysharma3501/NovaSR.git
```

### Option C — Editable / Developer Install

```bash
git clone https://github.com/ysharma3501/NovaSR.git
cd NovaSR
pip install -e .
```

### Dependencies (auto-installed by pip)

`torch`, `torchaudio`, `torchcodec`, `timm`, `einops`, `soxr`, `huggingface_hub`

---

## Usage

### 1. Desktop GUI

Launch the graphical interface:

```bash
python novasr_gui.py
```

- Browse or type paths to one or more audio files (`.wav`, `.mp3`, `.flac`, `.ogg`, `.opus`, `.m4a`, `.aac`, `.wma`).
- Optionally choose an output folder (defaults to same directory as input).
- Toggle half-precision on/off (GPU = on, CPU = off for best speed).
- Set **Compounding cycles** (1–10) to run the upscaled output back into the pipeline repeatedly.
- Optionally enable **Denoise profile** and/or **Post-EQ profile**.
- Optionally enable **Apply profile between cycles** to process audio between each SR pass.
- Enable **Dual output mode** to save both:
  - `<original_name>_48kHz.wav` (raw SR output)
  - `<original_name>_48kHz_profile.wav` (denoise/post-EQ output)
- Use **A/B Preview** controls in the GUI:
  - Select **Input (A)** or **Output (B)**
  - Click **Play** / **Stop** for quick quality checks

If profile options are enabled but dual-output is disabled, the profiled result is saved to `<original_name>_48kHz.wav`.

> Note: A/B playback currently uses Windows-native playback.

### 2. Windows Right-Click Context Menu

After running the installer (Option A above, or manually):

```bash
python install_context_menu.py --install
```

You can now **right-click any audio file** in Windows Explorer and select **"Upscale with NovaSR"**. The GUI will open with that file pre-loaded.

Supported formats: `.wav`, `.mp3`, `.flac`, `.ogg`, `.opus`, `.m4a`, `.aac`, `.wma`

To remove the context menu entry later:

```bash
python install_context_menu.py --uninstall
```

### 3. Python API

```python
from NovaSR import FastSR

# Load model (downloads weights from Hugging Face on first run)
upsampler = FastSR()

# For CPU-only machines (3-4x faster than half-precision on CPU):
# upsampler = FastSR(half=False)
```

Process a file:

```python
import torchaudio

# Load and resample input to 16 kHz
lowres_audio = upsampler.load_audio("input.wav")

# Run super-resolution
highres_audio = upsampler.infer(lowres_audio).cpu()

# Save as 48 kHz WAV
torchaudio.save("output_48kHz.wav", highres_audio, 48000)
```

In a Jupyter notebook:

```python
from IPython.display import Audio

lowres_audio = upsampler.load_audio("input.wav")
highres_audio = upsampler.infer(lowres_audio).cpu()
display(Audio(highres_audio, rate=48000))
```

> **Note:** `FastSR()` is a Python class. Run it inside Python (`python`, a `.py` script, or a notebook) — not directly in bash/PowerShell.

---

## Project Structure

```
NovaSR/
├── NovaSR/                      # Python package
│   ├── __init__.py              # FastSR class
│   ├── speechsr.py              # SynthesizerTrn / Generator model
│   ├── activations.py           # Snake / SnakeBeta activations
│   ├── commons.py               # Utility functions
│   └── resample.py              # Polyphase up/down sampling
├── novasr_gui.py                # Tkinter desktop GUI
├── install_context_menu.py      # Windows registry context-menu installer
├── install.bat                  # One-click Windows setup script
├── setup.py                     # pip package definition
├── LICENSE
├── NOTICE.md
└── README.md
```

---

## Training

Train the model further on custom datasets using the Kaggle notebook:
https://www.kaggle.com/code/yatharthsharma888/novasr-training

---

## FAQ

**Q: How much data was this trained on?**
A: Just 100 hours (MLS-Sidon + VCTK).

**Q: How is it so small?**
A: Fewer than 10 tiny Conv1d layers with Snake activations (based on BigVGAN) — optimized for maximum quality at minimal size.

**Q: Will benchmarks come?**
A: Yes — the model is still being trained further and will be benchmarked later.

**Q: I get `bash: from: command not found` when I type `from NovaSR import FastSR`.**
A: You're typing Python code into a shell. Run `python` first to enter the Python interpreter, or put the code in a `.py` file and run `python your_script.py`.

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding guidelines, and how to submit pull requests.

For bug reports or feature requests, please [open an issue](https://github.com/ysharma3501/NovaSR/issues).

---

## Final Notes

Repo stars and model likes are appreciated if you find this helpful. Thank you!

Email: yatharthsharma3501@gmail.com
