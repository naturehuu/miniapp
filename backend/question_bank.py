from typing import Dict, List


COMMON_QUESTIONS = [
    {"id": "strengths", "text": "请介绍你的优点和一个需要改进的缺点。"},
    {"id": "overtime", "text": "你如何看待加班？在什么情况下你愿意配合加班？"},
    {"id": "salary", "text": "你的薪资期望是多少？你是如何评估这个范围的？"},
    {"id": "motivation", "text": "你为什么选择这个岗位？你的求职动机是什么？"},
]


ROLE_QUESTIONS: Dict[str, List[dict]] = {
    "店铺运营": COMMON_QUESTIONS
    + [
        {"id": "shop_kpi", "text": "你会如何提升店铺转化率和复购率？"},
        {"id": "activity_plan", "text": "请分享一次你策划促销活动的思路。"},
    ],
    "剪辑师": COMMON_QUESTIONS
    + [
        {"id": "editing_flow", "text": "你的剪辑流程通常是怎样的？"},
        {"id": "tool_skill", "text": "你最熟悉的剪辑软件和效率技巧有哪些？"},
    ],
    "新媒体运营": COMMON_QUESTIONS
    + [
        {"id": "content_strategy", "text": "你如何制定新媒体内容选题和发布节奏？"},
        {"id": "growth_method", "text": "你做过哪些拉新或涨粉动作？效果如何评估？"},
    ],
    "短视频剪辑": COMMON_QUESTIONS
    + [
        {"id": "hook_design", "text": "短视频前三秒你通常如何设计吸引点？"},
        {"id": "data_iteration", "text": "你如何根据完播率、点赞率优化剪辑方案？"},
    ],
    "商品运营": COMMON_QUESTIONS
    + [
        {"id": "product_selection", "text": "你会用哪些维度判断一个商品是否值得主推？"},
        {"id": "pricing_strategy", "text": "你如何平衡毛利、销量和价格竞争力？"},
    ],
    "数据运营/分析师": COMMON_QUESTIONS
    + [
        {"id": "metric_design", "text": "你会如何为业务设计核心指标体系？"},
        {"id": "case_analysis", "text": "举例说明你如何从数据发现问题并推动改进。"},
    ],
    "社交媒体运营": COMMON_QUESTIONS
    + [
        {"id": "platform_diff", "text": "你如何区分不同社交平台的内容策略？"},
        {"id": "community_management", "text": "你如何处理评论互动与社群运营？"},
    ],
}


def get_supported_roles() -> List[str]:
    return list(ROLE_QUESTIONS.keys())


def get_questions_by_role(role: str) -> List[dict]:
    return ROLE_QUESTIONS.get(role, COMMON_QUESTIONS)
