# Clinical Trial Intelligence API

A FastAPI-based microservice providing multiple clinical-intelligence pipelines such as:

- Protocol Analyzer  
- Vendor Search  
- Document Comparison 

This document explains how to install **Python 3.11**, create your environment, install dependencies, and run the API server using `uvicorn`.

---

## 1. Install Python 3.11

### Windows
Download Python 3.11 installer:  
https://www.python.org/downloads/release/python-3110/

During installation:
- Check **“Add Python to PATH”**
- Continue with default options

### macOS (Homebrew)
```bash
brew install python@3.11
brew link python@3.11 --force
```

### Linux (Ubuntu / Debian)
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

### Verify installation:

```bash
python3.11 --version
```

## 2. Create Virtual Environment (Python 3.11)

### Inside project root:

```bash
python3.11 -m venv venv
```

### Activate environment:

#### Windows
```bash
venv\Scripts\activate
```

#### macOS / Linux
```bash
source venv/bin/activate
```

## 3. Install Dependencies

Ensure you are in the activated environment, then:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Run the FastAPI App with Uvicorn

The main application file is app.py.

Run using:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Options:

- --reload → auto-restart server on file changes (dev mode)
- --host 0.0.0.0 → accessible from network
- --port 8000 → change if needed

5. Test the API

After running uvicorn, open:

**Swagger UI**
```bash
http://localhost:8000/docs
```

**ReDoc**
```bash
http://localhost:8000/redoc
```

6. Project Structure
project/
│── app.py
│── requirements.txt
│── static/
│── temp/
│── data/
│── config/
      ├── config.py
│── src/
      ├── processes/
                ├── document_comparison/
                ├── protocol_analyzer/
                ├── vendor_search/
      ├── adapters/
      ├── prompts/
      ├── models.py
      ├── utils.py
      ├── utils_helper.py

7. Environment Deactivation
```bash
deactivate
```

8. Production Run

Without reload and using multiple workers:

```bash
uvicorn app:app --host 0.0.0.0 --port 80 --workers 4
```

Or behind Gunicorn:

```bash
gunicorn -k uvicorn.workers.UvicornWorker app:app --workers 4 --bind 0.0.0.0:80
```

### Notes

- Upload folder temp/ is auto-created
- All fallback JSONs live under static/
- Logging uses custom tracer (azure_tracer)
- Some endpoints have timeouts and built-in fallback static responses
