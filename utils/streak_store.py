import json
import os
from datetime import date, timedelta
from calendar import monthcalendar

STREAK_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "streak.json")

MILESTONES = [3, 7, 10, 14, 20, 30, 50, 100]

MILESTONE_MESSAGES = {
    3:   ("🌱", "3日連続達成！", "習慣の芽が出てきました。この調子！"),
    7:   ("🔥", "1週間連続達成！", "本物の継続力です。素晴らしい！"),
    10:  ("⭐", "10日連続達成！", "もう英語学習が日課になってきた！"),
    14:  ("🌟", "2週間連続達成！", "英語力が確実に伸びています！"),
    20:  ("💎", "20日連続達成！", "完全に習慣化されています！"),
    30:  ("🏆", "1ヶ月連続達成！", "あなたは本物の英語学習者です！"),
    50:  ("👑", "50日連続達成！", "圧倒的な継続力。英語がどんどん身に付いています！"),
    100: ("🎉", "100日連続達成！", "伝説の英語学習者！もう止まらない！"),
}


def _load() -> dict:
    if not os.path.exists(STREAK_FILE):
        return {"dates": [], "last_milestone": 0}
    with open(STREAK_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(STREAK_FILE), exist_ok=True)
    with open(STREAK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_activity() -> None:
    """今日の学習を記録する（重複なし）。"""
    today = date.today().isoformat()
    data = _load()
    if today not in data["dates"]:
        data["dates"].append(today)
        _save(data)


def studied_today() -> bool:
    return date.today().isoformat() in set(_load()["dates"])


def get_streak() -> int:
    """連続学習日数を返す（今日 or 昨日を起点）。"""
    dates_set = set(_load()["dates"])
    today = date.today()

    # 今日勉強済みなら今日から遡る、未済なら昨日から遡る
    start = today if today.isoformat() in dates_set else today - timedelta(days=1)

    streak = 0
    check = start
    while check.isoformat() in dates_set:
        streak += 1
        check -= timedelta(days=1)
    return streak


def get_all_dates() -> list[str]:
    return _load()["dates"]


def pop_new_milestone() -> tuple[int, tuple] | tuple[None, None]:
    """新しいマイルストーンに達していれば (日数, メッセージ情報) を返して記録。"""
    streak = get_streak()
    data = _load()
    last = data.get("last_milestone", 0)

    for m in reversed(MILESTONES):
        if streak >= m and last < m:
            data["last_milestone"] = m
            _save(data)
            return m, MILESTONE_MESSAGES[m]
    return None, None


def get_total_days() -> int:
    return len(set(_load()["dates"]))


def render_calendar_html(num_months: int = 3) -> str:
    """直近 num_months ヶ月のカレンダー HTML を返す。"""
    dates_set = set(_load()["dates"])
    today = date.today()

    # 対象月を求める
    months = []
    d = today.replace(day=1)
    for _ in range(num_months):
        months.insert(0, (d.year, d.month))
        d = (d - timedelta(days=1)).replace(day=1)

    day_names = ["月", "火", "水", "木", "金", "土", "日"]

    html = '<div style="display:flex; gap:16px; flex-wrap:wrap; justify-content:center;">'

    for year, month in months:
        month_label = f"{year}年{month}月"
        html += f'''
        <div style="flex:1; min-width:220px; max-width:260px;
                    background:#ffffff; border:1px solid #bfdbfe;
                    border-radius:12px; padding:14px 10px;
                    box-shadow:0 2px 8px rgba(37,99,235,0.08);">
          <div style="text-align:center; font-weight:bold; font-size:0.9em;
                      color:#2563eb; margin-bottom:10px;">{month_label}</div>
          <table style="width:100%; border-collapse:collapse; text-align:center; table-layout:fixed;">
            <tr>
        '''
        for i, dn in enumerate(day_names):
            color = "#ef4444" if i == 6 else "#3b82f6" if i == 5 else "#64748b"
            html += f'<th style="font-size:0.7em; color:{color}; padding:3px 0;">{dn}</th>'
        html += '</tr>'

        for week in monthcalendar(year, month):
            html += '<tr>'
            for day in week:
                if day == 0:
                    html += '<td style="padding:2px 0;"></td>'
                    continue
                d_str = f"{year}-{month:02d}-{day:02d}"
                is_today = (d_str == today.isoformat())
                is_studied = d_str in dates_set

                if is_today and is_studied:
                    bg, color, border = "#4ade80", "#1a1a1a", "2px solid #2563eb"
                elif is_today:
                    bg, color, border = "#fbbf24", "#1a1a1a", "2px solid #f59e0b"
                elif is_studied:
                    bg, color, border = "#22c55e", "#ffffff", "none"
                else:
                    bg = "#f1f5f9"
                    color = "#475569"
                    border = "none"

                fw = "bold" if is_today else "normal"
                html += f'''
                <td style="padding:2px 0;">
                  <div style="
                    width:28px; height:28px; line-height:28px;
                    margin:0 auto;
                    border-radius:50%;
                    background:{bg}; color:{color};
                    font-size:0.75em; border:{border};
                    font-weight:{fw};
                    box-sizing:border-box;
                    overflow:hidden;
                  ">{day}</div>
                </td>'''
            html += '</tr>'

        html += '</table></div>'

    html += '</div>'
    return html
