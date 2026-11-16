# paperfeed

自分の研究・関心に合わせた論文を、毎朝自動で選んで紹介してくれる Web サイト。

- GitHub Actions が毎朝 arXiv / bioRxiv / medRxiv / PubMed / Semantic Scholar から候補を集める
- Claude が `persona.md`（あなたの研究内容・関心）を読んで論文を選び、本文を読んで紹介文（要約・背景・手法・結果・研究との関係・読みどころ）を書く
- 結果は GitHub Pages の静的サイトに並ぶ（スマホでも読める、数式は MathJax で表示）
- 気になった論文はボタン1つで **Zotero に追加**（紹介文をノートとして、PDF をリンクとして添付）。BibTeX / RIS でほかの文献管理ソフトにも取り込める

サーバーもデータベースも不要です。fork して `persona.md` と `config.yaml` を書き換え、API キーを登録すれば動きます。

着想: ななな２「Claudeを使って論文を短期間で大量に流し読む」(note)

---

## 使い方

### 1. fork する

このリポジトリを自分のアカウントに fork します（public のままで構いません。API キーは Secrets に入れるので公開されません）。

> [!NOTE]
> public リポジトリでは、生成された紹介文（`site/data/`）と `persona.md` も公開されます。研究内容を公開したくない場合は private リポジトリにしてください（GitHub Pages を private リポジトリで使うには有料プランが必要です）。

### 2. `persona.md` を書く

あなたが誰で、何を研究していて、何に興味があり、何を読みたくないかを書きます。Claude はこのファイルを毎回全文読んでから論文を選び、紹介文を書きます。

- **言語** — 紹介文の言語（`日本語` / `English` など）
- **立場** — 例: 物理学専攻の修士1年、量子情報の研究室
- **主テーマ** — 何をどういう手法で調べているか、当面の課題
- **関連分野**
- **既に読んだ主要な先行研究** — ここに書いた論文は紹介されなくなる
- **対象外** — 読みたくない種類の論文
- **紹介文の書き方** — 文体の好みなど

具体的に書くほど、選定と「研究との関係」の質が上がります。

### 3. `config.yaml` を書く

分野（field）ごとに、どこから・どんな検索語で・何本探すかを決めます。

```yaml
total: 6               # 1日の最大本数
fields:
  - name: 量子誤り訂正
    count: 3            # この分野から何本
    lookback_days: 7    # 何日前までを候補にするか
    sources: [arxiv]
    categories: [quant-ph]
    queries:
      - quantum error correction threshold
      - correlated noise surface code

  - name: 単一細胞解析
    count: 2
    sources: [biorxiv, pubmed]
    categories: [bioinformatics, genomics]
    queries:
      - single-cell RNA-seq
```

| source | 検索方法 | `categories` | `queries` |
|---|---|---|---|
| `arxiv` | arXiv API | arXiv カテゴリ（`cs.LG`, `quant-ph` など） | 英語キーワード（全単語を含む論文） |
| `biorxiv` / `medrxiv` | 期間内の全件を取得してローカルで絞り込み | subject（`neuroscience` など、任意） | 題名・抄録に含まれる英語キーワード |
| `pubmed` | NCBI E-utilities | — | PubMed の検索式（MeSH 可） |
| `semanticscholar` | Semantic Scholar bulk search | — (`fields_of_study` で絞り込み可) | 英語キーワード |

検索語は英語で書いてください（日本語では英語の論文が見つかりません）。

Claude のモデルや考える深さも `config.yaml` の `claude:` で変えられます。既定は `claude-opus-5-5` です。費用を抑えたい場合は `claude-sonnet-5-5` などに変えてください。

### 4. API キーを登録する

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で登録します。

