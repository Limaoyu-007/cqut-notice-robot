import json
import os
from pathlib import Path


def _load_env_file(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def load_user_profile(path: str | Path) -> dict:
    profile_path = Path(path)
    with profile_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("User profile JSON must be an object")
    return data


_load_env_file(Path(__file__).with_name(".env"))

DEFAULT_NOTICE_LIST_URLS = [
    "https://www.cqut.edu.cn/tzgg/bmtz.htm",
    "https://www.cqut.edu.cn/tzgg/xxtz1.htm",
    "https://www.cqut.edu.cn/tzgg/zbxx.htm",
    "https://www.cqut.edu.cn/tzgg/xsjz.htm",
]
NOTICE_LIST_URLS = _get_list("NOTICE_LIST_URLS", DEFAULT_NOTICE_LIST_URLS)
NOTICE_LIST_URL = NOTICE_LIST_URLS[0]

BASE_URL = "https://www.cqut.edu.cn"

REQUEST_TIMEOUT = _get_int("REQUEST_TIMEOUT", 15)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
BROWSER_PATH = os.getenv("BROWSER_PATH", "")

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")

# 定时抓取间隔（分钟）
SCHEDULE_INTERVAL_MINUTES = _get_int("SCHEDULE_INTERVAL_MINUTES", 10)

LOG_PATH = os.getenv("NOTICE_ROBOT_LOG_PATH", "logs/notice_robot.log")
ERROR_ALERT_ENABLED = os.getenv("ERROR_ALERT_ENABLED", "1") != "0"
DRY_RUN = _get_bool("DRY_RUN", False)

AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-v4-flash")
AI_ENABLED = _get_bool("AI_ENABLED", True)

DEFAULT_USER_PROFILE = {
    "identity": "重庆理工大学计算机科学与技术专业本科生",
    "stage": "大二下",
    "career_direction": [
        "Java 后端开发",
        "AI 应用工程化",
        "软件开发项目实践",
        "实习就业",
    ],
    "high_interest": [
        "计算机、人工智能、软件开发、后端开发、Web 开发、数据、算法、工程实践相关讲座、培训、沙龙、分享会、比赛和实践活动",
        "大学生创新创业项目、计算机设计大赛、软件杯、挑战杯、互联网+、AI 创新类比赛、程序设计竞赛",
        "实验室招新、科研项目招募、导师项目、学生团队招募、技术社团招募，尤其是后端、AI、Web 开发、工程实践、科研训练相关机会",
        "实习就业、企业宣讲、校招提前批、实习招聘、就业指导、简历辅导、面试辅导、职业规划、企业参观",
        "学生可以直接参与、报名、申报、提交作品、获得证书、奖项、项目经历、科研经历、实习经历的通知",
        "英语四六级、考试安排、选课、补考、成绩、学籍、毕业要求等重要教务通知",
    ],
    "low_interest": [
        "教师项目申报、教师培训、教师评奖、教师会议、行政管理、公示公告等主要面向教职工的信息",
        "采购招标、资产处置、后勤维修、基建施工、财务报销、部门内部行政事务",
        "与专业方向关系较弱的普通宣传、形式化活动、非技术类讲座、无明确收获的会议通知",
        "已经过期、截止时间很近且无法参与、参与门槛明显不适合的通知",
        "只需要记录但不需要立刻打扰的低价值信息",
    ],
    "rating_rules": {
        "high": "与计算机、AI、软件开发、后端、Web、数据、算法、工程实践、竞赛、科研项目、实验室、实习就业、重要教务事项直接相关，并且用户可以报名、申报、参赛、参与项目、加入团队，或能获得证书、奖项、学分、项目经历、科研经历、实习经历、简历价值。",
        "medium": "与学生有关，但和计算机、AI、就业、竞赛、科研相关性一般；有一定参与价值但不是当前阶段核心目标；普通学术讲座、通用能力培训、学校活动、志愿活动、评优评奖、奖助学金、普通教务提醒等。",
        "low": "主要面向教师、行政人员、部门内部人员；采购、招标、资产、后勤、基建、会议、公示类信息；没有明确学生参与方式，或没有实际行动价值；已经过期或明显不适合参与。",
    },
    "analysis_preference": "优先判断这条通知是否值得用户现在停下来查看。高重要需要说明价值点和行动建议；中重要简短提醒关键信息；低重要说明为什么不值得打扰。当前阶段只优化 AI 判断，不改变现有推送流程。",
}

USER_PROFILE_PATH = os.getenv("USER_PROFILE_PATH", "")
USER_PROFILE = load_user_profile(USER_PROFILE_PATH) if USER_PROFILE_PATH else DEFAULT_USER_PROFILE
