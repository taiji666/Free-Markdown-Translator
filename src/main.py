from fastapi import FastAPI, UploadFile, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import shutil
import os
from pathlib import Path
from datetime import datetime
from MD.MDUtils import MDTranslate,MDAnalysis
app = FastAPI(debug=True)
# 获取当前文件所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=os.path.join(current_dir,"static")), name="static")

# 设置模板目录
templates = Jinja2Templates(directory=os.path.join(current_dir,"templates"))

# 创建上传文件保存的目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )


@app.post("/upload")
async def upload_file(file: UploadFile):
    try:
        # 生成唯一的文件名
        UPLOAD_DIR = Path("uploads")
        UPLOAD_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = file.filename
        new_filename = f"{timestamp}_{original_filename}"
        file_path = UPLOAD_DIR / new_filename

        # 保存上传的文件
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 处理文本文件（这里示例为将文本转换为大写）
        # with open(file_path, "r", encoding="utf-8") as f:
        #     content = f.read().upper()
        doc = MDTranslate(file_path)
        raw_data = await MDAnalysis(doc.src_file).parse()
        await doc.translate(raw_data)
        print(doc.target_files)
        # 保存处理后的文件
        # processed_filename = f"processed_{new_filename}"
        # processed_path = UPLOAD_DIR / processed_filename
        # with open(processed_path, "w", encoding="utf-8") as f:
        #     f.write(content)
        # for doc in doc.target_files:
        #
        #     return await FileResponse(
        #         path=doc,
        #         filename=doc.name,
        #         media_type="text/plain"
        #     )
        doc=doc.target_files[0]
        print(doc)
        print(doc.name)
        return  FileResponse(
            path=doc,
            filename=doc.name,
            media_type="text/plain"
        )

    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)