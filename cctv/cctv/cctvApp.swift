/*
 - 顔認証ようの顔を登録
    - Python Serverがもう一つ必要
 - 認証された顔以外 -> 通知
 - サーバをPythonで書き換え
 - モザイク処理の実装 プライバシーモード
 
 - 何を頑張ったか
    - コンセプトは簡単に
    - 作成時に何を頑張ったかの方が大切
    - 最初にデモをやる
    - スライドに長文を書かない.
    - 試行錯誤の過程を言うと良い
    - 1 slideには1 message
    - animationはなくても可
    - ハキハキ喋って堂々という. 大きな声で
 */

import SwiftUI

@main
struct cctvApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

#Preview {
    ContentView()
}
