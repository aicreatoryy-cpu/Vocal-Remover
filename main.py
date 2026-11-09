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
        # --segment 1 (သို့မဟုတ် 2) က RAM အများကြီးစားခြင်းကို ကာကွယ်ပေးသည်
        # --shifts 0 က processing အမြန်နှုန်းကို ပိုကောင်းစေသည်
        cmd = [
            "demucs",
            "-n", "htdemucs_s",  # htdemucs အစား ပိုပေါ့ပါးသော htdemucs_s (smaller model) ကို သုံးခြင်း
            "--two-stems", "vocals",
            "--segment", "2",
            "--shifts", "0",
            input_path,
            "-o", output_dir
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Demucs Error: {result.stderr}")
        
        # 3. ထွက်လာသော Instrumental ဖိုင် လမ်းကြောင်းကို ရှာခြင်း (htdemucs_s အတွက် folder နာမည် ပြောင်းလဲမှုကို ထည့်သွင်းခြင်း)
        filename_without_ext = os.path.splitext(file.filename)[0]
        instrumental_path = os.path.join(output_dir, "htdemucs_s", filename_without_ext, "no_vocals.wav")
        
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
