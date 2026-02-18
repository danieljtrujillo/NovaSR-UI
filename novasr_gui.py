#!/usr/bin/env python3
"""
NovaSR - Minimalist Audio Super-Resolution GUI
Drag & drop or browse audio files → upscale 16kHz → 48kHz in one click.
"""
from __future__ import annotations

import os
import sys
import threading
import tempfile
import logging
import subprocess
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path

import torch
import torchaudio
import soundfile as sf

if os.name == "nt":
    import winsound


LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "novasr_gui.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
LOGGER = logging.getLogger("novasr_gui")


def _short_exc(exc: Exception) -> str:
    msg = str(exc).strip().splitlines()
    if not msg:
        return exc.__class__.__name__
    return f"{exc.__class__.__name__}: {msg[0]}"


def safe_torchaudio_load(path: str):
    load_errors = []
    try:
        audio_np, sample_rate = sf.read(path, always_2d=True, dtype="float32")
        waveform = torch.from_numpy(audio_np).transpose(0, 1)
        LOGGER.info("Loaded audio with soundfile: %s", path)
        return waveform, sample_rate
    except Exception as exc:
        load_errors.append(f"soundfile: {_short_exc(exc)}")
        LOGGER.warning("Audio load failed (soundfile): %s", _short_exc(exc))

    for backend in ("soundfile", "sox", "ffmpeg", None):
        try:
            if backend is None:
                waveform, sample_rate = torchaudio.load(path)
                LOGGER.info("Loaded audio with default backend: %s", path)
                return waveform, sample_rate
            waveform, sample_rate = torchaudio.load(path, backend=backend)
            LOGGER.info("Loaded audio with backend=%s: %s", backend, path)
            return waveform, sample_rate
        except Exception as exc:
            short = _short_exc(exc)
            load_errors.append(f"backend={backend}: {short}")
            LOGGER.warning("Audio load failed (backend=%s): %s", backend, short)
            if "torchcodec" in str(exc).lower() or "libtorchcodec" in str(exc).lower():
                LOGGER.warning("TorchCodec backend unavailable; stopping torchaudio backend probing.")
                break

    raise RuntimeError(
        "Failed to load audio with all torchaudio backends. "
        + " | ".join(load_errors)
    )


def safe_audio_save(path: str, waveform: torch.Tensor, sample_rate: int):
    save_errors = []
    audio = waveform.detach().cpu().float()
    if audio.dim() == 1:
        audio = audio.unsqueeze(0)
    audio = torch.clamp(audio, -1.0, 1.0)

    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    try:
        audio_np = audio.transpose(0, 1).numpy()
        sf.write(path, audio_np, sample_rate, subtype="PCM_16")
        LOGGER.info("Saved audio with soundfile: %s", path)
        return
    except Exception as exc:
        save_errors.append(f"soundfile: {_short_exc(exc)}")
        LOGGER.warning("Audio save failed (soundfile): %s", _short_exc(exc))

    for backend in ("soundfile", "sox", "ffmpeg", None):
        try:
            if backend is None:
                torchaudio.save(path, audio, sample_rate)
                LOGGER.info("Saved audio with default backend: %s", path)
            else:
                torchaudio.save(path, audio, sample_rate, backend=backend)
                LOGGER.info("Saved audio with backend=%s: %s", backend, path)
            return
        except Exception as exc:
            short = _short_exc(exc)
            save_errors.append(f"backend={backend}: {short}")
            LOGGER.warning("Audio save failed (backend=%s): %s", backend, short)
            if "torchcodec" in str(exc).lower() or "libtorchcodec" in str(exc).lower():
                LOGGER.warning("TorchCodec backend unavailable; stopping torchaudio backend probing.")
                break

    raise RuntimeError(
        "Failed to save audio with all backends. "
        + " | ".join(save_errors)
    )


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac", ".wma"}


