from typing import Any, Tuple
from sklearn.model_selection import train_test_split

def split_dataset(X: Any, y: Any, test_size: float = 0.2, random_state: int = 42) -> Tuple[Any, Any, Any, Any]:
    """
    Common utility wrapper for dividing datasets into train and test splits,
    ensuring consistent seeds and API structures across all model developments.
    """
    return train_test_split(X, y, test_size=test_size, random_state=random_state)
