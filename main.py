import os
import shutil
import subprocess
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vocal Remover API")

# Website Frontend ကနေ လှမ်းခေါ်လို့ရအောင် CORS ခွင့်ပြုပေးခြင်း
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "online", "message": "Vocal Remover API is running!"}

@app.post("/remove-vocals/")
async def remove_vocals(file: UploadFile = File(...)):
    # 1. Upload ဖိုင်ကို ယာယီသိမ်းဆည်းခြင်း
    input_path = f"temp_{file.filename}"
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    output_dir = "output"
    
    try:
        # 2. Demucs CLI ကို RAM စားသက်သာစေရန် Options များနှင့် ခေါ်ယူခြင်း
        cmd = [
            "demucs",
            "-n", "htdemucs",
            "--two-stems", "vocals",
            "--segment", "2",
            "--shifts", "0",
            input_path,
            "-o", output_dir
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Demucs Error: {result.stderr}")
        
        # 3. ထွက်လာသော Instrumental ဖိုင် လမ်းကြောင်းကို ရှာခြင်း
        filename_without_ext = os.path.splitext(file.filename)[0]
        instrumental_path = os.path.join(output_dir, "htdemucs", filename_without_ext, "no_vocals.wav")
        
        if not os.path.exists(instrumental_path):
            raise HTTPException(status_code=500, detail="Instrumental file output not found.")
        
        # 4. Instrumental ဖိုင်ကို Frontend သို့ ပြန်လည် ပေးပို့ခြင်း
        return FileResponse(
            path=instrumental_path,
            media_type="audio/wav",
            filename=f"instrumental_{filename_without_ext}.wav"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # 5. ယာယီသုံးထားသော Input ဖိုင်ကို ဖျက်ဆီးခြင်း
        if os.path.exists(input_path):
            os.remove(input_path)
