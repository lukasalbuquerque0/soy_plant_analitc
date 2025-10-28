from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
# ✅ CORREÇÃO FINAL: Usamos a importação relativa (..) que o Python espera para um módulo pai.
from ..database import Base 
from datetime import datetime

class Utilizador(Base):
    __tablename__ = "utilizadores"
    # Permite a redefinição devido ao ciclo de importação
    __table_args__ = {'extend_existing': True} 

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # Relação com Analise
    analises = relationship("Analise", back_populates="utilizador")

class Analise(Base):
    __tablename__ = "analises"
    
    # Permite a redefinição devido ao ciclo de importação
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    utilizador_id = Column(Integer, ForeignKey("utilizadores.id"), nullable=False)
    nome_arquivo_original = Column(String, nullable=False)
    video_salvo_em = Column(String, unique=True, nullable=False)
    
    data_analise = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    contagem_total_unicos = Column(Integer, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    local_texto = Column(String, nullable=True)

    utilizador = relationship("Utilizador", back_populates="analises")
