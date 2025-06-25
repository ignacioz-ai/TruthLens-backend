# TruthLens Backend

## Environment Setup

### Option 1: Using the startup script (Recommended)
1. Simply double-click on `start_server.bat`
2. The server will start automatically on port 5000

### Option 2: Manual virtual environment activation
1. Open a terminal in the `backend` folder
2. Activate the virtual environment:
   ```bash
   # On Windows:
   .\venv\Scripts\activate
   
   # On Unix/MacOS:
   source venv/bin/activate
   ```
3. Start the server:
   ```bash
   python main.py
   ```

## Verification
- The server will be available at: http://localhost:5000
- API documentation will be at: http://localhost:5000/docs
- Health endpoint will be at: http://localhost:5000/api/v1/health

## Notes
- Make sure you have a `.env` file with the necessary variables
- The server must be running for the frontend to work properly
- If you see connection errors, verify that the server is running on port 5000

## API Documentation

Once the server is running, you can access:
- Interactive API docs (Swagger UI): `http://localhost:8000/docs`
- Alternative API docs (ReDoc): `http://localhost:8000/redoc`

## API Endpoints

### POST /api/analyze
Analyzes a text for bias and factual accuracy.

Request body:
```json
{
    "input_text": "Your text to analyze here..."
}
```

Response:
```json
{
    "factual_accuracy": 82,
    "bias": "neutral",
    "emotional_tone": "measured",
    "recommendation": "This article appears balanced. Consider checking the sources to confirm accuracy."
}
``` 