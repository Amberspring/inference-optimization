# 上传 GitHub

这是独立项目，不依赖生成项目时的 work/ 目录。仓库尚未发布到远程。
已初始化的本地仓库可以在 GitHub Desktop 中通过 Add local repository 导入，然后选择 Publish repository。
若使用 zip，先解压，然后在项目目录执行：

```sh
git init -b main
git add .
git commit -m "Implement verified CPU project and experiment reports"
```

在 GitHub 新建空仓库后，按页面提供的 remote/push 命令上传。请使用你自己的仓库地址和作者身份。
不要上传 .env、密钥、大模型权重或客户数据。artifacts/、models/ 和本地缓存已加入 .gitignore；results/ 是可审阅的实际测试和实验记录。
此项目由 AI 辅助实现，建议如实说明辅助方式；不要声称全部代码独立手写或把未执行实验说成已经完成。
