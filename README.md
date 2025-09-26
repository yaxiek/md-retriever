# md-retriever

`md-retriever` は、指定ディレクトリ配下の **Markdown(.md) ファイル** を再帰的に列挙し、  
**ツリー構造のリンク集**を `index.md`（既定）などに書き出すツールです。  

`.gitignore` は参照せず（= 無視）、ファイルシステム上に存在する `.md` をすべて対象にします。  
実行は手動のみ。シンプルな 2 ファイル構成（`md-retriever.sh` + `md_retriever.py`）で動作します。  

---

## 特徴

- `.gitignore` は無視して `.md` を全件探索
- 階層を反映したツリー構造でリンク出力
- 既存 `index.md` の  
  `<!-- AUTO-TOC START --> ... <!-- AUTO-TOC END -->` 区間だけ差し替え  
- 除外パターンは TOML 設定または CLI オプションで指定可能（glob 対応）
- macOS 標準の `python3` で動作（依存なし）
- CLI > TOML > デフォルト の優先度で設定をマージ

---

## インストール方法

### 前提
- macOS または Linux
- Python 3.11 以上推奨（標準搭載の `python3` で動作可）
  - 3.11 未満の場合は `tomli` ライブラリが必要になることがあります  
    ```bash
    pip install tomli
    ```

### 手順

1. リポジトリを取得します。
   ```bash
   git clone https://github.com/yourname/md-retriever.git
   cd md-retriever
   ```

2. 実行権限を付与します。
   ```bash
   chmod +x md-retriever.sh
   ```

3. （任意）システムのパスが通った場所に配置します。  
   ```bash
   sudo cp md-retriever.sh /usr/local/bin/md-retriever
   sudo cp md_retriever.py /usr/local/bin/
   ```

   これでどこからでも実行できます。
   ```bash
   md-retriever .
   ```

> ⚠️ `md-retriever.sh` と `md_retriever.py` は **必ず同じディレクトリに置いてください**。  
> `md-retriever.sh` は同じ場所にある Python 本体を呼び出します。

---

## 使い方

### 基本

```bash
# カレント配下を対象に ./index.md を生成
md-retriever .

# docs 配下を対象に docs/index.md を生成
md-retriever docs
```

### 除外指定

```bash
md-retriever . --exclude node_modules --exclude .obsidian
```

### 出力ファイルを変更

```bash
md-retriever . --output README.md --title "Documentation Index"
```

### 設定ファイルを使う

```bash
md-retriever . --config ./config.toml
```

---

## 設定ファイル（config.toml）

対象ディレクトリ直下に `.md-retriever/config.toml` を置くと、  
`--config` を指定しなくても自動的に読み込まれます。  

CLI > TOML > デフォルト の順に上書きされます。

```toml
# .md-retriever/config.toml

# 出力ファイル名
output = "index.md"

# 差し替えマーカー
marker_start = "<!-- AUTO-TOC START -->"
marker_end   = "<!-- AUTO-TOC END -->"

# 新規作成時のタイトル
title = "Documentation Index"

# 内蔵の除外リストを無効化する場合
# no_default_excludes = true

# 除外したいパターン（glob対応）
excludes = [
  ".obsidian",
  "build",
  "dist",
]
```

---

## オプション一覧（CLI）

- `--exclude <pattern>` : 除外パターン（複数回可）
- `--output <file>` : 出力ファイル名（既定: index.md）
- `--marker-start <str>` : 差し替え開始マーカー
- `--marker-end <str>` : 差し替え終了マーカー
- `--title <str>` : 新規作成時にタイトルを追加
- `--no-default-excludes` : 内蔵の除外リストを無効化
- `--config <file>` : TOML 設定ファイルを読み込み

---

## Obsidian / iCloud で利用

Obsidian Vault 内で直接生成するのが最も確実です。  
外部に生成した `index.md` を Vault に取り込みたい場合はシンボリックリンクを張ることも可能です。

```bash
ln -s "/path/to/notes/index.md"   "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Obsidian/MyVault/index.md"
```

ただし相対リンクの解決がずれる場合があるため、Vault 内で生成するのがおすすめです。  

---

## ライセンス

MIT（任意にどうぞ）

---

⚠️ **Note**: このツール本体および README は AI (ChatGPT) により生成されました。  
利用や改変はご自身の判断と責任でお願いします。
