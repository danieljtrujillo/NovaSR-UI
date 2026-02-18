import torch
import os
import torchaudio
import soundfile as sf
from .speechsr import SynthesizerTrn


def _safe_load_audio(audio_file):
    load_errors = []
    try:
        audio_np, sample_rate = sf.read(audio_file, always_2d=True, dtype="float32")
        audio = torch.from_numpy(audio_np).transpose(0, 1)
        return audio, sample_rate
    except Exception as exc:
        load_errors.append(f"soundfile: {exc}")

    for backend in ("soundfile", "sox", "ffmpeg", None):
        try:
            if backend is None:
                return torchaudio.load(audio_file)
            return torchaudio.load(audio_file, backend=backend)
        except Exception as exc:
            load_errors.append(f"backend={backend}: {exc}")
    raise RuntimeError(
        "Failed to load audio with all torchaudio backends. "
        + " | ".join(load_errors)
    )

class FastSR:
    def __init__(self, ckpt_path=None, half=True, require_gpu=False):
        
        cuda_available = torch.cuda.is_available()
        torch_cuda = torch.version.cuda

        if require_gpu and not cuda_available:
            raise RuntimeError(
                "GPU is required but unavailable. "
                f"torch={torch.__version__}, torch_cuda={torch_cuda}, "
                "cuda_available=False. "
                "This usually means a CPU-only PyTorch build is installed."
            )

        self.device = torch.device('cuda' if cuda_available else 'cpu')
        self.hps = {
            "train": {
                "segment_size": 9600
            },
            "data": {
                "hop_length": 320,
                "n_mel_channels": 128
            },
            "model": {
                "resblock": "0",
                "resblock_kernel_sizes": [11],
                "resblock_dilation_sizes": [[1,3,5]],
                "upsample_initial_channel": 32,
            }
        }
        if ckpt_path is None:
            from huggingface_hub import snapshot_download
            model_path = snapshot_download("YatharthS/NovaSR")
            ckpt_path = f"{model_path}/pytorch_model_v1.bin"

        # Load model in float32 precision first
        self.model = self._load_model(ckpt_path).eval().float()
        
        # Optionally convert to half-precision if on GPU
        self.half = False
        if half and self.device.type == 'cuda':
            self.half = True
            self.model.half()


    def _load_model(self, ckpt_path):
        model = SynthesizerTrn(
            self.hps['data']['n_mel_channels'],
            self.hps['train']['segment_size'] // self.hps['data']['hop_length'],
            **self.hps['model']
        ).to(self.device)
        if not os.path.isfile(ckpt_path):
            raise FileNotFoundError(
                f"Model checkpoint not found at: {ckpt_path}. "
                "Please check that the model was downloaded correctly."
            )
        checkpoint_dict = torch.load(ckpt_path, map_location='cpu')
        model.dec.remove_weight_norm()
        model.load_state_dict(checkpoint_dict, strict=True)
        model.eval()
        return model

    def load_audio(self, audio_file):
        audio, sample_rate = _safe_load_audio(audio_file)
        audio = audio[:1, :]
        lowres_wav = torchaudio.functional.resample(audio, sample_rate, 16000, resampling_method="kaiser_window").unsqueeze(1).to(self.device)
        if self.half == True:
            lowres_wav = lowres_wav.half()
        return lowres_wav
        
    def infer(self, lowres_wav):
        with torch.no_grad():
            new_wav = self.model(lowres_wav)

        return new_wav.squeeze(0)

        
