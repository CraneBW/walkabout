# Changelog

## [Unreleased]

### Fixed

- **端口冲突导致 `[Errno 98] address already in use`**
  - `webview.py`: 移除 `open_window()` 中内嵌的 uvicorn 服务启动逻辑（#6ae2f2c），避免与 `__main__.py` 的服务器线程争夺端口。
  - `__main__.py`: 预创建 TCP socket 并设置 `SO_REUSEADDR` 选项（#8c4f3b1），消除 TIME-WAIT 状态导致的端口绑定失败。重构服务器启动流程，统一由 `_run_server()` 管理，消除重复的 `uvicorn.run()` 调用。
  - 影响文件: `walkabout/__main__.py`, `walkabout/webview.py`

- **Conda 环境 libstdc++/libgcc_s 版本过旧**
  - 将 `libstdc++.so.6` 从 6.0.29 更新至系统版本 6.0.35，解决 `GLIBCXX_3.4.30 not found` 导致 GTK 原生窗口加载失败的问题。
  - 同步更新 `libgcc_s.so.1` 以匹配系统 GCC 版本，消除 `GCC_12.0.0 not found` 错误。
  - 修复命令:
    ```bash
    conda install -n deeplearning -c conda-forge libstdcxx-ng --update-deps
    # 或手动替换:
    cp /usr/lib/libstdc++.so.6 ~/.conda/envs/deeplearning/lib/libstdc++.so.6.0.35
    cp /usr/lib/libgcc_s.so.1 ~/.conda/envs/deeplearning/lib/libgcc_s.so.1
    ```
