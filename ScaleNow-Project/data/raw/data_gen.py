from sklearn.datasets import make_regression

# Generate synthetic data for regression
X, y = make_regression(n_samples=1000, n_features=5, noise=0.1)

# Save as a DataFrame
import pandas as pd
data = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(5)])
data["target"] = y
print(data.head())
