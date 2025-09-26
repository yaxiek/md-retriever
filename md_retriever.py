#!/usr/bin/env python3
# md_retriever.py — 指定ディレクトリ配下の .md を列挙し、ツリーのリンク集を出力
# 設定は config.toml（--config）で読み込み可能。CLI > TOML > デフォルトで上書き。

import argparse, os, sys, fnmatch, textwrap

# --- TOML ローダ（Python 3.11+: tomllib / それ以前: tomli があれば使用） ---
def load_toml(path):
    if not path:
        return {}
    if not os.path.exists(path):
        raise FileNotFoundError(f"config not found: {path}")
    try:
        import tomllib  # Python 3.11+
        with open(path, 'rb') as f:
            return tomllib.load(f)
    except ModuleNotFoundError:
        try:
            import tomli  # サードパーティ（任意）
            with open(path, 'rb') as f:
                return tomli.load(f)
        except ModuleNotFoundError:
            raise RuntimeError(
                "TOML reader not available. Use Python 3.11+ (tomllib) "
                "or `pip install tomli`, or avoid --config."
            )

# --- デフォルト ---
DEFAULTS = {
    "output": "index.md",
    "marker_start": "<!-- AUTO-TOC START -->",
    "marker_end": "<!-- AUTO-TOC END -->",
    "title": None,
    "no_default_excludes": False,
    "excludes": [
        ".git", ".DS_Store", "node_modules", ".venv",
        "dist", "build", "Library", "Temp",
        ".Trash", ".idea", ".vscode"
    ],
    "respect_gitignore": True,
}

