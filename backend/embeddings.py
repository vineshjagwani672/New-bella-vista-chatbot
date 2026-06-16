import hashlib
import math
import re
from typing import List

from langchain_core.embeddings import Embeddings


class LocalHashEmbeddings(Embeddings):
    def __init__(self, size: int = 384):
        self.size = size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self.size
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())

        for word in words:
            digest = hashlib.md5(word.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % self.size
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[index] += sign

        length = math.sqrt(sum(value * value for value in vector))
        if length == 0:
            return vector

        return [value / length for value in vector]
