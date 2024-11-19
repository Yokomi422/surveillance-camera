import SwiftUI

struct ContentView: View {
    @State private var isShowingFrames = false
    @State private var lastDetection: DetectionData?
    @State private var showAlert: Bool = false
    @State private var alertMessage: String = ""
    
    var body: some View {
        VStack {
            // ヘッダー
            HStack {
                Image(systemName: "person.circle")
                    .resizable()
                    .frame(width: 40, height: 40)
                    .padding()
                Spacer()
                Text("監視カメラ")
                    .font(.title2)
                    .fontWeight(.bold)
                Spacer()
                Image(systemName: "gearshape")
                    .resizable()
                    .frame(width: 30, height: 30)
                    .padding()
            }
            .padding(.horizontal)

            Spacer()

            // メインボタン
            VStack {
                Text("ようこそ")
                    .font(.headline)
                    .padding(.bottom, 10)
                Button(action: {
                    isShowingFrames = true
                }) {
                    Text("映像を表示")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                        .padding(.horizontal, 20)
                }
            }

            Spacer()

            // フッター（タブ風）
            HStack {
                VStack {
                    Image(systemName: "house.fill")
                    Text("ホーム")
                        .font(.footnote)
                }
                .frame(maxWidth: .infinity)

                VStack {
                    Image(systemName: "video.fill")
                    Text("映像")
                        .font(.footnote)
                }
                .frame(maxWidth: .infinity)

                VStack {
                    Image(systemName: "person.fill")
                    Text("プロフィール")
                        .font(.footnote)
                }
                .frame(maxWidth: .infinity)
            }
            .padding()
            .background(Color(.systemGray6))
        }
        .background(Color(.systemGroupedBackground).edgesIgnoringSafeArea(.all))
        .sheet(isPresented: $isShowingFrames) {
            FrameViewer()
        }
        .onAppear {
            startFetchingDetection()
        }
        .alert(isPresented: $showAlert) {
            Alert(title: Text("検出通知"), message: Text(alertMessage), dismissButton: .default(Text("OK")))
        }
    }

    func startFetchingDetection() {
        Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { _ in
            fetchDetectionData()
        }
    }

    func fetchDetectionData() {
        guard let url = URL(string: "http://localhost:8080/get_detection") else { return }

        URLSession.shared.dataTask(with: url) { data, response, error in
            if let error = error {
                print("検出データの取得エラー: \(error.localizedDescription)")
                return
            }

            guard let data = data else {
                print("検出データがありません")
                return
            }

            do {
                let detection = try JSONDecoder().decode(DetectionData.self, from: data)
                DispatchQueue.main.async {
                    if detection != lastDetection {
                        alertMessage = "ステータス: \(detection.status)\n詳細: \(detection.detail)"
                        showAlert = true
                        lastDetection = detection
                    }
                }
            } catch {
                print("検出データのデコードエラー: \(error.localizedDescription)")
            }
        }.resume()
    }
}

#Preview {
    ContentView()
}