def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="md-retriever",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
            指定ディレクトリ配下の .md を再帰列挙し、ツリー状リンクを出力します。
            優先度: CLI > TOML > デフォルト
        """),
        add_help=True
    )
    p.add_argument("root", help="対象ディレクトリ")
    p.add_argument("--config", default=None, help="TOML 設定ファイルパス（例: ./config.toml）")
    p.add_argument("--exclude", action="append", default=None, help="除外パターン（glob）。複数回可")
    p.add_argument("--output", default=None, help="出力ファイル名（既定: index.md）")
    p.add_argument("--marker-start", dest="marker_start", default=None, help="差し替え開始マーカー")
    p.add_argument("--marker-end", dest="marker_end", default=None, help="差し替え終了マーカー")
    p.add_argument("--title", default=None, help="新規作成時の先頭 H1 タイトル")
    p.add_argument("--no-default-excludes", action="store_true", help="内蔵の除外リストを無効化")
    p.add_argument("--respect-gitignore", dest="respect_gitignore", action="store_true", help="Enable honoring .gitignore files (default)")
    p.add_argument("--no-gitignore", dest="respect_gitignore", action="store_false", help="Do NOT honor .gitignore (scan everything)")
    p.set_defaults(respect_gitignore=None)
    return p.parse_args(argv)

def merge_config(cli, toml_obj):
    # TOML セクションは top-level or [md_retriever] の両方に対応
    conf = {}
    if toml_obj:
        conf = dict(toml_obj.get("md_retriever", toml_obj))

    merged = dict(DEFAULTS)

    # TOML 反映
    if "output" in conf: merged["output"] = conf["output"]
    if "marker_start" in conf: merged["marker_start"] = conf["marker_start"]
    if "marker_end" in conf: merged["marker_end"] = conf["marker_end"]
    if "title" in conf: merged["title"] = conf["title"]
    if "no_default_excludes" in conf: merged["no_default_excludes"] = bool(conf["no_default_excludes"])
    if "respect_gitignore" in conf:
        merged["respect_gitignore"] = bool(conf["respect_gitignore"])
    if "excludes" in conf and isinstance(conf["excludes"], list):
        merged["excludes"] = conf["excludes"][:] if not merged["no_default_excludes"] else conf["excludes"][:]

    # CLI 反映（優先）
    if cli.output is not None: merged["output"] = cli.output
    if cli.marker_start is not None: merged["marker_start"] = cli.marker_start
    if cli.marker_end is not None: merged["marker_end"] = cli.marker_end
    if cli.title is not None: merged["title"] = cli.title
    if cli.no_default_excludes: merged["no_default_excludes"] = True
    if cli.respect_gitignore is not None:
        merged["respect_gitignore"] = bool(cli.respect_gitignore)

    # excludes は CLI があればそれを優先マージ
    # no_default_excludes = True の場合は DEFAULTS をベースにしない
    base_ex = [] if merged["no_default_excludes"] else list(DEFAULTS["excludes"])
    # TOML に excludes があれば追加
    if "excludes" in conf and isinstance(conf.get("excludes"), list):
        for x in conf["excludes"]:
            if x not in base_ex:
                base_ex.append(x)
    # CLI excludes（あれば最優先で追加）
    if cli.exclude:
        for x in cli.exclude:
            if x not in base_ex:
                base_ex.append(x)
    merged["excludes"] = base_ex

    return merged

def load_gitignore_spec(root):
    """Load all .gitignore rules under root into a single pathspec.
    Rules keep their directory context by prefixing patterns with the .gitignore's relative dir when needed.
    Returns a pathspec.PathSpec or None.
    """
    try:
        import pathspec
    except ModuleNotFoundError:
        return None

    patterns = []
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        if ".gitignore" in filenames:
            reldir = os.path.relpath(dirpath, root)
            # read lines
            fp = os.path.join(dirpath, ".gitignore")
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    for line in f:
                        s = line.rstrip("\n")
                        if not s or s.lstrip().startswith('#'):
                            continue
                        neg = s.startswith('!')
                        raw = s[1:] if neg else s
                        # Normalize root-anchored vs relative patterns
                        if raw.startswith('/'):
                            # Root-anchored pattern relative to repo root
                            norm = raw.lstrip('/')
                        else:
                            base = (reldir if reldir != '.' else '')
                            norm = os.path.join(base, raw).replace('\\', '/')
                        pat = ('!' if neg else '') + norm
                        patterns.append(pat)
            except Exception:
                continue
    if not patterns:
        return None
    try:
        import pathspec
        return pathspec.PathSpec.from_lines('gitwildmatch', patterns)
    except Exception:
        return None

def should_exclude(name, relpath, patterns, git_spec=None, is_dir=False):
    # Git ignore takes precedence when provided
    if git_spec is not None:
        relpath_norm = relpath.replace(os.sep, '/')
        if is_dir and not relpath_norm.endswith('/'):
            relpath_norm += '/'
        if git_spec.match_file(relpath_norm):
            return True
    for pat in patterns:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(relpath, pat):
            return True
        if relpath.startswith(pat.rstrip('/')) and pat.endswith('/**'):
            return True
    return False

def scan_md(root, excludes, git_spec=None):
    md = []
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        reldir = os.path.relpath(dirpath, root)
        if reldir == '.':
            reldir = ''
        dirnames[:] = [d for d in dirnames
                        if not should_exclude(d, os.path.join(reldir, d), excludes, git_spec, is_dir=True)]
        for f in filenames:
            relfile = os.path.join(reldir, f) if reldir else f
            if should_exclude(f, relfile, excludes, git_spec, is_dir=False):
                continue
            if f.lower().endswith('.md'):
                md.append(relfile)
    return sorted(md, key=str.lower)

def build_tree(md_paths, root, outdir):
    tree = {}
    for p in md_paths:
        parts = p.split(os.sep)
        cur = tree
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur.setdefault('_files', []).append(parts[-1])

    def emit(node, prefix):
        lines = []
        for f in sorted(node.get('_files', []), key=str.lower):
            rel_to_root = os.path.join(prefix, f)
            abs_target = os.path.join(root, rel_to_root)
            href = os.path.relpath(abs_target, start=outdir).replace(os.sep, '/')
            lines.append(f"- [{f}]({href})")
        for name in sorted([k for k in node.keys() if k != '_files'], key=str.lower):
            # Flatten chain of single-child directories with no files
            chain = [name]
            child_node = node[name]
            while True:
                subdirs = [k for k in child_node.keys() if k != '_files']
                if len(subdirs) == 1 and not child_node.get('_files'):
                    chain.append(subdirs[0])
                    child_node = child_node[subdirs[0]]
                else:
                    break
            display = "/".join(chain) + "/"
            lines.append(f"- **{display}**")
            new_prefix = os.path.join(prefix, *chain)
            child_lines = emit(child_node, new_prefix)
            lines.extend(["  " + l for l in child_lines])
        return lines
    return emit(tree, "")

def write_index(root, outfile, lines, marker_start, marker_end, title):
    outpath = os.path.join(root, outfile)
    existed = os.path.exists(outpath)
    before, after = "", ""
    if existed:
        with open(outpath, 'r', encoding='utf-8') as f:
            content = f.read()
        if marker_start in content and marker_end in content:
            pre, rest = content.split(marker_start, 1)
            mid, post = rest.split(marker_end, 1)
            before, after = pre, post
        else:
            before = content
            after = ""
    else:
        if title:
            before = f"# {title}\n\n"

    body = "\n".join(lines) + "\n"
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(before.rstrip() + "\n")
        f.write(marker_start + "\n")
        f.write(body)
        f.write(marker_end + "\n")
        f.write(after.lstrip())
    return outpath

def main(argv):
    cli = parse_args(argv)

    # 設定ファイル決定
    config_path = cli.config
    if not config_path:
        candidate = os.path.join(cli.root, ".md-retriever", "config.toml")
        if os.path.exists(candidate):
            config_path = candidate

    toml_obj = load_toml(config_path) if config_path else {}
    cfg = merge_config(cli, toml_obj)

    root = os.path.abspath(cli.root)
    # Resolve output directory for link relativization
    outpath = cfg["output"] if os.path.isabs(cfg["output"]) else os.path.join(root, cfg["output"]) 
    outdir = os.path.dirname(outpath)

    git_spec = None
    if cfg.get("respect_gitignore", True):
        git_spec = load_gitignore_spec(root)
        if git_spec is None and cfg.get("respect_gitignore", True):
            # If user explicitly requested gitignore but pathspec is missing, give a friendly hint
            try:
                import pathspec  # noqa: F401
            except ModuleNotFoundError:
                print("[md-retriever] .gitignore is enabled but 'pathspec' is not installed. Run: pip install pathspec", file=sys.stderr)

    md = scan_md(root, cfg["excludes"], git_spec)
    md = [p for p in md if p != cfg["output"]]  # 自分自身を除外
    lines = build_tree(md, root, outdir)
    out = write_index(root, cfg["output"], lines,
                    cfg["marker_start"], cfg["marker_end"], cfg["title"])
    print(f"wrote: {out}")

if __name__ == "__main__":
    main(sys.argv[1:])