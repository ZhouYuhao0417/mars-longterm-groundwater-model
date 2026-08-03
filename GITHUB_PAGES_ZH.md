# GitHub Pages 发布

## 上传内容

把本目录中的全部文件上传到一个 GitHub 仓库的默认分支。`index.html` 必须位于仓库根目录。

## 开启页面

在 GitHub 仓库中依次打开：

1. `Settings`
2. `Pages`
3. `Build and deployment`
4. `Source: Deploy from a branch`
5. 选择默认分支和 `/ (root)`
6. 保存

几分钟后，GitHub 会显示公开网址。`.nojekyll` 已包含在发布包中，不需要构建工具。

## 公开前检查

- 把 `CITATION.cff` 中的团体作者替换为论文作者，并补充 DOI 和仓库网址；
- 根据 DEM、影像和代码授权情况选择许可证；
- 确认中情景仍被标明为未完成，未被写成定量空间结果；
- 在论文或仓库中注明交互页是体积映射展示，完成运行的 JSON 和栅格才是定量来源。

页面完全自包含，GitHub Pages 不需要额外依赖或服务器端程序。
