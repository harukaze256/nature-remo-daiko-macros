# Nature Remo / DAIKO macro generator

DAIKOの独自BLEサービス向けに、Nature Remo機器拡張マクロのXMLをローカル生成するツールです。Python 3.9以上の標準ライブラリだけで動作します。

公開ソースには実機の接続コード、Bluetoothアドレス、器具固有名、LANアドレス、アクセストークン、利用者名、ローカルパスを含めません。`*.xml.template`には実行用データを持たないテンプレートだけを置いています。

## ローカル生成

リポジトリの外に非公開JSON設定を用意します。設定項目は次のとおりです。

| キー | 内容 |
|---|---|
| `sid` | 必須。実機から取得した5桁のASCII接続コード |
| `last_color` | 任意。13〜240の光色値。既定値13 |
| `last_brightness` | 任意。13〜240の明るさ値。既定値240 |

設定ファイルと出力先の両方をソースディレクトリ外に指定します。

```text
python generate.py --settings <PRIVATE_SETTINGS_JSON> --output <PRIVATE_OUTPUT_DIRECTORY>
```

既存の出力ファイルは上書きしません。ネットワークへの送信は行いません。接続コードをコマンドライン引数や環境変数へ直接入れる必要もありません。

## 公開範囲とNature Homeへの登録

**生成した`on.xml`と`off.xml`には、接続コードが16進数の送信データとして含まれます。これらは非公開ファイルです。ソースコードが設定を外部化していても、生成済みXMLの公開が安全になるわけではありません。**

Nature公式の標準手順は「PUBLIC GITHUB URL」からマクロXMLを登録する方式です。このリポジトリの未置換テンプレートをそのまま登録しても実機は操作できません。接続コードを公開しない条件での登録経路は、別途検証が必要です。

## 通信内容

独自サービス`ffb0`の`ffb2`に20バイトをWrite With Responseで送信します。先頭5バイトはASCIIの接続コード、制御バイトは`c0`です。消灯は明るさ`ff`を用い、点灯はローカル設定値を使います。

ONの明るさ・光色は生成時に固定されます。フレーム内の時刻も生成時の値になるため、照明タイマーとの併用は未検証です。機種ごとの通信仕様・適合性は利用する実機で確認してください。

## テスト

```text
python -m unittest -v test_generate
```

テストは合成データを使い、実機やネットワークへ接続しません。

## 公式資料

- [Natureの機器拡張マクロ公開告知](https://nature.global/press/news/18867/)
- [Natureの登録手順](https://engineering.nature.global/entry/introduce-device-extension-macro)
- [Natureのマクロ操作仕様](https://engineering.nature.global/entry/ble-macro-beta-operation)

本ツールはNature・DAIKOの公式製品ではありません。
