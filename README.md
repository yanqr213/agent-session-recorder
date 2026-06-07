# agent-session-recorder

`agent-session-recorder` 是一个离线 CLI/轻量本地工具，用来把一次 AI coding agent 工作流整理成可审计的 session bundle。它会记录用户目标、上下文文件、命令记录、测试证据、导入材料、变更摘要、风险和后续项，让团队可以把 AI 代理交付过程作为工单附件复查。

项目定位很克制：Python 3.9+、标准库优先、不依赖云服务、不上传数据。

## 适用场景

- AI 编程代理完成一个需求后，团队需要把交付过程沉淀为审计附件。
- Code review 之外还需要保留上下文文件、命令、测试输出和风险说明。
- 安全团队希望离线检查 bundle 是否泄露 token、密码或私钥片段。
- 平台团队想把 shell history、git diff、pytest/JUnit、Markdown notes、JSONL transcript 合并成统一证据包。

## 安装

```bash
python -m pip install .
```

开发安装：

```bash
python -m pip install -e ".[dev]"
```

安装后会得到命令：

```bash
agent-session-recorder --help
```

## 快速工作流

```bash
agent-session-recorder init .asr/session-001 \
  --goal "修复支付回调重试逻辑并补充测试" \
  --title "payment callback retry"

agent-session-recorder add-file --session .asr/session-001 src/payment_retry.py --role changed-source

agent-session-recorder add-command --session .asr/session-001 \
  --cmd "pytest tests/test_payment_retry.py" \
  --exit-code 0 \
  --stdout "3 passed in 0.18s"

agent-session-recorder import-transcript --session .asr/session-001 pytest-output.txt --type pytest

agent-session-recorder summarize --session .asr/session-001

agent-session-recorder export --session .asr/session-001 \
  --format markdown \
  --output dist/session-001.md \
  --check

agent-session-recorder export --session .asr/session-001 \
  --format zip \
  --output dist/session-001.zip \
  --check
```

`--output` 会自动创建父目录。`--check` 会在导出前验证附件和导入文件的 SHA-256。

## 子命令

### `init`

创建 session 目录和 `manifest.json`。

```bash
agent-session-recorder init .asr/my-session --goal "实现审计 bundle 导出"
```

### `add-command`

记录命令、工作目录、退出码、stdout、stderr 和备注。stdout/stderr 可以直接传字符串，也可以从文件读取。

```bash
agent-session-recorder add-command --session .asr/my-session \
  --cmd "pytest" \
  --cwd "/repo/service" \
  --exit-code 0 \
  --stdout-file pytest-output.txt
```

### `add-file`

把上下文文件或证据附件复制进 bundle，并写入大小和哈希。

```bash
agent-session-recorder add-file --session .asr/my-session docs/agent-notes.md --role notes
```

### `import-transcript`

导入外部记录。支持：

- `transcript`: JSONL transcript
- `shell-history`: shell history
- `git-diff`: git diff/patch
- `pytest`: pytest 文本输出
- `junit`: JUnit XML
- `notes`: Markdown notes
- `auto`: 按文件名和扩展名推断

```bash
agent-session-recorder import-transcript --session .asr/my-session transcript.jsonl --type transcript
agent-session-recorder import-transcript --session .asr/my-session changes.diff --type git-diff
agent-session-recorder import-transcript --session .asr/my-session junit.xml --type junit
```

### `summarize`

生成离线、确定性的摘要、风险和后续项。它不会调用 LLM。

```bash
agent-session-recorder summarize --session .asr/my-session
```

### `export`

导出 Markdown、JSON 或 ZIP。

```bash
agent-session-recorder export --session .asr/my-session --format json --output out/session.json --check
```

ZIP 中包含：

- `session.json`
- `session.md`
- `SHA256SUMS`
- `bundle/` 下的完整 session 目录副本

### `check`

单独验证 bundle 完整性。

```bash
agent-session-recorder check --session .asr/my-session
```

## Bundle 结构

```text
session/
  manifest.json
  attachments/
  imports/
  evidence/
  exports/
```

`manifest.json` 记录 session 元数据、附件清单、导入清单、命令、摘要、风险、后续项和测试证据。附件和导入文件都会记录 SHA-256，用于后续完整性检查。

## Redaction 和隐私

工具默认会在写入 manifest、命令输出、导入记录和摘要前进行 redaction。内置规则覆盖：

- OpenAI 风格 key
- GitHub token
- AWS access key id
- Bearer token
- `password: ...`、`secret: ...`、`token: ...`、`api_key: ...`
- URL 中的用户名密码
- PEM private key block

也可以追加自定义正则：

```bash
agent-session-recorder --redact-pattern "internal-[0-9]{6}" add-command \
  --session .asr/my-session \
  --cmd "deploy --ticket internal-123456"
```

注意：redaction 是防护网，不是形式化安全证明。团队仍应在提交 bundle 前复查导出文件。

## CI

项目自带 GitHub Actions 配置，覆盖 Python 3.9 到 3.13：

```bash
pytest
```

CI 文件位于 `.github/workflows/ci.yml`。

## examples

`examples/` 里有可直接运行的 shell 和 PowerShell 示例，会生成一个本地 session、导入 JSONL/pytest/git diff，并导出 Markdown/JSON/ZIP。

## 限制

- 摘要是规则生成，不替代人工审阅。
- 目前不会解析真实终端数据库，只导入用户提供的 history 文本。
- JUnit 解析覆盖常见 `testsuite`/`testsuites` 结构。
- redaction 不能保证识别所有组织内部 secret 格式，建议用 `--redact-pattern` 补充规则。

## English

`agent-session-recorder` is an offline CLI for producing auditable bundles from AI coding agent work. It captures the user goal, context files, commands, test evidence, imported transcripts, summaries, risks, and follow-up items. The output can be attached to tickets, reviews, or internal audit records.

Key properties:

- Python 3.9+ with no runtime dependencies.
- Installable CLI: `agent-session-recorder`.
- Markdown, JSON, and ZIP exports.
- Built-in secret redaction.
- Manifest with SHA-256 hashes and integrity checks.
- Imports JSONL transcripts, shell history, git diff, pytest output, JUnit XML, and Markdown notes.

This tool is local-first. It does not publish bundles or send data to any service.
