# 单 case 录屏工具（按需触发，与 ugc-publisher skill 无关）

用途：执行 test-cases.md 中某条 case 时，按需录制"浏览器端 + 命令行"全过程。
原理：ZCode 应用内的 IAB 浏览器与命令行回显在同一个窗口，ffmpeg 全屏录制一路即同框覆盖两端。

## 用法

```bash
./recordings/rec-start.sh <case-id>   # 开始，如 ./recordings/rec-start.sh case05
# …执行该 case（手动或让 agent 跑）…
./recordings/rec-stop.sh              # 结束，产物 recordings/<时间戳>_<case-id>.mp4
```

- 只在明确要录的时候用；不录屏时这两个脚本完全不参与任何流程。
- 双显示器：第二个参数指定 avfoundation 屏幕索引，如 `rec-start.sh case05 2`；
  索引查看：`ffmpeg -hide_banner -f avfoundation -list_devices true -i ""`。
- 特性：24fps H.264（crf 23）、含鼠标指针、SIGINT 优雅收尾（mp4 可直接播放）、
  1 小时安全上限、pidfile 防重复录制；`recordings/*.mp4` 已 gitignore。

## 备选：只要浏览器画面（零权限，≤90 秒）

browser-use 插件原生 `tab.recording`（node_repl：`recordingStart / recordingStatus /
recordingCancel`），输出 webm，不需要 ffmpeg 与屏幕录制权限；单条硬上限 90 秒，
长流程需分段录制后用 ffmpeg concat 合并。详见插件 `docs/recording.md`。

## 已验证（2026-09-19，macOS 25.6 / ffmpeg 8.1.2）

- 3 秒试录：1080p、73 帧、可正常播放，抽帧为真实画面（非黑屏）。
- avfoundation 会打印 "Selected pixel format (yuv420p) is not supported by the input
  device"，属格式协商警告，exit=0、编码正常，可忽略。
- 换机器首次使用若弹「屏幕录制」系统授权，允许宿主 App 一次即可。
