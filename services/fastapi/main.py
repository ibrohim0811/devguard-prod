from fastapi import FastAPI


app = FastAPI()


@app.get('/root/')
async def root():
    return {"status":"ok"}