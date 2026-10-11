"""Portable configured startup: python -m app.server (from backend/)."""
import uvicorn
from app.config import settings

def main():
    uvicorn.run('app.main:app',host=settings.host,port=settings.port)

if __name__=='__main__': main()