| 名前 | 必須 | 説明 |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✓ | [Claude Console](https://console.anthropic.com/) で発行 |
| `NCBI_API_KEY` | | PubMed のレート制限を緩める（任意） |
| `S2_API_KEY` | | Semantic Scholar のレート制限を緩める（任意） |

### 5. GitHub Pages を有効にする

**Settings → Pages → Build and deployment → Source** を **GitHub Actions** にします。

### 6. 初回実行

**Actions → daily digest → Run workflow** で手動実行します。数分後に `https://<ユーザー名>.github.io/paperfeed/` に論文が表示されます。以後は毎朝 6:00（日本時間）ごろに自動で実行されます。時刻は `.github/workflows/daily.yml` の `cron`（UTC）で変えられます。

> [!NOTE]
> GitHub は、60日間コミットのない fork のスケジュール実行を止めることがあります。このワークフローは毎日コミットするので通常は問題ありませんが、止まった場合は Actions 画面から再度有効にしてください。

### 7. Zotero を設定する（任意）

1. [zotero.org/settings/keys/new](https://www.zotero.org/settings/keys/new) で API キーを作成する。「Allow library access」と「Allow write access」にチェックを入れる
2. paperfeed のページ右上の ⚙ を開き、API キーを入力して「キーを確認」を押す（ユーザー ID が自動で入る）
3. 追加先のコレクションを決めたい場合は、Zotero ウェブ版でコレクションを開いたときの URL の末尾 8 文字（コレクションキー）を入力する
4. 保存する

以後、各論文の「Zotero に追加」ボタンで、書誌情報・紹介文（ノート）・PDF リンクが Zotero に入ります。

API キーはそのブラウザの localStorage にだけ保存され、送信先は `api.zotero.org` だけです。リポジトリや他のサーバーには送られません。共用の端末では使い終わったら「消去」を押してください。

Mendeley / Paperpile / EndNote などは、BibTeX または RIS ボタンから取り込めます。

---

## 仕組み

```
GitHub Actions (毎朝 cron)
  └─ python -m pipeline
       1. config.yaml の各 field について sources から候補を取得
       2. data/seen.json（既に紹介した論文）と重複を除く
       3. Claude に persona.md と候補一覧を渡して選定 ─┐ structured outputs
       4. 選んだ論文の本文（arXiv は HTML 版）を読み、紹介文を書く ─┘ (JSON)
       5. site/data/YYYY-MM-DD.json と index.json を書いてコミット
  └─ site/ を GitHub Pages にデプロイ
```

```
persona.md          あなたの研究と関心（Claude が毎回読む）
config.yaml         取得元・検索語・本数・モデル
pipeline/           収集・選定・紹介文作成（Python）
  sources/          arxiv / biorxiv / pubmed / semanticscholar
  prompts/          選定と紹介文の指示文
site/               静的サイト（HTML/CSS/JS、ビルド不要）
  data/             生成された紹介文
data/seen.json      既に紹介した論文の記録
```

指示文（`pipeline/prompts/*.md`）も自由に書き換えられます。

## ローカルで動かす

[uv](https://docs.astral.sh/uv/) を使います。

```bash
uv sync
```

```bash
uv run python -m pipeline --dry-run
```

`--dry-run` は候補を集めるだけで Claude を呼ばず、紹介文の欄が空の JSON を書きます（`seen.json` は更新しません）。実際に生成するには `ANTHROPIC_API_KEY` を環境変数か、リポジトリ直下の `.env`（`.gitignore` 済み）に `ANTHROPIC_API_KEY=...` と書いてから実行します。

```bash
uv run python -m pipeline --limit 1
```

| オプション | 説明 |
|---|---|
| `--date YYYY-MM-DD` | 日付を指定（既定は日本時間の今日。`PAPERFEED_TZ` で変更可） |
| `--limit N` | 最大 N 本だけ書く（お試し用） |
| `--force` | その日のファイルがあっても作り直す |
| `--dry-run` | Claude を呼ばない |
| `--data-dir PATH` | 出力先（既定 `site/data`） |

サイトの確認:

```bash
uv run python -m http.server -d site 8000
```

テスト:

```bash
uv run pytest
```

## 費用の目安

1日6本の場合、Claude の呼び出しは選定1回＋紹介文6回です。本文を読むため1本あたりの入力は数万トークンになります。`config.yaml` で本数・モデル・`effort` を調整してください。料金は [Anthropic の料金ページ](https://www.anthropic.com/pricing) を確認してください。

---

## English

paperfeed is a self-hosted daily paper digest. Fork it, describe yourself in `persona.md` (set `## Language` to `English`), list sources and keywords per field in `config.yaml`, add `ANTHROPIC_API_KEY` as an Actions secret, set Pages to deploy from GitHub Actions, and run the **daily digest** workflow. Each morning Claude picks papers from arXiv / bioRxiv / medRxiv / PubMed / Semantic Scholar, reads them, and writes a structured digest. Papers can be sent to Zotero with one click (your Zotero key stays in your browser's localStorage) or exported as BibTeX / RIS.

## License

MIT
