from fastapi import FastAPI
import random

app = FastAPI()

# Root endpoint
@app.get("/")
def root():
    return {"message": "Welcome to the ScaleNow API"}

# Prediction endpoint
@app.get("/predict")
def predict():
    prediction_value = random.randint(0, 100)
    return {"prediction": f"The predicted value is {prediction_value}"}

