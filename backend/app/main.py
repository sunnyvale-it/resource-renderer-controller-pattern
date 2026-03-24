from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas, database
from .database import engine

# In a pure PoC avoiding alembic migrations, auto-create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resource Renderer Controller API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For PoC purposes only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/appconfigs/", response_model=schemas.AppConfig)
def create_appconfig(appconfig: schemas.AppConfigCreate, db: Session = Depends(database.get_db)):
    db_config = models.AppConfig(**appconfig.model_dump())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@app.get("/appconfigs/", response_model=List[schemas.AppConfig])
def read_appconfigs(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    return db.query(models.AppConfig).offset(skip).limit(limit).all()

@app.get("/appconfigs/{config_id}", response_model=schemas.AppConfig)
def read_appconfig(config_id: int, db: Session = Depends(database.get_db)):
    db_config = db.query(models.AppConfig).filter(models.AppConfig.id == config_id).first()
    if db_config is None:
        raise HTTPException(status_code=404, detail="AppConfig not found")
    return db_config

@app.put("/appconfigs/{config_id}", response_model=schemas.AppConfig)
def update_appconfig(config_id: int, appconfig: schemas.AppConfigUpdate, db: Session = Depends(database.get_db)):
    db_config = db.query(models.AppConfig).filter(models.AppConfig.id == config_id).first()
    if db_config is None:
        raise HTTPException(status_code=404, detail="AppConfig not found")
    
    update_data = appconfig.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_config, key, value)
        
    db.commit()
    db.refresh(db_config)
    return db_config

@app.delete("/appconfigs/{config_id}")
def delete_appconfig(config_id: int, db: Session = Depends(database.get_db)):
    db_config = db.query(models.AppConfig).filter(models.AppConfig.id == config_id).first()
    if db_config is None:
        raise HTTPException(status_code=404, detail="AppConfig not found")
    
    db.delete(db_config)
    db.commit()
    return {"ok": True}
