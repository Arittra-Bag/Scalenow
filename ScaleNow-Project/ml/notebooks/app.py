from fastapi import FastAPI
import joblib

app = FastAPI()

# Load the model
model = joblib.load("model.pkl")

@app.post("/predict")
def predict(features: dict):
    prediction = model.predict([features["data"]])
    return {"prediction": prediction.tolist()}
