import json
import logging
import threading
from collections.abc import Callable

from qibao_desktop.startup_progress import StartupProgress


logger = logging.getLogger(__name__)


def _close_boot_splash() -> None:
    try:
        import pyi_splash
    except ImportError:
        return
    try:
        pyi_splash.close()
    except Exception:
        logger.warning("failed to close boot splash", exc_info=True)


def _startup_html() -> str:
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{color-scheme:dark;font-family:"JetBrains Mono","Microsoft YaHei UI",monospace;background:#06080d;color:#d9e7ee}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:#06080d;overflow:hidden}.shell{display:grid;grid-template-columns:210px 1fr;min-height:100vh}.nav{border-right:1px solid #1a2b35;background:#080d13;padding:20px 14px}.brand{font:700 17px/1.4 Orbitron,"Microsoft YaHei UI",sans-serif;color:#f0c96a}.brand small{display:block;margin-top:5px;color:#58717e;font:10px/1.5 "JetBrains Mono",monospace}.nav i{display:block;height:34px;margin-top:24px;border-left:2px solid #31d7ca;background:#0b151c}.nav span{display:block;height:26px;margin-top:8px;border:1px solid #132630;background:#0a1118}.page{padding:18px}.top{height:78px;border:1px solid #1b313c;background:#091119;padding:15px}.top b{display:block;color:#e5edf1;font-size:20px}.top small{color:#66818e}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:10px}.grid span{height:70px;border:1px solid #142934;background:#081119}.boot{position:fixed;inset:0 0 0 210px;display:grid;place-items:center;background:rgba(4,8,12,.88);backdrop-filter:blur(3px)}.panel{width:min(660px,calc(100vw - 260px));border:1px solid #2c5661;background:#071017;padding:24px;box-shadow:0 0 34px rgba(32,217,202,.09)}.eyebrow{color:#35ddd0;font-size:10px}.panel h1{margin:8px 0 4px;color:#edcf79;font:700 22px/1.4 Orbitron,"Microsoft YaHei UI",sans-serif}.detail{margin:0;color:#7f99a5;font-size:12px}.meter{height:7px;margin:22px 0 10px;background:#10202a;overflow:hidden}.bar{width:12%;height:100%;background:#35ddd0;box-shadow:0 0 14px #35ddd0;transition:width .2s ease}.row{display:flex;justify-content:space-between;color:#b9cbd3;font-size:12px}.percent{color:#edcf79;font-size:18px}.scan{height:54px;margin-top:18px;position:relative;overflow:hidden;border-top:1px solid #132b35;border-bottom:1px solid #132b35;background:repeating-linear-gradient(90deg,transparent 0 31px,#10232b 32px)}.scan:after{content:"";position:absolute;inset:0;width:28%;background:linear-gradient(90deg,transparent,rgba(53,221,208,.25),transparent);animation:scan 1.4s linear infinite}@keyframes scan{from{transform:translateX(-110%)}to{transform:translateX(470%)}}@media(max-width:800px){.shell{grid-template-columns:72px 1fr}.brand{font-size:11px}.brand small{display:none}.boot{left:72px}.panel{width:calc(100vw - 100px)}.grid{grid-template-columns:repeat(2,1fr)}}@media(prefers-reduced-motion:reduce){.scan:after{animation:none}.bar{transition:none}}
.meter{position:relative}.bar{width:1%;position:relative;overflow:hidden;transition:width 40ms linear}.bar:after{content:"";position:absolute;inset:0 auto 0 -72px;width:72px;background:linear-gradient(90deg,transparent,#fff,transparent);animation:homepage-progress-tracer 1.15s linear infinite}@keyframes homepage-progress-tracer{to{transform:translateX(732px)}}@media(prefers-reduced-motion:reduce){.bar:after{animation:none}.bar{transition:none}}
</style></head><body><div class="shell"><aside class="nav"><div class="brand">一树-A股观测台<small>A-SHARE OBSERVATION TERMINAL</small></div><i></i><span></span><span></span><span></span><span></span><span></span></aside><main class="page"><header class="top"><small>A-SHARE / MARKET OVERVIEW</small><b>信息总览</b></header><section class="grid"><span></span><span></span><span></span><span></span></section></main></div><section class="boot" role="dialog" aria-label="正在启动一树电子商务-A股观测台"><div class="panel"><div class="eyebrow">DESKTOP STARTUP PIPELINE</div><h1>正在启动一树电子商务-A股观测台</h1><p class="detail" id="detail">桌面进程已初始化</p><div class="meter"><div class="bar homepage-progress-tracer" id="bar"></div></div><div class="row"><span id="step">准备本地运行环境</span><b class="percent" id="percent">1%</b></div><div class="scan"></div></div></section><script>let currentProgress=1,progressTarget=1,progressTimer=null;function renderProgress(){document.getElementById('bar').style.width=currentProgress+'%';document.getElementById('percent').textContent=currentProgress+'%'}function advanceProgress(){if(currentProgress>=progressTarget){clearInterval(progressTimer);progressTimer=null;return}currentProgress+=1;renderProgress()}window.qibaoStartup={update:function(value,step,detail,elapsed){progressTarget=Math.max(progressTarget,value);if(!progressTimer)progressTimer=setInterval(advanceProgress,20);document.getElementById('step').textContent=step;document.getElementById('detail').textContent=elapsed===null||elapsed===undefined?detail:detail+' · 阶段耗时 '+elapsed+'ms'},fail:function(detail){document.getElementById('step').textContent='启动失败';document.getElementById('detail').textContent=detail;document.getElementById('bar').style.background='#ff5f6d'}}</script></body></html>"""


def _startup_progress_script(progress: StartupProgress) -> str:
    step = json.dumps(progress.step, ensure_ascii=False)
    detail = json.dumps(progress.detail, ensure_ascii=False)
    elapsed = "null" if progress.elapsed_ms is None else str(progress.elapsed_ms)
    return f"window.qibaoStartup.update({progress.percent},{step},{detail},{elapsed})"


def run_window(
    start_application: Callable[[], str],
    *,
    startup_progress: Callable[[], StartupProgress | None] | None = None,
) -> None:
    try:
        import webview
    except ImportError as error:
        raise RuntimeError("pywebview is not installed") from error
    window = webview.create_window(
        "一树电子商务-A股观测台",
        html=_startup_html(),
        width=1500,
        height=920,
        min_size=(1080, 700),
        background_color="#06080d",
    )

    def load_application() -> None:
        _close_boot_splash()
        window.evaluate_js(
            "window.qibaoStartup.update(24,'桌面窗口已显示','正在等待本地 API 完成健康检查')"
        )
        stop_progress = threading.Event()
        progress_thread: threading.Thread | None = None
        if startup_progress is not None:
            def watch_progress() -> None:
                last_stage: str | None = None
                while not stop_progress.wait(0.08):
                    try:
                        progress = startup_progress()
                    except Exception:
                        logger.debug("desktop startup progress read failed", exc_info=True)
                        continue
                    if progress is None or progress.stage == last_stage:
                        continue
                    last_stage = progress.stage
                    window.evaluate_js(_startup_progress_script(progress))

            progress_thread = threading.Thread(
                target=watch_progress,
                name="qibao-startup-progress",
                daemon=True,
            )
            progress_thread.start()
        try:
            url = start_application()
        except Exception as error:
            stop_progress.set()
            if progress_thread is not None:
                progress_thread.join(timeout=1)
            logger.exception("local API failed while desktop shell was visible")
            message = json.dumps(f"本地 API 启动失败：{error}", ensure_ascii=False)
            window.evaluate_js(f"window.qibaoStartup.fail({message})")
            return
        stop_progress.set()
        if progress_thread is not None:
            progress_thread.join(timeout=1)
        window.evaluate_js(
            "window.qibaoStartup.update(42,'本地 API 已就绪','正在挂载首页资源与真实市场数据')"
        )
        window.load_url(f"{url}/?desktopBoot=42")

    webview.start(load_application, debug=False)
