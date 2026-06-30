from fastapi import FastAPI, UploadFile, File
from reader import AthenaReader

app = FastAPI(
    title="Athena Core API",
    version="0.1"
)

reader = AthenaReader()


@app.get("/")
def root():

    return {
        "status": "Athena is alive"
    }


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):

    contents = await file.read()

    temp_file = f"temp_{file.filename}"

    with open(temp_file, "wb") as f:
        f.write(contents)

    text = reader.read(temp_file)

    return {
        "filename": file.filename,
        "characters": len(text),
        "preview": text[:1000]
    }