from collections import deque
from datetime import datetime
import time
from pathlib import Path
from typing import Union
import os
import logging
import requests
import librosa
import numpy as np
import sounddevice as sd
from scipy.spatial import distance
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    filename="coffee_machine.logs",
    filemode='a',
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    level=20  # INFO
)
logger = logging.getLogger()


class AudioHandler:
    def __init__(self) -> None:
        self.DIST_THRESHOLD = 85
        self.sr = 44100
        self.sec = 0.7
        self.coffee_machine_mfcc, _ = self._set_coffee_machine_features()
        sd.default.device = os.getenv("SD_DEFAULT_DEVICE")

    def start_detection(self) -> None:
        """
        Start listening the environment and if the euclidean distance 3 times less than the threshold
        then count it as coffee machine sound
        """
        logger.info("Listening...")
        logger.info(f"sampling rate: {self.sr}")
        logger.info(sd.query_devices())

        d = deque([500, 500, 500], 3)
        timeout = 12 * 60 * 60  # [seconds]
        timeout_start = time.time()

        while time.time() < timeout_start + timeout:
            sound_record = sd.rec(
                int(self.sec * self.sr),
                samplerate=self.sr,
                channels=1,
                dtype="float32",
                blocking=True,
            ).flatten()

            mfcc_features = self._compute_mean_mfcc(
                sound_record, self.sr
            )
            score = distance.euclidean(self.coffee_machine_mfcc, mfcc_features)
            d.appendleft(score)
            if np.max(d) < self.DIST_THRESHOLD:
                logger.info("coffee machine")
                logger.info(d)
                self.send_api_request()
                time.sleep(43)
                d = deque([500, 500, 500], 3)
                logger.info("start listening again..")
            # print(d)
        logger.info("End of the day, code run successfully ..")

    def _set_coffee_machine_features(self) -> Union[np.array, int]:
        coffee_machine_audio, sr = librosa.load(
            os.getenv("COFFEE_AUDIO_PATH"),
            sr=self.sr
        )
        coffee_machine_audio = coffee_machine_audio[:int(self.sec * self.sr)]
        coffee_machine_mfcc = self._compute_mean_mfcc(coffee_machine_audio, sr)
        return coffee_machine_mfcc, sr

    @staticmethod
    def _compute_mean_mfcc(audio, sr, dtype="float32"):
        mfcc_features = librosa.feature.mfcc(audio, sr=sr, dtype=dtype, n_mfcc=20)
        return np.mean(mfcc_features, axis=1)

    @staticmethod
    def send_api_request():
        logger.info("sending API request")
        requests.post(url = os.getenv("API_URL"), data = {'api_key': os.getenv("API_KEY")})

if __name__ == '__main__':
    AudioHandler().start_detection()
