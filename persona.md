# Persona

<!--
このファイルは paperfeed が毎朝の論文選定と紹介文の執筆に使う「読者像」です。
Claude はこのファイルを全文読んでから論文を選び、紹介文を書きます。
fork したら下の各節を自分の内容に書き換えてください（見出しはそのままでも、増やしても構いません）。
具体的に書くほど選定と「研究との関係」の質が上がります。

This file describes YOU, the reader. paperfeed reads it in full before picking
papers and writing the digests. Rewrite every section for yourself.
-->

## 言語 / Language
日本語

<!-- 紹介文を書く言語。例: 日本語 / English -->

## 立場
物理学専攻の修士1年。量子情報の研究室に所属。

## 主テーマ
<!-- 何を、どういう手法で調べているかを2〜3文で。当面の課題も書く -->
開放量子系におけるノイズ下での量子誤り訂正符号の性能を、テンソルネットワークを用いた数値シミュレーションで調べている。
当面の課題は、相関のあるノイズ（非マルコフ的なノイズ）に対する閾値の評価方法を確立すること。

## 関連分野
- 量子誤り訂正・フォールトトレラント量子計算
- 開放量子系・量子マスター方程式
- テンソルネットワーク法（MPS / PEPS）
- 量子計算向けの機械学習デコーダ

## 既に読んだ主要な先行研究
<!-- ここに書いた論文は紹介されなくなる -->
- Dennis, Kitaev, Landahl, Preskill, "Topological quantum memory" (2002)
- Bravyi, Suchara, Vargo, "Efficient algorithms for maximum likelihood decoding in the surface code" (2014)

## 対象外
<!-- 読みたくない種類の論文 -->
- 実験装置の工学的な詳細だけを扱う論文
- 量子暗号・量子通信プロトコル

## 紹介文の書き方
- 文体: 常体。比喩を使わない。強い語で誇張しない。
- 手法の節では主要な式を1〜3本、論文の式番号を添えて説明する。
- 機械学習の論文では、入力と出力、学習データ、損失関数を明記する。
- 「研究との関係」は、上の主テーマのどこにどう使えるかを具体的に書く。
