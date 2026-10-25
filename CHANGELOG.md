# 更新
## v1.5.0 (2026-10-25)
### 重构
- 按面向对象分层重构：`main.py` 只保留 `Star` 子类与指令声明，业务实现下沉到 `rollpig/` 包（config / models / storage / repository / fonts / typography / renderer / service / targeting / presenter）。
- 卡片渲染改为「内容块组合 + 纵向居中布局」：`ContentBlock` 家族只负责自测量与自绘，`PigCardRenderer` 只负责排布与落盘；画布尺寸、字号、间距、配色收敛为不可变规格对象 `CanvasSpec`，消除散落的魔法数字。
- 字体加载改为模板方法基类 + 声明式候选表，新增字体只需增加一个子类。
- 持久化拆分为 `JsonStore`（通用 JSON 读写）与 `DailyBoardStore`（日期校验与结构转换）。
- 抽签逻辑抽出 `RollPigService`，时间源与随机源可注入，便于测试每日刷新。
- 渲染结果与交互行为保持不变：全部 96 个素材的卡片输出逐像素一致（Pillow 10.4 / 12.3 双环境校验）。

### 修复
- 开启 `at_view_pig` 后，指令带额外文本但消息中并没有 `@` 段时，原实现会抛 `IndexError`；现按「抽自己」处理。

## v1.4.1 (2026-10-25)
### 修复
- 修复渲染小猪图片时报 `TypeError: 'float' object cannot be interpreted as an integer` 的崩溃

## v1.4.0 (2026-10-25)
### 新增
- 新增配置项 `at_reply_user`，可控制群聊回复今日小猪时是否 @ 抽到小猪的用户。
- 「今日小猪」命令新增 `pig` 别名。

## v1.3.0 (2026-07-25)
### 新增
- 新增多款小猪形象素材，丰富随机抽取结果池。
