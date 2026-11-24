import numpy as np

from claude_agent.audio import pcm
from claude_agent.audio.vad import EnergyVAD


def test_vad_detects_tone_and_hangover():
    v = EnergyVAD()
    assert not any(v.feed(pcm.silence(1.0, 16000)))
    act = v.feed(pcm.tone(220, 0.5, 16000, 0.3))
    assert act[-1] is True
    after = v.feed(pcm.silence(0.2, 16000))
    assert after[-1] is True                  # still within 450 ms hangover
    after = v.feed(pcm.silence(0.5, 16000))
    assert after[-1] is False


def test_vad_ignores_low_noise():
    rng = np.random.default_rng(0)
    noise = pcm.to_pcm((rng.standard_normal(16000) * 0.002).astype(np.float32))
    assert not any(EnergyVAD().feed(noise))


def test_resample_length_and_wav():
    x = pcm.tone(440, 1.0, 24000)
    y = pcm.resample(x, 24000, 16000)
    assert len(y) == 2 * 16000
    assert pcm.wav_bytes(y, 16000)[:4] == b"RIFF"
    assert len(pcm.envelope(y, 12)) == 12
    assert pcm.clipping_ratio(pcm.tone(440, 0.1, 16000, 1.2)) > 0.1
