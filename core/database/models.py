#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Models
================
SQLite 数据库模型定义

使用 SQLAlchemy ORM 进行数据持久化
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime, 
    ForeignKey, Boolean, JSON, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class AnalysisSession(Base):
    """
    分析会话表
    
    每次上传数据并运行分析时创建一个会话
    """
    __tablename__ = 'analysis_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 会话元数据
    name = Column(String(255), nullable=True)  # 用户自定义名称
    description = Column(Text, nullable=True)
    source_files = Column(JSON, nullable=True)  # 源文件列表
    
    # 分析配置
    channel = Column(String(50), default='ratio')
    method = Column(String(50), default='auc')
    units = Column(String(20), default='calorie')
    
    # 关联的结果
    tm_results = relationship("TmResultRecord", back_populates="session", cascade="all, delete-orphan")
    thermo_result = relationship("ThermoResultRecord", back_populates="session", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AnalysisSession(id={self.id}, created_at={self.created_at}, name={self.name})>"


class TmResultRecord(Base):
    """
    Tm 分析结果表
    
    每个毛细管的 Tm 分析结果
    """
    __tablename__ = 'tm_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('analysis_sessions.id'), nullable=False)
    
    # 样品信息
    capillary_name = Column(String(255), nullable=False)
    concentration = Column(Float, nullable=True)  # 摩尔浓度
    source_file = Column(String(512), nullable=True)
    
    # Tm 结果
    tm = Column(Float, nullable=True)
    tm_error = Column(Float, nullable=True)
    r_squared = Column(Float, nullable=True)
    method = Column(String(50), nullable=False)
    
    # 质量指标
    quality_flag = Column(String(10), default='✓')
    snr = Column(Float, nullable=True)
    warnings = Column(JSON, nullable=True)
    
    # 进度曲线数据（用于热力学分析）
    progress_curve = Column(JSON, nullable=True)  # 存储为 JSON 数组
    progress_temperature = Column(JSON, nullable=True)
    
    # 关系
    session = relationship("AnalysisSession", back_populates="tm_results")
    
    def __repr__(self):
        return f"<TmResultRecord(id={self.id}, name={self.capillary_name}, tm={self.tm})>"


class ThermoResultRecord(Base):
    """
    热力学分析结果表
    
    Van't Hoff 分析结果
    """
    __tablename__ = 'thermo_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('analysis_sessions.id'), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Van't Hoff 参数
    delta_h = Column(Float, nullable=True)  # kJ/mol 或 kcal/mol
    delta_s = Column(Float, nullable=True)  # J/mol/K 或 cal/mol/K
    delta_h_error = Column(Float, nullable=True)
    delta_s_error = Column(Float, nullable=True)
    units = Column(String(20), default='calorie')
    
    # 拟合质量
    r_squared = Column(Float, nullable=True)
    n_points = Column(Integer, nullable=True)
    
    # 外推的 KD 值
    kd_298k = Column(Float, nullable=True)  # nM
    kd_310k = Column(Float, nullable=True)  # nM
    
    # 蛋白浓度（用于 EC50→KD 转换）
    protein_concentration = Column(Float, nullable=True)
    
    # 等温 EC50 数据（JSON 存储）
    ec50_data = Column(JSON, nullable=True)
    
    # ΔCp 相关（可选）
    delta_cp = Column(Float, nullable=True)
    delta_cp_fitted = Column(Boolean, default=False)
    
    # 关系
    session = relationship("AnalysisSession", back_populates="thermo_result")
    
    def __repr__(self):
        return f"<ThermoResultRecord(id={self.id}, delta_h={self.delta_h}, r2={self.r_squared})>"


# 数据库工具函数
def create_database(db_path: str = "quantdsf_history.db"):
    """
    创建数据库和所有表
    
    Args:
        db_path: 数据库文件路径
    
    Returns:
        engine, Session 对象
    """
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session


def get_session(db_path: str = "quantdsf_history.db"):
    """
    获取数据库会话
    
    Args:
        db_path: 数据库文件路径
    
    Returns:
        Session 实例
    """
    engine, Session = create_database(db_path)
    return Session()

