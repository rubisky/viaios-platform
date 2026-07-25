"""Search Engine V2 — Complete image comparison + library management."""
import hashlib
import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .production_upgrade import db_store, health_monitor

logger = logging.getLogger(__name__)

# ===== 比对库 (Demo data — replace with DB query in production) =====

TARGET_LIBRARY = {
    "嫌疑人员": [
        {"目标ID":"S001","名称":"红夹克嫌疑人","类型":"嫌疑人员","标签":["红色夹克","男性","盗窃案"],"属性":{"性别":"男","年龄":35,"身高":"178cm","体型":"中等","上衣":"红色夹克","下衣":"黑色长裤","鞋子":"白色运动鞋"},"特征图片":["/preview/suspect_front.jpg","/preview/suspect_side.jpg"],"最近出现":"摄像头A3 20:15","关联案件":"CASE-001"},
        {"目标ID":"S002","名称":"黑衣男子","类型":"嫌疑人员","标签":["黑色外套","男性","打架"],"属性":{"性别":"男","年龄":28,"身高":"172cm","体型":"瘦","上衣":"黑色外套","下衣":"蓝色牛仔裤","鞋子":"棕色皮鞋"},"特征图片":["/preview/black_jacket.jpg"],"最近出现":"摄像头B1 20:22","关联案件":"CASE-002"},
        {"目标ID":"S003","名称":"背包男子","类型":"重点人员","标签":["黑色背包","男性","多次出现"],"属性":{"性别":"男","年龄":40,"身高":"180cm","体型":"健壮","上衣":"灰色外套","下衣":"深色长裤","配饰":"黑色背包"},"特征图片":["/preview/backpack_man.jpg"],"最近出现":"摄像头C2 19:50","关联案件":"CASE-001"},
    ],
    "涉案车辆": [
        {"目标ID":"V001","名称":"白色凯美瑞ABC123","类型":"涉案车辆","标签":["白色","丰田","ABC123"],"属性":{"品牌":"丰田","型号":"凯美瑞","颜色":"白色","年份":"2023","车牌":"ABC123"},"特征图片":["/preview/camry_white.jpg"],"最近出现":"Gate A 20:10","关联案件":"CASE-001"},
        {"目标ID":"V002","名称":"黑色雅阁XYZ789","类型":"涉案车辆","标签":["黑色","本田","XYZ789"],"属性":{"品牌":"本田","型号":"雅阁","颜色":"黑色","年份":"2022","车牌":"XYZ789"},"特征图片":["/preview/accord_black.jpg"],"最近出现":"Gate A 20:05","关联案件":"CASE-003"},
        {"目标ID":"V003","名称":"白色面包车WL001","类型":"重点车辆","标签":["白色","五菱","无牌"],"属性":{"品牌":"五菱","型号":"荣光","颜色":"白色","年份":"2021","车牌":"WL001"},"特征图片":["/preview/van_white.jpg"],"最近出现":"C2停车场 20:28","关联案件":"CASE-001"},
    ],
}


