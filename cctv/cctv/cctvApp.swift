/*
 - 顔認証ようの顔を登録
    - Python Serverがもう一つ必要
 - 認証された顔以外 -> 通知
 - サーバをPythonで書き換え
 - モザイク処理の実装 プライバシーモード
 */

import SwiftUI

@main
struct cctvApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

#Preview {
    ContentView()
}
