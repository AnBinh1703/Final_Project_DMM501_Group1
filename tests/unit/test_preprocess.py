import numpy as np

from src.features.preprocess import preprocess_feature_vector


def test_preprocess_feature_vector_shape() -> None:
    x = preprocess_feature_vector([1.0, 2.0, 3.0])
    assert isinstance(x, np.ndarray)
    assert x.shape == (1, 3)
