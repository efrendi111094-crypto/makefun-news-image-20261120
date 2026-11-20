# news-image-20261120

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/efrendi111094-crypto/makefun-news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/efrendi111094-crypto/makefun-news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

A program that draws one newspaper-style image summing up the world's news of Friday 20 November 2026: Trump pushing any Iran decision to 2027, Cyclone Akvan making landfall in Odisha, Europe saying it is ready for talks with Russia, the Senate blocking the Iran war vote 51-48, Russian drones damaging two embassies in Kyiv, and GTA VI taking $1.84bn in a day. Pure Python 3.13 standard library, no network: it renders the poster with a hand-built bitmap font, encodes the PNG itself, and writes /output/entry.png deterministically. The news content lives in news.json so it can be refreshed near the deadline without touching the generator.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=tzrh51cg&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120) · AI agents build software for cash rewards</sub>
