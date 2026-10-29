#!/usr/bin/env python3
"""note記事の公開前チェック（自動でできる部分だけ）。

使い方:
    python3 scripts/check_article.py articles/drafts/xxx.md [他のファイル ...]

ERROR が1つでもあれば終了コード1。WARN は確認を促すだけ。
手で確認する項目は checklists/pre-publish.md を参照。
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

BANNED_WORDS = [
    "神家電",
    "買わなきゃ損",
    "買わないと損",
    "最安",
    "今だけ",
    "在庫あり",
    "どれも良い",
    "どれもいい",
]
PR_PATTERN = re.compile(r"PR|広告")
PR_SEARCH_LINES = 5
REVIEW_TYPES = {"使用レビュー", "スペック比較"}
STALE_DAYS = 14
MAX_TABLE_ROWS = 5
MIN_QA = 3

# 6つの壁に対応する見出し（format ごと）。見出しにこの語が含まれていればOK
REQUIRED_HEADINGS = {
    "comparison": ["結論", "比較表", "サイズ", "違い", "安さだけ", "ネット", "こんな人", "Q&A"],
    "ranking": ["条件", "結論", "比較表", "安さだけ", "ネット", "Q&A"],
}

PRICE_PATTERN = re.compile(r"[0-9０-９][0-9０-９,，.]*\s*(万円|円)")
WEAK_LINK_PATTERN = re.compile(r"\[(詳しくはこちら|こちら|ここ|コチラ|リンク)\]\(")
EMPTY_LINK_PATTERN = re.compile(r"\]\(\s*\)")
LINK_PATTERN = re.compile(r"\]\(\s*https?://|https?://")
PLACEHOLDER_PATTERN = re.compile(r"〇|YYYY|【要確認】")


@dataclass
class Result:
    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def split_front_matter(text: str) -> tuple[dict[str, str], str]:
    """先頭の --- で囲まれた部分から、トップレベルの key: value だけ読む。"""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*?)\s*(#.*)?$", line)
        if m:
            meta[m.group(1)] = m.group(2).strip().strip('"')
    return meta, text[end + 5 :]


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def check_date(meta: dict[str, str], key: str, label: str, res: Result, today: dt.date) -> None:
    value = meta.get(key, "")
    try:
        date = dt.date.fromisoformat(value)
    except ValueError:
        res.errors.append(f"front matter の {key}（{label}）に確認日を YYYY-MM-DD で書いてください（現在: {value or '未記入'}）")
        return
    if date > today:
        res.errors.append(f"{key} が未来の日付です: {value}")
    elif (today - date).days > STALE_DAYS:
        res.warnings.append(f"{key} が{STALE_DAYS}日以上前です（{value}）。公開前にもう一度確認してください")


def headings(body: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"^#{2,4}\s+(.+)$", body, flags=re.MULTILINE)]


def comparison_table_rows(body: str) -> int | None:
    """「比較表」見出しの直後にある最初の表のデータ行数。"""
    m = re.search(r"^#{2,4}\s+比較表.*$", body, flags=re.MULTILINE)
    if not m:
        return None
    rows = []
    for line in body[m.end() :].splitlines():
        if line.startswith("#"):
            break
        if line.strip().startswith("|"):
            rows.append(line)
        elif rows:
            break
    data = [r for r in rows[1:] if not re.fullmatch(r"[\s|:\-]+", r)]
    return len(data)


def check(path: Path, today: dt.date) -> Result:
    res = Result(path)
    meta, raw_body = split_front_matter(path.read_text(encoding="utf-8"))
    body = strip_comments(raw_body)

    if not meta:
        res.errors.append("front matter（--- で囲んだ記事情報）がありません。templates/ からコピーしてください")

    fmt = meta.get("format", "comparison")
    review_type = meta.get("review_type", "")
    if review_type not in REVIEW_TYPES:
        res.errors.append(f"review_type は「使用レビュー」か「スペック比較」にしてください（現在: {review_type or '未記入'}）")
    elif review_type not in body:
        res.warnings.append(f"本文に「{review_type}」の表示がありません")

    check_date(meta, "prices_checked", "価格の確認日", res, today)
    check_date(meta, "recall_checked", "リコール情報の確認日", res, today)

    lines = [l for l in body.splitlines() if l.strip()]
    if LINK_PATTERN.search(body) or EMPTY_LINK_PATTERN.search(body):
        head = lines[:PR_SEARCH_LINES]
        if not any(PR_PATTERN.search(l) for l in head):
            res.errors.append(
                f"リンクがあるのに冒頭{PR_SEARCH_LINES}行以内にPR表記がありません"
                "（例：※本記事はアフィリエイト広告（PR）を含みます）"
            )

    for word in BANNED_WORDS:
        if word in body:
            res.errors.append(f"使わない言葉「{word}」が入っています")

    for m in sorted(set(PLACEHOLDER_PATTERN.findall(body))):
        res.errors.append(f"穴埋めが残っています: {m}")

    if EMPTY_LINK_PATTERN.search(body):
        res.errors.append("URLが空のリンク [..]() があります")

    for m in WEAK_LINK_PATTERN.finditer(body):
        res.warnings.append(f"リンク文言「{m.group(1)}」→ 条件と一緒に置いてください（例：乾燥まで毎日回すならこのモデル）")

    if PRICE_PATTERN.search(body) and "記事執筆時点" not in body:
        res.errors.append("価格を書いているのに「記事執筆時点」の表記がありません")

    found = headings(body)
    for required in REQUIRED_HEADINGS.get(fmt, []):
        if not any(required in h for h in found):
            res.errors.append(f"見出し「{required}」がありません（{fmt} の型）")

    if fmt == "ranking":
        if "基準" not in body:
            res.errors.append("ランキングの順位の基準が書かれていません")
        if body.count("合わない人") < 3:
            res.warnings.append("各順位に「合わない人」を書いてください（3つ未満）")
    else:
        if "なくても良い人" not in body and "なくてもいい人" not in body:
            res.warnings.append("「なくても良い人」が書かれていません")
        if "測る" not in body:
            res.warnings.append("サイズの「測る場所」が書かれていません")

    rows = comparison_table_rows(body)
    if rows is not None and rows > MAX_TABLE_ROWS:
        res.warnings.append(f"比較表が{rows}行あります（{MAX_TABLE_ROWS}項目まで）")

    qa = len(re.findall(r"^\*\*Q\.", body, flags=re.MULTILINE))
    if qa < MIN_QA:
        res.warnings.append(f"Q&Aが{qa}個です（{MIN_QA}個が目安）")

    return res


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip())
        return 2
    today = dt.date.today()
    failed = False
    for arg in argv:
        res = check(Path(arg), today)
        status = "NG" if res.errors else "OK"
        print(f"[{status}] {res.path}")
        for e in res.errors:
            print(f"  ERROR: {e}")
        for w in res.warnings:
            print(f"  WARN:  {w}")
        failed |= bool(res.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