def is_audio_file(path: str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


# ---------------------------------------------------------------------------
# Upsampler singleton (lazy‑loaded)
# ---------------------------------------------------------------------------
_upsampler = None


def get_upsampler(use_half: bool = True):
    """Load the model once and cache it."""
    global _upsampler
    if _upsampler is None:
        LOGGER.info("Initializing FastSR (half=%s)", use_half)
        from NovaSR import FastSR
        _upsampler = FastSR(half=use_half, require_gpu=False)
        LOGGER.info("FastSR initialized successfully on device: %s", _upsampler.device)
    return _upsampler


def get_upsampler_with_mode(use_half: bool, require_gpu: bool):
    global _upsampler
    if _upsampler is None:
        LOGGER.info("Initializing FastSR (half=%s, require_gpu=%s)", use_half, require_gpu)
        from NovaSR import FastSR
        _upsampler = FastSR(half=use_half, require_gpu=require_gpu)
        LOGGER.info("FastSR initialized successfully on device: %s", _upsampler.device)
    else:
        if require_gpu and getattr(_upsampler, "device", torch.device("cpu")).type != "cuda":
            raise RuntimeError(
                "GPU is required, but current model instance is on CPU. Restart app after installing CUDA-enabled PyTorch."
            )
    return _upsampler


def process_file(input_path: str, output_path: str, use_half: bool = True):
    """Run NovaSR super‑resolution on a single audio file and save as 48 kHz WAV."""
    import torchaudio

    sr = get_upsampler(use_half)
    lowres = sr.load_audio(input_path)
    highres = sr.infer(lowres).cpu()
    safe_audio_save(output_path, highres, 48000)


def run_sr_once(waveform: torch.Tensor, sample_rate: int, use_half: bool) -> torch.Tensor:
    """Run one SR pass from arbitrary sample rate/tensor to 48k output tensor."""
    sr = get_upsampler(use_half)
    LOGGER.info("Running SR pass: input_sr=%s, input_shape=%s", sample_rate, tuple(waveform.shape))
    audio = waveform[:1, :]
    lowres = torchaudio.functional.resample(
        audio, sample_rate, 16000, resampling_method="kaiser_window"
    ).unsqueeze(1).to(sr.device)
    if sr.half:
        lowres = lowres.half()
    highres = sr.infer(lowres).cpu()
    LOGGER.info("SR pass complete: output_shape=%s", tuple(highres.shape))
    return torch.clamp(highres, -1.0, 1.0)


def apply_profile(waveform: torch.Tensor, sample_rate: int, do_denoise: bool, do_eq: bool) -> torch.Tensor:
    """Apply lightweight denoise and/or post-EQ profile to waveform [1, T]."""
    audio = waveform
    LOGGER.info("Applying profile: denoise=%s, eq=%s, sr=%s", do_denoise, do_eq, sample_rate)

    if do_denoise:
        x = audio.squeeze(0)
        n_fft = 1024
        hop = 256
        window = torch.hann_window(n_fft)
        spec = torch.stft(x, n_fft=n_fft, hop_length=hop, window=window, return_complex=True)
        mag = spec.abs()
        phase = torch.angle(spec)
        noise_frames = max(4, min(24, mag.shape[1] // 20 if mag.shape[1] > 0 else 4))
        noise_floor = mag[:, :noise_frames].median(dim=1, keepdim=True).values
        threshold = noise_floor * 1.5
        gate = torch.sigmoid((mag - threshold) * 10.0)
        mag_denoised = mag * (0.2 + 0.8 * gate)
        spec_denoised = torch.polar(mag_denoised, phase)
        x = torch.istft(spec_denoised, n_fft=n_fft, hop_length=hop, window=window, length=x.shape[-1])
        audio = x.unsqueeze(0)

    if do_eq:
        low = torchaudio.functional.lowpass_biquad(audio, sample_rate, cutoff_freq=3000)
        high = audio - low
        audio = audio + 0.18 * high

    return torch.clamp(audio, -1.0, 1.0)


def run_compounded_sr(
    input_path: str,
    cycles: int,
    use_half: bool,
    process_between_cycles: bool,
    do_denoise: bool,
    do_eq: bool,
) -> tuple[torch.Tensor, int]:
    """Run NovaSR repeatedly for N cycles; optionally profile between each cycle."""
    waveform, sample_rate = safe_torchaudio_load(input_path)
    LOGGER.info(
        "Starting compounded SR: file=%s, cycles=%s, between_cycles=%s, denoise=%s, eq=%s",
        input_path,
        cycles,
        process_between_cycles,
        do_denoise,
        do_eq,
    )
    waveform = waveform[:1, :]
    current = waveform
    current_sr = sample_rate

    for idx in range(cycles):
        LOGGER.info("Cycle %s/%s", idx + 1, cycles)
        current = run_sr_once(current, current_sr, use_half)
        current_sr = 48000
        if process_between_cycles and idx < cycles - 1 and (do_denoise or do_eq):
            current = apply_profile(current, current_sr, do_denoise, do_eq)

    return current, current_sr


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class NovaSRApp(tk.Tk):
    BG = "#1e1e2e"
    FG = "#cdd6f4"
    ACCENT = "#89b4fa"
    ACCENT_HOVER = "#74c7ec"
    ENTRY_BG = "#313244"
    BTN_BG = "#45475a"

    def __init__(self):
        super().__init__()
        LOGGER.info("GUI startup")
        self.title("NovaSR  ·  Audio Super-Resolution")
        self.configure(bg=self.BG)
        self.resizable(False, False)
        self.geometry("700x660")
        self.preview_input_wav: str | None = None
        self.preview_output_wav: str | None = None
        self.latest_output_path: str | None = None
        self._tmp_preview_files: list[str] = []

        # ── Styles ──
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.BG)
        style.configure("TLabel", background=self.BG, foreground=self.FG, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.ACCENT)
        style.configure("Status.TLabel", font=("Segoe UI", 9), foreground="#a6adc8")
        style.configure("TCheckbutton", background=self.BG, foreground=self.FG, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", self.BG)])
        style.configure(
            "Accent.TButton",
            background=self.ACCENT,
            foreground="#1e1e2e",
            font=("Segoe UI", 11, "bold"),
            padding=(16, 8),
        )
        style.map("Accent.TButton", background=[("active", self.ACCENT_HOVER)])

        # ── Header ──
        ttk.Label(self, text="NovaSR", style="Header.TLabel").pack(pady=(18, 2))
        ttk.Label(self, text="16 kHz → 48 kHz audio upscaling  ·  ~52 KB model", style="Status.TLabel").pack()

        # ── File picker ──
        frame_file = ttk.Frame(self)
        frame_file.pack(fill="x", padx=28, pady=(18, 6))

        ttk.Label(frame_file, text="Input file(s):").pack(anchor="w")
        row = ttk.Frame(frame_file)
        row.pack(fill="x", pady=4)
        self.file_var = tk.StringVar()
        entry = tk.Entry(row, textvariable=self.file_var, bg=self.ENTRY_BG, fg=self.FG,
                         insertbackground=self.FG, relief="flat", font=("Segoe UI", 10))
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        browse_btn = tk.Button(row, text=" Browse… ", command=self._browse,
                               bg=self.BTN_BG, fg=self.FG, relief="flat", font=("Segoe UI", 9),
                               activebackground=self.ACCENT, activeforeground="#1e1e2e", cursor="hand2")
        browse_btn.pack(side="right", padx=(6, 0))

        # ── Output dir ──
        frame_out = ttk.Frame(self)
        frame_out.pack(fill="x", padx=28, pady=6)

        ttk.Label(frame_out, text="Output folder (blank = same as input):").pack(anchor="w")
        row2 = ttk.Frame(frame_out)
        row2.pack(fill="x", pady=4)
        self.out_var = tk.StringVar()
        entry2 = tk.Entry(row2, textvariable=self.out_var, bg=self.ENTRY_BG, fg=self.FG,
                          insertbackground=self.FG, relief="flat", font=("Segoe UI", 10))
        entry2.pack(side="left", fill="x", expand=True, ipady=4)
        out_btn = tk.Button(row2, text=" Browse… ", command=self._browse_out,
                            bg=self.BTN_BG, fg=self.FG, relief="flat", font=("Segoe UI", 9),
                            activebackground=self.ACCENT, activeforeground="#1e1e2e", cursor="hand2")
        out_btn.pack(side="right", padx=(6, 0))

        # ── Options ──
        frame_opts = ttk.Frame(self)
        frame_opts.pack(fill="x", padx=28, pady=6)
        self.half_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_opts, text="Use half-precision (GPU, faster)", variable=self.half_var).pack(anchor="w")

        row_cycles = ttk.Frame(frame_opts)
        row_cycles.pack(fill="x", pady=(8, 2))
        ttk.Label(row_cycles, text="Compounding cycles:").pack(side="left")
        self.cycles_var = tk.IntVar(value=1)
        self.cycles_spin = tk.Spinbox(
            row_cycles,
            from_=1,
            to=10,
            textvariable=self.cycles_var,
            width=6,
            bg=self.ENTRY_BG,
            fg=self.FG,
            insertbackground=self.FG,
            relief="flat",
            font=("Segoe UI", 10),
        )
        self.cycles_spin.pack(side="left", padx=(8, 0))

        self.denoise_var = tk.BooleanVar(value=False)
        self.eq_var = tk.BooleanVar(value=False)
        self.between_cycles_var = tk.BooleanVar(value=False)
        self.dual_output_var = tk.BooleanVar(value=True)
        self.require_gpu_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_opts, text="Denoise profile", variable=self.denoise_var).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(frame_opts, text="Post-EQ profile", variable=self.eq_var).pack(anchor="w")
        ttk.Checkbutton(
            frame_opts,
            text="Apply profile between cycles (for compounding pipeline)",
            variable=self.between_cycles_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            frame_opts,
            text="Dual output mode (save raw + profile when profile enabled)",
            variable=self.dual_output_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            frame_opts,
            text="Require GPU (fail if CUDA unavailable)",
            variable=self.require_gpu_var,
        ).pack(anchor="w")

        # ── A/B Preview ──
        frame_preview = ttk.Frame(self)
        frame_preview.pack(fill="x", padx=28, pady=(8, 4))
        ttk.Label(frame_preview, text="A/B Preview:").pack(anchor="w")

        self.preview_mode_var = tk.StringVar(value="input")
        row_preview = ttk.Frame(frame_preview)
        row_preview.pack(fill="x", pady=(4, 0))
        ttk.Radiobutton(row_preview, text="Input (A)", value="input", variable=self.preview_mode_var).pack(side="left")
        ttk.Radiobutton(row_preview, text="Output (B)", value="output", variable=self.preview_mode_var).pack(side="left", padx=(10, 0))

        row_preview_btns = ttk.Frame(frame_preview)
        row_preview_btns.pack(fill="x", pady=(4, 0))
        ttk.Button(row_preview_btns, text="▶ Play", command=self._preview_play).pack(side="left")
        ttk.Button(row_preview_btns, text="■ Stop", command=self._preview_stop).pack(side="left", padx=(8, 0))
        ttk.Button(row_preview_btns, text="📂 Open Output", command=self._open_latest_output).pack(side="left", padx=(8, 0))

        # ── Progress ──
        self.progress = ttk.Progressbar(self, mode="determinate", length=500)
        self.progress.pack(padx=28, pady=(12, 4))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, style="Status.TLabel").pack()

        # ── Run button ──
        self.run_btn = ttk.Button(self, text="⚡  Upscale", style="Accent.TButton", command=self._start)
        self.run_btn.pack(pady=(14, 18))

        # ── Drag & drop hint ──
        ttk.Label(self, text="Tip: You can also right-click audio files → 'Upscale with NovaSR'",
                  style="Status.TLabel").pack(pady=(0, 8))

        # Handle CLI args (for context‑menu integration)
        if len(sys.argv) > 1:
            files = [f for f in sys.argv[1:] if is_audio_file(f)]
            if files:
                self.file_var.set("; ".join(files))
                LOGGER.info("Loaded CLI/context-menu files: %s", files)

        self.after(150, self._startup_self_check)

    # ── Callbacks ──
    def _browse(self):
        paths = filedialog.askopenfilenames(
            title="Select audio files",
            filetypes=[("Audio files", " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)), ("All files", "*.*")],
        )
        if paths:
            self.file_var.set("; ".join(paths))

    def _browse_out(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.out_var.set(d)

    def _start(self):
        raw = self.file_var.get().strip()
        LOGGER.info("Start requested. Raw input field: %s", raw)
        if not raw:
            self.status_var.set("⚠  No files selected")
            return
        files = [f.strip().strip('"') for f in raw.split(";") if f.strip()]
        files = [f for f in files if os.path.isfile(f)]
        if not files:
            self.status_var.set("⚠  No valid files found")
            LOGGER.warning("No valid files resolved from input")
            return
        LOGGER.info("Resolved files to process: %s", files)
        self.run_btn.configure(state="disabled")
        threading.Thread(target=self._process, args=(files,), daemon=True).start()

    def _prepare_preview_wav(self, source_path: str, prefix: str) -> str:
        LOGGER.info("Preparing preview WAV: source=%s, prefix=%s", source_path, prefix)
        path = Path(source_path)
        if path.suffix.lower() == ".wav":
            return str(path)
        waveform, sample_rate = safe_torchaudio_load(str(path))
        waveform = waveform[:1, :]
        tmp = tempfile.NamedTemporaryFile(prefix=f"novasr_{prefix}_", suffix=".wav", delete=False)
        tmp.close()
        safe_audio_save(tmp.name, waveform, sample_rate)
        self._tmp_preview_files.append(tmp.name)
        LOGGER.info("Created temp preview WAV: %s", tmp.name)
        return tmp.name

    def _startup_self_check(self):
        self._set_status("Running startup self-check…")
        LOGGER.info("Startup self-check: begin")
        LOGGER.info(
            "Torch runtime: version=%s, torch_cuda=%s, cuda_available=%s, cuda_devices=%s",
            torch.__version__,
            torch.version.cuda,
            torch.cuda.is_available(),
            torch.cuda.device_count(),
        )
        if torch.cuda.is_available():
            try:
                gpu_name = torch.cuda.get_device_name(0)
                LOGGER.info("Detected GPU: %s", gpu_name)
            except Exception:
                LOGGER.exception("Unable to query CUDA device name")
        else:
            LOGGER.warning("CUDA unavailable to PyTorch. If you have an NVIDIA GPU, install CUDA-enabled torch build.")

        try:
            probe = torch.zeros((1, 1600), dtype=torch.float32)
            tmp = tempfile.NamedTemporaryFile(prefix="novasr_probe_", suffix=".wav", delete=False)
            tmp.close()
            safe_audio_save(tmp.name, probe, 16000)
            w, s = safe_torchaudio_load(tmp.name)
            os.unlink(tmp.name)
            LOGGER.info("Startup self-check: PASS (shape=%s, sr=%s)", tuple(w.shape), s)
            self._set_status("Ready")
        except Exception:
            LOGGER.exception("Startup self-check: FAIL")
            self._set_status("⚠ Startup self-check failed. See novasr_gui.log")

    def _preview_play(self):
        if os.name != "nt":
            self._set_status("⚠ Preview playback is currently enabled for Windows only")
            return
        self._preview_stop()
        selected = self.preview_mode_var.get()
        path = self.preview_input_wav if selected == "input" else self.preview_output_wav
        if not path or not os.path.isfile(path):
            self._set_status("⚠ No preview file available yet")
            return
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            self._set_status(f"▶ Playing {selected} preview")
            LOGGER.info("Playing preview: mode=%s, file=%s", selected, path)
        except Exception as exc:
            LOGGER.exception("Preview playback failed")
            self._set_status(f"✗ Preview playback failed: {exc}")

    def _preview_stop(self):
        if os.name == "nt":
            winsound.PlaySound(None, winsound.SND_PURGE)

    def _open_latest_output(self):
        path = self.latest_output_path
        if not path or not os.path.exists(path):
            self._set_status("⚠ No output file available yet")
            return

        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
            LOGGER.info("Opened output file: %s", path)
        except Exception as exc:
            LOGGER.exception("Open output failed")
            self._set_status(f"✗ Could not open output: {exc}")

    def _process(self, files: list[str]):
        total = len(files)
        out_dir = self.out_var.get().strip() or None

        self.progress["maximum"] = total
        self.progress["value"] = 0

        use_half = self.half_var.get()
        cycles = max(1, int(self.cycles_var.get()))
        do_denoise = self.denoise_var.get()
        do_eq = self.eq_var.get()
        process_between = self.between_cycles_var.get()
        dual_output = self.dual_output_var.get()
        require_gpu = self.require_gpu_var.get()
        LOGGER.info(
            "Process settings: use_half=%s, cycles=%s, denoise=%s, eq=%s, between_cycles=%s, dual_output=%s, require_gpu=%s",
            use_half,
            cycles,
            do_denoise,
            do_eq,
            process_between,
            dual_output,
            require_gpu,
        )

        # Load model (show status)
        self._set_status("Loading model…")
        try:
            get_upsampler_with_mode(use_half, require_gpu)
        except Exception as exc:
            LOGGER.exception("Model load failed")
            self._set_status(f"✗ Model load failed: {exc}")
            self.after(0, lambda: self.run_btn.configure(state="normal"))
            return

        for i, fpath in enumerate(files, 1):
            name = Path(fpath).stem
            dest_dir = out_dir or str(Path(fpath).parent)
            out_path = os.path.join(dest_dir, f"{name}_48kHz.wav")
            profile_path = os.path.join(dest_dir, f"{name}_48kHz_profile.wav")
            LOGGER.info("Processing file %s/%s: %s", i, total, fpath)

            self._set_status(f"Processing {i}/{total}: {Path(fpath).name} (cycles={cycles})")
            try:
                raw_audio, raw_sr = run_compounded_sr(
                    fpath,
                    cycles=cycles,
                    use_half=use_half,
                    process_between_cycles=process_between,
                    do_denoise=do_denoise,
                    do_eq=do_eq,
                )
                profiled_audio = apply_profile(raw_audio, raw_sr, do_denoise, do_eq) if (do_denoise or do_eq) else None

                if do_denoise or do_eq:
                    if dual_output:
                        safe_audio_save(out_path, raw_audio, raw_sr)
                        safe_audio_save(profile_path, profiled_audio, raw_sr)
                        primary_for_preview = profile_path
                    else:
                        safe_audio_save(out_path, profiled_audio, raw_sr)
                        primary_for_preview = out_path
                else:
                    safe_audio_save(out_path, raw_audio, raw_sr)
                    primary_for_preview = out_path

                self.preview_input_wav = self._prepare_preview_wav(fpath, "input")
                self.preview_output_wav = self._prepare_preview_wav(primary_for_preview, "output")
                self.latest_output_path = primary_for_preview
                LOGGER.info(
                    "File complete. raw_out=%s, profile_out=%s, raw_sr=%s",
                    out_path,
                    profile_path if (do_denoise or do_eq) and dual_output else "n/a",
                    raw_sr,
                )
            except Exception as exc:
                LOGGER.exception("Processing failed for file: %s", fpath)
                self._set_status(f"✗ Error on {Path(fpath).name}: {exc}")
                continue

            self.after(0, lambda v=i: self.progress.configure(value=v))

        details = ""
        if do_denoise or do_eq:
            details = " with profile"
            if dual_output:
                details += " (dual output)"
        self._set_status(f"✓ Done — {total} file(s) processed at 48 kHz{details}")
        LOGGER.info("Batch complete: total=%s%s", total, details)
        self.after(0, lambda: self.run_btn.configure(state="normal"))

    def _set_status(self, msg: str):
        self.after(0, lambda: self.status_var.set(msg))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    LOGGER.info("Launching NovaSR GUI app. Log path: %s", LOG_PATH)
    app = NovaSRApp()
    app.mainloop()
