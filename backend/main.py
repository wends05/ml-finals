import cv2
import numpy as np
import base64
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# Allow Vite to send POST requests with JSON headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# This is our global state that the ESP32 constantly reads
kiosk_state = {
    "status": "waiting",
    "name": "Unknown",
    "confidence": 0.0
}

# Define the expected data structure from Vite
class ImageData(BaseModel):
    image: str

@app.post("/api/predict")
async def process_frame(data: ImageData):
    """Vite calls this 2-3 times a second with a base64 image."""
    global kiosk_state
    
    try:
        # 1. Clean the base64 string (remove "data:image/jpeg;base64,")
        encoded_data = data.image.split(',')[1]
        
        # 2. Decode the string into a numpy array
        nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        
        # 3. Convert the numpy array into an OpenCV BGR image
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # ---------------------------------------------------------
        # YOUR DEEP LEARNING MODEL GOES HERE
        # e.g., preprocessed_face = preprocess(frame)
        # prediction, confidence = custom_model.predict(preprocessed_face)
        # ---------------------------------------------------------
        
        # MOCK PREDICTION UPDATE (Replace with actual model logic)
        kiosk_state["status"] = "recognized"
        kiosk_state["name"] = "Student"
        kiosk_state["confidence"] = 0.95
        
        # Return the updated state back to Vite for the UI
        return kiosk_state
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/kiosk-status")
def get_kiosk_status():
    """ESP32 will instantly get the latest state from here."""
    return kiosk_state

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
