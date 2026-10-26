import tempfile
import unittest
import wave
from pathlib import Path
import numpy as np
from music_cpu import render_sequence

class IslamicMusicTests(unittest.TestCase):
    def test_documentary_bed_is_finite_faded_stereo_and_avoids_sub_bass_drone(self):
        sequence={'totalQuantizedSteps':64,'notes':[
            {'pitch':60+i,'quantizedStartStep':i*4,'quantizedEndStep':i*4+2} for i in range(16)]}
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'music.wav'
            seconds=render_sequence(sequence,target,seed=76)
            with wave.open(str(target)) as source:
                self.assertEqual((source.getnchannels(),source.getframerate()),(2,48000))
                audio=np.frombuffer(source.readframes(source.getnframes()),dtype='<i2').reshape(-1,2)/32768
            self.assertAlmostEqual(len(audio)/48000,seconds,places=3)
            self.assertTrue(np.isfinite(audio).all())
            self.assertLess(np.max(np.abs(audio)),.56)
            self.assertLess(np.max(np.abs(audio[[0,-1]])),.001)
            section=audio[5*48000:9*48000,0]
            power=np.abs(np.fft.rfft(section))**2
            frequency=np.fft.rfftfreq(len(section),1/48000)
            self.assertLess(power[frequency<150].sum()/power.sum(),.4)

    def test_fresh_arrangements_differ_and_saved_seed_reproduces_audio(self):
        sequence = {'totalQuantizedSteps': 64, 'notes': [
            {'pitch': 64, 'quantizedStartStep': i*4, 'quantizedEndStep': i*4+3}
            for i in range(16)]}
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory)/f'{i}.wav' for i in range(3)]
            for path, seed in zip(paths, (101, 202, 101)):
                render_sequence(sequence, path, seed=seed)
            self.assertNotEqual(paths[0].read_bytes(), paths[1].read_bytes())
            self.assertEqual(paths[0].read_bytes(), paths[2].read_bytes())

    def test_empty_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            render_sequence({'totalQuantizedSteps':64,'notes':[]},Path('unused.wav'))
