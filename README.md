# xyzrss

将小宇宙（Xiaoyuzhou）RSS 转换为兼容 Anytime Player 的 RSS。

本项目专门针对部分 Anytime Player 对小宇宙 RSS 中 `audio/mp4` enclosure MIME type 兼容性不佳的问题，将：

```text
audio/mp4
```

转换为：

```text
audio/x-m4a
```

## 添加播客

编辑：

```text
feeds.txt
```

格式：

```text
FEED_ID # Podcast Name
```

例如：

```text
6xkltdh9kfav # 历史学人
```

提交后 GitHub Actions 会自动生成：

```text
docs/6xkltdh9kfav.xml
```

对应的 RSS 地址为：

```text
https://x-claire-lin.github.io/xyzrss/6xkltdh9kfav.xml
```

## 更新频率

GitHub Actions 默认每两小时运行一次。

也可以在：

```text
GitHub → Actions → Update Xiaoyuzhou RSS
```

手动运行。

如果填写 Feed ID：

```text
6xkltdh9kfav
```

则只更新这个节目。

如果留空，则更新全部节目。

## 网页

GitHub Pages 页面：

```text
https://x-claire-lin.github.io/xyzrss/
```

网页可以：

* 查看当前播客列表
* 复制 RSS URL
* 打开 RSS
* 选择多个播客
* 生成 OPML
* 根据小宇宙 RSS 地址生成 `feeds.txt` 配置

## License

MIT

