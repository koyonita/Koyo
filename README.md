# どっち買い｜家電と家具の結論

迷ったら、あなたの条件で“こっち”を決めます。

家電・家具の比較アカウントの原稿・計画・チェックツール置き場。
Threads / Instagram で集客 → noteマガジン「どっち買い図鑑」→ Amazon・楽天。

| 場所 | 中身 |
| --- | --- |
| [docs/handoff.md](docs/handoff.md) | 引き継ぎ資料（全体設計） |
| [CLAUDE.md](CLAUDE.md) | 原稿を書くときのルール（Claude Code もこれに従う） |
| [content/ideas.md](content/ideas.md) | ネタ帳と進捗 |
| [content/calendar-2026-11.md](content/calendar-2026-11.md) | 11月の投稿カレンダー |
| [templates/](templates/) | note比較記事・ランキング記事・カルーセル・Threads・チャートの型 |
| [checklists/pre-publish.md](checklists/pre-publish.md) | 公開前チェックリスト |
| [scripts/check_article.py](scripts/check_article.py) | 公開前の自動チェック |

## 記事を作る流れ

1. `templates/note-comparison.md`（またはランキング）を `articles/drafts/` にコピー
2. 書く。分からない数値は `【要確認】` と書いておく
3. 自動チェック

   ```bash
   python3 scripts/check_article.py articles/drafts/<ファイル名>.md
   ```

4. `checklists/pre-publish.md` の手動項目を確認
5. noteに公開したら `articles/published/` に移し、`content/ideas.md` の状態を更新

## テスト

```bash
python3 -m unittest discover -s tests
```