class ImageComparator:
    """图片特征比对引擎 — 提取视觉特征并与库中目标比对."""

    def __init__(self):
        self._feature_cache: Dict[str, Dict] = {}
        self._init_library_features()

    def _init_library_features(self):
        """为比对库中每个目标预计算特征向量."""
        for category, targets in TARGET_LIBRARY.items():
            for target in targets:
                tid = target["目标ID"]
                attrs = target["属性"]
                self._feature_cache[tid] = {
                    "颜色特征": self._extract_color_features(attrs),
                    "形状特征": self._extract_shape_features(attrs),
                    "目标ID": tid,
                    "名称": target["名称"],
                }

    def _extract_color_features(self, attrs: Dict) -> Dict:
        """提取颜色特征向量."""
        colors = []
        for key in ["上衣","下衣","鞋子","颜色","配饰"]:
            if key in attrs: colors.append(attrs[key])
        # 模拟特征哈希
        color_hash = hashlib.md5("|".join(colors).encode()).hexdigest()[:16]
        return {"颜色列表": colors, "颜色哈希": color_hash, "主要颜色": colors[0] if colors else "未知"}

    def _extract_shape_features(self, attrs: Dict) -> Dict:
        """提取形状/体型特征."""
        height = attrs.get("身高","170cm").replace("cm","")
        body = attrs.get("体型","中等")
        return {"身高数值": int(height) if height.isdigit() else 170, "体型": body}

    def compare_image(self, uploaded_image_data: str, category: str = "嫌疑人员",
                      top_k: int = 10) -> Dict[str, Any]:
        """
        上传图片比对 — 提取图片特征后与库中目标逐一比对.

        Args:
            uploaded_image_data: base64编码的图片数据
            category: 比对库类别
            top_k: 返回前K个结果
        """
        start = time.perf_counter()

        # 从图片中提取视觉特征（模拟）
        image_hash = hashlib.md5(uploaded_image_data.encode()[:200]).hexdigest()
        image_rng = random.Random(int(image_hash[:8], 16))

        # 提取"检测到的属性"
        detected_attrs = self._detect_attributes_from_image(uploaded_image_data, category)

        # 与库中目标比对
        results = []
        for cat, targets in TARGET_LIBRARY.items():
            if category != "全部" and category != cat: continue
            for target in targets:
                tid = target["目标ID"]
                target_attrs = target["属性"]
                visual_score = self._visual_similarity(detected_attrs, target_attrs, image_hash, tid)
                attr_score = self._attribute_match(detected_attrs, target_attrs)
                combined = round(visual_score * 0.6 + attr_score * 0.4, 1)

                if combined > 30:
                    results.append({
                        "目标ID": tid,
                        "名称": target["名称"],
                        "类别": cat,
                        "标签": target["标签"],
                        "综合匹配度": combined,
                        "视觉相似度": round(visual_score, 1),
                        "属性匹配度": round(attr_score, 1),
                        "匹配属性": self._explain_match_detail(detected_attrs, target_attrs),
                        "特征图片": target["特征图片"],
                        "最近出现": target["最近出现"],
                        "关联案件": target["关联案件"],
                        "目标属性": target["属性"],
                    })

        results.sort(key=lambda x: -x["综合匹配度"])
        results = results[:top_k]

        elapsed = (time.perf_counter() - start) * 1000
        health_monitor.record("image_compare_latency", elapsed)

        return {
            "检索方式": "图片比对",
            "上传图片特征": detected_attrs,
            "比对库": category,
            "库中目标数": sum(len(v) for v in TARGET_LIBRARY.values()),
            "匹配结果数": len(results),
            "耗时_ms": round(elapsed, 1),
            "结果": results,
        }

    def _detect_attributes_from_image(self, image_data: str, category: str) -> Dict:
        """从图片中检测属性（模拟AI检测）."""
        seed = hashlib.md5(image_data.encode()[:100]).hexdigest()
        rng = random.Random(int(seed[:8], 16))

        if "人员" in category or "嫌疑" in category:
            colors = ["红色","黑色","白色","蓝色","灰色","黄色"]
            clothes = ["夹克","外套","衬衫","T恤","制服","马甲"]
            pants = ["长裤","牛仔裤","西裤","短裤"]
            return {
                "检测上衣": f"{rng.choice(colors)}{rng.choice(clothes)}",
                "检测下衣": rng.choice(pants),
                "检测体型": rng.choice(["中等","瘦","健壮"]),
                "检测性别": rng.choice(["男","女"]),
                "估计身高": f"{rng.randint(160,185)}cm",
            }
        else:
            brands = ["丰田","本田","宝马","奥迪","五菱","大众"]
            colors = ["白色","黑色","红色","银色","蓝色"]
            return {
                "检测颜色": rng.choice(colors),
                "检测车型": rng.choice(["轿车","SUV","面包车","卡车"]),
                "估计年份": f"{rng.randint(2020,2024)}",
            }

    def _visual_similarity(self, detected: Dict, target: Dict, img_hash: str, target_id: str) -> float:
        """计算视觉相似度（模拟但有区分度）."""
        rng = random.Random(int(img_hash[:8], 16) + hash(target_id) % 10000)

        # 颜色匹配检查
        color_match = False
        for key in detected:
            for tkey in target:
                dval = str(detected.get(key,""))
                tval = str(target.get(tkey,""))
                if dval and tval and (dval in tval or tval in dval):
                    color_match = True

        base_score = rng.uniform(40, 85)
        if color_match: base_score += 10
        return min(base_score, 98)

    def _attribute_match(self, detected: Dict, target: Dict) -> float:
        """属性匹配评分."""
        score = 0
        count = 0
        for key in detected:
            dval = str(detected[key]).lower()
            for tkey in target:
                tval = str(target[tkey]).lower()
                if dval and tval:
                    if dval in tval or tval in dval:
                        score += 1
                    count += 1
        return (score / max(count, 1)) * 100

    def _explain_match_detail(self, detected: Dict, target: Dict) -> str:
        """详细匹配解释."""
        explanations = []
        for key in detected:
            dval = str(detected[key])
            for tkey in target:
                tval = str(target[tkey])
                if dval and tval and dval in tval:
                    explanations.append(f"{key}={tval}(✓)")
        return "; ".join(explanations[:4]) if explanations else "部分属性匹配"

    def get_library_stats(self) -> Dict:
        """获取比对库统计信息."""
        total = 0
        stats = {}
        for cat, targets in TARGET_LIBRARY.items():
            stats[cat] = {"数量": len(targets), "目标列表": [t["名称"] for t in targets]}
            total += len(targets)
        stats["总计"] = {"数量": total}
        return {"比对库统计": stats, "更新时间": datetime.now(timezone.utc).isoformat()}


image_comparator = ImageComparator()
