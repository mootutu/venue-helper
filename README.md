# 深大体育场馆 WebUI 预约助手

项目现在只保留 Streamlit 交互式预约入口。Cookie、学号和姓名只在当前页面会话中使用，不写入仓库。

## 启动

开发环境：

```powershell
uv sync
uv run streamlit run app.py
```

也可以直接双击打包好的 Windows 程序 `dist/深大场馆预约.exe`。它会自动打开浏览器，不需要再运行 `uv run`。黑色控制台窗口请保持打开；日志和本机姓名/学号缓存会写在 exe 旁边。

重新打包：

```powershell
uv sync --group dev
uv run pyinstaller --noconfirm venue-helper.spec
```

启动后先在登录页面填写姓名、学号和 ehall Cookie（姓名与学号首次填写后会保存在本机的 `.venue_profile.json`，该文件已被 Git 忽略），点击“登录并进入预约”。验证成功后才会显示预约工作区，按“校区 → 场馆 → 日期 → 查询预约时段”的顺序操作。持续轮询支持限次模式，也支持无限轮询直到预约成功；页面提供“停止预约”按钮，收到停止请求后会在当前网络请求结束后停止轮询。Cookie 不会写入本地。

## 安全说明

- 不要把 Cookie 写入 `settings.py`、`user.yaml` 或提交到 Git。
- Cookie 失效时重新从浏览器开发者工具复制请求头中的 Cookie。
- 预约成功后仅弹出一次成功提示；操作日志不在页面展示，仍写入 `OPERATION_LOG.md`，且不记录完整 Cookie。

## 项目结构

- `app.py`：Streamlit WebUI 和预约流程
- `apis.py`：接口访问、超时、响应校验和错误日志
- `settings.py`：非敏感默认配置及环境变量读取
- `launcher.py`：打包后的启动入口
- `venue-helper.spec`：PyInstaller 打包配置
- `OPERATION_LOG.md`：操作进度和运行日志


## 安全说明

- 不要把 Cookie 写入 `settings.py`、`user.yaml` 或提交到 Git。
- Cookie 失效时重新从浏览器开发者工具复制请求头中的 Cookie。
- 预约成功后仅弹出一次成功提示；操作日志不在页面展示，仍写入 `OPERATION_LOG.md`，且不记录完整 Cookie。

## 项目结构

- `app.py`：Streamlit WebUI 和预约流程
- `apis.py`：接口访问、超时、响应校验和错误日志
- `settings.py`：非敏感默认配置及环境变量读取
- `OPERATION_LOG.md`：操作进度和运行日志
