#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Repository
====================
数据库操作封装

提供简洁的 API 用于保存和查询分析结果
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

from .models import (
    AnalysisSession, TmResultRecord, ThermoResultRecord,
    create_database, get_session
)


class HistoryRepository:
    """
    历史记录仓库
    
    封装所有数据库操作，提供简洁的 API
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化仓库
        
        Args:
            db_path: 数据库路径，默认为用户目录下的 quantdsf_history.db
        """
        if db_path is None:
            # 默认存储在用户目录
            db_path = Path.home() / ".quantdsf" / "history.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_path = str(db_path)
        
        self.db_path = db_path
        self._engine, self._Session = create_database(db_path)
    
    def _get_session(self):
        """获取新的数据库会话"""
        return self._Session()
    
    # =========== 会话操作 ===========
    
    def create_session(
        self,
        name: str = None,
        description: str = None,
        source_files: List[str] = None,
        channel: str = 'ratio',
        method: str = 'auc',
        units: str = 'calorie'
    ) -> int:
        """
        创建新的分析会话
        
        Args:
            name: 会话名称
            description: 描述
            source_files: 源文件列表
            channel: 数据通道
            method: 分析方法
            units: 单位制
        
        Returns:
            新创建的会话 ID
        """
        session = self._get_session()
        try:
            analysis_session = AnalysisSession(
                name=name or f"Analysis {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                description=description,
                source_files=source_files,
                channel=channel,
                method=method,
                units=units
            )
            session.add(analysis_session)
            session.commit()
            return analysis_session.id
        finally:
            session.close()
    
    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话 ID
        
        Returns:
            会话信息字典
        """
        session = self._get_session()
        try:
            record = session.query(AnalysisSession).filter_by(id=session_id).first()
            if record:
                return {
                    'id': record.id,
                    'created_at': record.created_at.isoformat(),
                    'name': record.name,
                    'description': record.description,
                    'source_files': record.source_files,
                    'channel': record.channel,
                    'method': record.method,
                    'units': record.units,
                    'n_samples': len(record.tm_results),
                    'has_thermo': record.thermo_result is not None
                }
            return None
        finally:
            session.close()
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出最近的分析会话
        
        Args:
            limit: 最大返回数量
        
        Returns:
            会话列表
        """
        session = self._get_session()
        try:
            records = session.query(AnalysisSession)\
                .order_by(AnalysisSession.created_at.desc())\
                .limit(limit)\
                .all()
            
            return [{
                'id': r.id,
                'created_at': r.created_at.isoformat(),
                'name': r.name,
                'n_samples': len(r.tm_results),
                'method': r.method,
                'has_thermo': r.thermo_result is not None
            } for r in records]
        finally:
            session.close()
    
    def delete_session(self, session_id: int) -> bool:
        """
        删除分析会话及其所有关联数据
        
        Args:
            session_id: 会话 ID
        
        Returns:
            是否删除成功
        """
        session = self._get_session()
        try:
            record = session.query(AnalysisSession).filter_by(id=session_id).first()
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    # =========== Tm 结果操作 ===========
    
    def save_tm_results(
        self,
        session_id: int,
        results: List[Dict[str, Any]]
    ) -> int:
        """
        保存 Tm 分析结果
        
        Args:
            session_id: 会话 ID
            results: Tm 结果列表
        
        Returns:
            保存的记录数
        """
        session = self._get_session()
        try:
            count = 0
            for result in results:
                record = TmResultRecord(
                    session_id=session_id,
                    capillary_name=result.get('name', 'Unknown'),
                    concentration=result.get('concentration'),
                    source_file=result.get('source_file'),
                    tm=result.get('tm'),
                    tm_error=result.get('tm_error'),
                    r_squared=result.get('r_squared'),
                    method=result.get('method', 'auc'),
                    quality_flag=result.get('quality_flag', '✓'),
                    snr=result.get('snr'),
                    warnings=result.get('warnings'),
                    progress_curve=result.get('progress_curve'),
                    progress_temperature=result.get('progress_temperature')
                )
                session.add(record)
                count += 1
            
            session.commit()
            return count
        finally:
            session.close()
    
    def get_tm_results(self, session_id: int) -> List[Dict[str, Any]]:
        """
        获取会话的所有 Tm 结果
        
        Args:
            session_id: 会话 ID
        
        Returns:
            Tm 结果列表
        """
        session = self._get_session()
        try:
            records = session.query(TmResultRecord)\
                .filter_by(session_id=session_id)\
                .order_by(TmResultRecord.concentration.desc())\
                .all()
            
            return [{
                'id': r.id,
                'name': r.capillary_name,
                'concentration': r.concentration,
                'tm': r.tm,
                'tm_error': r.tm_error,
                'r_squared': r.r_squared,
                'method': r.method,
                'quality_flag': r.quality_flag,
                'snr': r.snr,
                'warnings': r.warnings,
                'progress_curve': r.progress_curve,
                'progress_temperature': r.progress_temperature
            } for r in records]
        finally:
            session.close()
    
    # =========== 热力学结果操作 ===========
    
    def save_thermo_result(
        self,
        session_id: int,
        result: Dict[str, Any]
    ) -> int:
        """
        保存热力学分析结果
        
        Args:
            session_id: 会话 ID
            result: 热力学结果字典
        
        Returns:
            记录 ID
        """
        session = self._get_session()
        try:
            # 检查是否已存在，存在则更新
            existing = session.query(ThermoResultRecord)\
                .filter_by(session_id=session_id).first()
            
            if existing:
                # 更新现有记录
                existing.delta_h = result.get('delta_h')
                existing.delta_s = result.get('delta_s')
                existing.delta_h_error = result.get('delta_h_error')
                existing.delta_s_error = result.get('delta_s_error')
                existing.units = result.get('units', 'calorie')
                existing.r_squared = result.get('r_squared')
                existing.n_points = result.get('n_points')
                existing.kd_298k = result.get('kd_298k')
                existing.kd_310k = result.get('kd_310k')
                existing.protein_concentration = result.get('protein_concentration')
                existing.ec50_data = result.get('ec50_data')
                existing.delta_cp = result.get('delta_cp')
                existing.delta_cp_fitted = result.get('delta_cp_fitted', False)
                session.commit()
                return existing.id
            else:
                # 创建新记录
                record = ThermoResultRecord(
                    session_id=session_id,
                    delta_h=result.get('delta_h'),
                    delta_s=result.get('delta_s'),
                    delta_h_error=result.get('delta_h_error'),
                    delta_s_error=result.get('delta_s_error'),
                    units=result.get('units', 'calorie'),
                    r_squared=result.get('r_squared'),
                    n_points=result.get('n_points'),
                    kd_298k=result.get('kd_298k'),
                    kd_310k=result.get('kd_310k'),
                    protein_concentration=result.get('protein_concentration'),
                    ec50_data=result.get('ec50_data'),
                    delta_cp=result.get('delta_cp'),
                    delta_cp_fitted=result.get('delta_cp_fitted', False)
                )
                session.add(record)
                session.commit()
                return record.id
        finally:
            session.close()
    
    def get_thermo_result(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        获取热力学分析结果
        
        Args:
            session_id: 会话 ID
        
        Returns:
            热力学结果字典
        """
        session = self._get_session()
        try:
            record = session.query(ThermoResultRecord)\
                .filter_by(session_id=session_id).first()
            
            if record:
                return {
                    'id': record.id,
                    'created_at': record.created_at.isoformat(),
                    'delta_h': record.delta_h,
                    'delta_s': record.delta_s,
                    'delta_h_error': record.delta_h_error,
                    'delta_s_error': record.delta_s_error,
                    'units': record.units,
                    'r_squared': record.r_squared,
                    'n_points': record.n_points,
                    'kd_298k': record.kd_298k,
                    'kd_310k': record.kd_310k,
                    'protein_concentration': record.protein_concentration,
                    'ec50_data': record.ec50_data,
                    'delta_cp': record.delta_cp,
                    'delta_cp_fitted': record.delta_cp_fitted
                }
            return None
        finally:
            session.close()
    
    # =========== 便捷方法 ===========
    
    def save_complete_analysis(
        self,
        name: str,
        source_files: List[str],
        tm_results: List[Dict[str, Any]],
        thermo_result: Optional[Dict[str, Any]] = None,
        channel: str = 'ratio',
        method: str = 'auc',
        units: str = 'calorie'
    ) -> int:
        """
        一次性保存完整的分析结果
        
        Args:
            name: 会话名称
            source_files: 源文件列表
            tm_results: Tm 结果列表
            thermo_result: 热力学结果（可选）
            channel: 数据通道
            method: 分析方法
            units: 单位制
        
        Returns:
            会话 ID
        """
        # 创建会话
        session_id = self.create_session(
            name=name,
            source_files=source_files,
            channel=channel,
            method=method,
            units=units
        )
        
        # 保存 Tm 结果
        self.save_tm_results(session_id, tm_results)
        
        # 保存热力学结果（如果有）
        if thermo_result:
            self.save_thermo_result(session_id, thermo_result)
        
        return session_id
    
    def get_complete_analysis(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        获取完整的分析结果
        
        Args:
            session_id: 会话 ID
        
        Returns:
            完整的分析结果字典
        """
        session_info = self.get_session(session_id)
        if not session_info:
            return None
        
        return {
            'session': session_info,
            'tm_results': self.get_tm_results(session_id),
            'thermo_result': self.get_thermo_result(session_id)
        }

