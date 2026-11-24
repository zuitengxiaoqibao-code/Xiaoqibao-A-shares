# 第三方软件、模型与数据

本项目的 [LICENSE](LICENSE) 仅适用于有权按该许可授权的项目内容，不替代第三方原许可，不限制第三方原许可独立授予的权利。

## 主要组件

| 组件 | 用途 | 许可说明 |
| --- | --- | --- |
| React、Vite、TypeScript、FastAPI、Pydantic、DuckDB、SQLAlchemy、mootdx | 界面、API、存储与数据适配 | 保留各自 MIT 等原始许可，以对应版本随附文件为准 |
| pywebview、HTTPX、Uvicorn、pandas | 桌面容器、网络与数据处理 | 保留各自 BSD 等原始许可 |
| ECharts、exchange-calendars、AxData | 图表、交易日历与适配器 | 保留各自 Apache-2.0 等原始许可及声明 |
| eltdx 3.3.5 | 通达信日线适配 | 使用其非商业学习与数据研究许可；商业用途须另行取得相关权利人的授权 |
| edge-tts 7.3.1 | 在线语音合成 | 主体 LGPLv3，srt_composer.py 使用 MIT；原许可随包保留。项目未修改此依赖源码 |
| Python、PyInstaller、WebView2、字体及其他传递依赖 | 运行时、打包、网页容器、显示 | 遵守各组件自己的条款，不能统一改为本项目许可 |

依赖项目：

- eltdx：<https://github.com/electkismet/eltdx>
- AxData：<https://github.com/electkismet/AxData>
- mootdx：<https://github.com/mootdx/mootdx>
- edge-tts：<https://github.com/rany2/edge-tts>
- pywebview：<https://github.com/r0x0r/pywebview>

公开便携目录中的 THIRD_PARTY_LICENSES 保存构建环境中运行依赖的版本、项目地址和随附许可文件；_internal、前端资源自身已有的版权与许可声明继续保留。此说明不是逐个依赖许可文本的替代品。修改、重新打包或商业部署时，须重新检查实际版本及其许可义务。

源码中依赖通过标准包管理器安装。edge-tts 等依赖的原始源码可从对应项目及 Python 包索引获取；开发者可在自己的环境中替换兼容版本后重新构建，不应以本项目的非商业许可限制原依赖自身允许的行为。

## 模型与数据

Kronos 源码与权重由用户另行获取，并适用相应项目和具体模型的许可。公开便携包不附带模型权重。

腾讯、通达信、东方财富、百度、巨潮、同花顺等行情、财务、公告与资讯来源，以及内嵌网页，均归相关权利人所有。公开源码不等于取得数据采集、服务访问、数据再分发或商业使用许可。用户应按来源要求取得授权，不绕过访问限制。

项目商业授权不包含第三方软件、数据、新闻、模型或网页的商业授权。
