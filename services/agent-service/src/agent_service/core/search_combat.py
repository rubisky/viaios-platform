"""Combat-Ready Search — 1:N matching, N:M comparison, data preview."""
import hashlib
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .production_upgrade import db_store, health_monitor, production_cache

logger = logging.getLogger(__name__)


class CombatSearchEngine:
    """Production combat search with 1:N, N:M matching and preview."""

    SAMPLE_DATA = {
        "person_001": {"id":"person_001","type":"人员","name":"嫌疑人A","attributes":{"性别":"男","年龄":35,"身高":"178cm","体型":"中等","上衣":"红色夹克","下衣":"黑色长裤","鞋子":"白色运动鞋","配饰":"黑色背包"},"images":["/preview/person_001_front.jpg","/preview/person_001_side.jpg"],"timeline":[{"时间":"20:15","摄像头":"A3-主入口","行为":"进入"},{"时间":"20:22","摄像头":"B1-走廊","行为":"经过"},{"时间":"20:30","摄像头":"C2-停车场","行为":"离开"}]},
        "person_002": {"id":"person_002","type":"人员","name":"同行者B","attributes":{"性别":"男","年龄":28,"身高":"172cm","体型":"瘦","上衣":"黑色外套","下衣":"蓝色牛仔裤","鞋子":"棕色皮鞋"},"timeline":[{"时间":"20:14","摄像头":"A3-主入口","行为":"进入"},{"时间":"20:22","摄像头":"B1-走廊","行为":"经过"}]},
        "person_003": {"id":"person_003","type":"人员","name":"目击者C","attributes":{"性别":"女","年龄":42,"身高":"162cm","体型":"中等","上衣":"白色衬衫","下衣":"黑色裙子","鞋子":"黑色高跟鞋"},"timeline":[{"时间":"20:18","摄像头":"B1-走廊","行为":"目击"}]},
        "person_004": {"id":"person_004","type":"人员","name":"保安D","attributes":{"性别":"男","年龄":45,"身高":"175cm","体型":"健壮","上衣":"蓝色制服","下衣":"黑色长裤","配饰":"对讲机"},"timeline":[{"时间":"20:12","摄像头":"A3-主入口","行为":"巡逻"}]},
        "person_005": {"id":"person_005","type":"人员","name":"快递员E","attributes":{"性别":"男","年龄":25,"身高":"170cm","体型":"瘦","上衣":"黄色马甲","下衣":"黑色长裤","配饰":"快递箱"},"timeline":[{"时间":"20:08","摄像头":"A3-主入口","行为":"送货"}]},
        "person_006": {"id":"person_006","type":"人员","name":"清洁工F","attributes":{"性别":"女","年龄":50,"身高":"158cm","体型":"中等","上衣":"灰色工作服","下衣":"深蓝长裤"},"timeline":[{"时间":"19:30","摄像头":"C2-停车场","行为":"清扫"}]},
        "vehicle_001": {"id":"vehicle_001","type":"车辆","name":"白色凯美瑞ABC123","attributes":{"品牌":"丰田","型号":"凯美瑞","颜色":"白色","年份":"2023","车牌":"ABC123"},"images":["/preview/vehicle_001_front.jpg"],"timeline":[{"时间":"20:10","摄像头":"Gate A-车辆入口","行为":"进入"},{"时间":"20:30","摄像头":"Gate B-车辆出口","行为":"离开"}]},
        "vehicle_002": {"id":"vehicle_002","type":"车辆","name":"黑色雅阁XYZ789","attributes":{"品牌":"本田","型号":"雅阁","颜色":"黑色","年份":"2022","车牌":"XYZ789"},"timeline":[{"时间":"20:05","摄像头":"Gate A-车辆入口","行为":"进入"}]},
        "vehicle_003": {"id":"vehicle_003","type":"车辆","name":"红色宝马X5","attributes":{"品牌":"宝马","型号":"X5","颜色":"红色","年份":"2024","车牌":"BMW888"},"timeline":[{"时间":"20:25","摄像头":"Gate A-车辆入口","行为":"进入"}]},
        "vehicle_004": {"id":"vehicle_004","type":"车辆","name":"银色奥迪A6","attributes":{"品牌":"奥迪","型号":"A6","颜色":"银色","年份":"2023","车牌":"AUD666"},"timeline":[{"时间":"20:18","摄像头":"Gate B-车辆出口","行为":"离开"}]},
        "vehicle_005": {"id":"vehicle_005","type":"车辆","name":"白色面包车","attributes":{"品牌":"五菱","型号":"荣光","颜色":"白色","年份":"2021","车牌":"WL001"},"timeline":[{"时间":"20:02","摄像头":"Gate A-车辆入口","行为":"进入"},{"时间":"20:28","摄像头":"C2-停车场","行为":"停靠"}]},
    }

    def search_1vn(self, target: Dict, compare_pool: List[Dict],
                   top_k: int = 10) -> Dict[str, Any]:
        """
        1:N matching — 录入一个目标，在N个目标库中检索最相似的对象。

        Args:
            target: 待检索目标 {attributes: {...}, image_url: "..."}
            compare_pool: 比对库 [{attributes: {...}}, ...]
            top_k: 返回Top-K个结果
        """
        start = time.perf_counter()
        target_attrs = target.get("attributes", {})
        results = []

        for item in compare_pool:
            item_attrs = item.get("attributes", {})
            score = self._attribute_match_score(target_attrs, item_attrs)
            if score > 0.3:
                results.append({
                    **item,
                    "匹配度": round(score * 100, 1),
                    "匹配详情": self._explain_match(target_attrs, item_attrs, score),
                })

        results.sort(key=lambda x: -x["匹配度"])
        results = results[:top_k]

        elapsed = (time.perf_counter() - start) * 1000
        health_monitor.record("search_1vn_latency", elapsed)

        return {
            "检索模式": "1:N",
            "目标": target.get("name", "未知目标"),
            "比对数量": len(compare_pool),
            "结果数量": len(results),
            "耗时_ms": round(elapsed, 1),
            "结果": results,
        }

    def search_nvm(self, queries: List[Dict], compare_pool: List[Dict]) -> Dict[str, Any]:
        """
        N:M matching — 批量目标同时对库进行检索比对。

        Args:
            queries: N个待检索目标
            compare_pool: M个比对目标
        """
        start = time.perf_counter()
        cross_results = []
        match_matrix = []

        for qi, query in enumerate(queries):
            row = []
            for ci, candidate in enumerate(compare_pool):
                score = self._attribute_match_score(
                    query.get("attributes", {}), candidate.get("attributes", {}))
                row.append(round(score * 100, 1))
                if score > 0.5:
                    cross_results.append({
                        "查询目标": query.get("name", f"目标{qi+1}"),
                        "匹配目标": candidate.get("name", f"目标{ci+1}"),
                        "匹配度": round(score * 100, 1),
                        "匹配详情": self._explain_match(
                            query.get("attributes", {}), candidate.get("attributes", {}), score),
                    })
            match_matrix.append(row)

        cross_results.sort(key=lambda x: -x["匹配度"])
        elapsed = (time.perf_counter() - start) * 1000
        health_monitor.record("search_nvm_latency", elapsed)

        return {
            "检索模式": "N:M",
            "查询数量": len(queries),
            "比对数量": len(compare_pool),
            "交叉匹配数": len(cross_results),
            "匹配矩阵": match_matrix,
            "耗时_ms": round(elapsed, 1),
            "结果": cross_results[:20],
        }

    def get_preview(self, target_id: str) -> Optional[Dict[str, Any]]:
        """获取目标的详细预览数据（图片、属性、时间线）。"""
        data = self.SAMPLE_DATA.get(target_id)
        if not data:
            return None
        return {
            **data,
            "预览时间": datetime.now(timezone.utc).isoformat(),
        }

    def get_candidates(self, category: str = "人员") -> List[Dict]:
        """获取候选比对库列表。"""
        type_map = {"person": "人员", "vehicle": "车辆", "camera": "摄像头", "人员": "人员", "车辆": "车辆", "摄像头": "摄像头", "all": "all"}
        target_type = type_map.get(category, "人员")
        return [v for k, v in self.SAMPLE_DATA.items()
                if v.get("type") == target_type
                or (target_type == "all" and v.get("type") in ("人员", "车辆"))]

    def _attribute_match_score(self, attrs1: Dict, attrs2: Dict) -> float:
        """属性匹配评分算法。"""
        if not attrs1 or not attrs2:
            return 0.1

        total_weight = 0
        matched_weight = 0
        weights = {"上衣": 3, "颜色": 3, "车牌": 5, "性别": 2, "品牌": 3, "型号": 2, "下衣": 1, "鞋子": 1, "配饰": 1, "体型": 1, "年份": 1}

        for key, val1 in attrs1.items():
            val2 = attrs2.get(key)
            if val2 is None:
                continue
            weight = weights.get(key, 1)
            total_weight += weight
            val1_str = str(val1).strip().replace(' ','')
            val2_str = str(val2).strip().replace(' ','')
            if val1_str == val2_str:
                matched_weight += weight
            elif key == "身高":
                try:
                    h1 = int(val1_str.replace('cm','').replace('CM',''))
                    h2 = int(val2_str.replace('cm','').replace('CM',''))
                    if abs(h1 - h2) <= 5: matched_weight += weight * 0.5
                except: pass
            elif key in ("上衣", "下衣") and ("夹克" in val1_str or "外套" in val1_str) and ("夹克" in val2_str or "外套" in val2_str):
                matched_weight += weight * 0.7

        return matched_weight / max(total_weight, 1) if total_weight > 0 else 0

    def _explain_match(self, attrs1: Dict, attrs2: Dict, score: float) -> str:
        """生成匹配解释。"""
        explanations = []
        for key in set(list(attrs1.keys()) + list(attrs2.keys())):
            v1 = attrs1.get(key, "-")
            v2 = attrs2.get(key, "-")
            if v1 == v2 and v1 != "-":
                explanations.append(f"{key}一致({v1})")
            elif v1 != v2 and v1 != "-" and v2 != "-":
                explanations.append(f"{key}不同({v1}vs{v2})")
        return "; ".join(explanations[:5]) if explanations else "无可比对属性"


combat_search = CombatSearchEngine()
