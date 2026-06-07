# Contributing

感谢你考虑贡献 `agent-session-recorder`。这个项目关注的是可审计、离线、低依赖的 AI 编程代理交付记录。

## 开发原则

- 标准库优先，新增运行时依赖需要有明确收益。
- 默认保护隐私，新增导入器和导出器必须经过 redaction。
- 输出格式要稳定，便于团队把 bundle 放进工单、审计系统或内部知识库。
- 测试覆盖应贴近真实工作流，而不仅是函数级 happy path。

## 本地开发

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
pytest
```

## Pull Request 检查清单

- 运行 `pytest`。
- 新增或改变 CLI 行为时更新 `README.md`。
- 不提交真实 token、密码、内部域名、个人邮箱或客户数据。
- 示例域名使用 `.test`。

## 版本策略

项目使用语义化版本。CLI 输出结构、bundle schema 或 manifest 校验规则改变时，应在 `CHANGELOG.md` 中说明迁移影响。
