import SwiftUI
import Vision
import CoreImage
import CoreImage.CIFilterBuiltins

extension CGImagePropertyOrientation {
    init(_ uiOrientation: UIImage.Orientation) {
        switch uiOrientation {
        case .up: self = .up
        case .down: self = .down
        case .left: self = .left
        case .right: self = .right
        case .upMirrored: self = .upMirrored
        case .downMirrored: self = .downMirrored
        case .leftMirrored: self = .leftMirrored
        case .rightMirrored: self = .rightMirrored
        @unknown default:
            self = .up
        }
    }
}

struct DetectionData: Codable, Equatable {
    let status: String
    let detail: String
}

struct FrameViewer: View {
    @Environment(\.presentationMode) var presentationMode
    @State private var currentFrame: UIImage?
    @State private var timer: Timer?
    @State private var isRecording: Bool = false
    @State private var statusMessage: String = "映像を読み込み中..."
    
    @State private var lastDetection: DetectionData?
    @State private var backgroundChanged: Bool = false  // 背景の変化を追跡する変数を追加
    
    let ciContext = CIContext()
    
    @State private var imageScale: CGFloat = 1.0

    var body: some View {
        VStack {
            // タイトル
            Text("Surveillance Viewer")
                .font(.headline)
                .padding()
            
            Divider()
            
            // 映像表示
            ZStack {
                if let image = currentFrame {
                    GeometryReader { geometry in
                        Image(uiImage: image)
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .scaleEffect(imageScale)
                            .frame(width: geometry.size.width, height: geometry.size.height)
                            .gesture(
                                MagnificationGesture()
                                    .onChanged { value in
                                        self.imageScale = value.magnitude
                                    }
                            )
                    }
                    .padding()
                } else {
                    VStack {
                        ProgressView() // ローディングインジケーター
                        Text(statusMessage)
                            .font(.subheadline)
                            .foregroundColor(.gray)
                            .padding(.top)
                    }
                }
            }
            .background(Color.black.opacity(0.1))
            .cornerRadius(10)
            .padding()
            
            if currentFrame != nil {
                HStack {
                    Text("画像サイズ")
                    Slider(value: $imageScale, in: 0.5...3.0, step: 0.1)
                        .padding()
                }
                .padding(.horizontal)
            }
            
            Spacer()
            
            // 背景変化を示すランプを追加
            HStack {
                Spacer()
                Circle()
                    .fill(self.backgroundChanged ? Color.red : Color.green)
                    .frame(width: 20, height: 20)
                Spacer()
            }
            .padding()
            
            HStack {
                Button(action: toggleRecording) {
                    HStack {
                        Image(systemName: isRecording ? "stop.circle.fill" : "video.circle.fill")
                        Text(isRecording ? "録画停止" : "録画開始")
                    }
                    .font(.headline)
                    .padding()
                    .background(isRecording ? Color.red.opacity(0.7) : Color.blue.opacity(0.7))
                    .foregroundColor(.white)
                    .cornerRadius(10)
                }
                
                Spacer()
                
                Button("閉じる") {
                    presentationMode.wrappedValue.dismiss()
                }
                .font(.headline)
                .padding()
                .background(Color.gray.opacity(0.7))
                .foregroundColor(.white)
                .cornerRadius(10)
            }
            .padding()
        }
        .onAppear {
            startFetchingFrames()
            startFetchingDetection()
        }
        .onDisappear {
            stopFetchingFrames()
        }
        .background(Color(UIColor.systemGroupedBackground))
        .navigationBarHidden(true) // ナビゲーションバーを非表示
    }
    // フレームを取得するタイマー
    func startFetchingFrames() {
        timer = Timer.scheduledTimer(withTimeInterval: 0.033, repeats: true) { _ in
            fetchLatestFrame()
        }
    }

    func stopFetchingFrames() {
        timer?.invalidate()
        timer = nil
    }

    // フレームを取得する関数
    func fetchLatestFrame() {
        guard let url = URL(string: "http://localhost:8080/get_frame") else { return }

        URLSession.shared.dataTask(with: url) { data, response, error in
            if let data = data, let uiImage = UIImage(data: data) {
                DispatchQueue.main.async {
                    self.currentFrame = uiImage
                    self.statusMessage = "映像取得成功"
                }
            } else if let error = error {
                DispatchQueue.main.async {
                    self.statusMessage = "映像取得エラー: \(error.localizedDescription)"
                }
            }
        }.resume()
    }
    
    // 検出データを取得するタイマー
    func startFetchingDetection() {
        Timer.scheduledTimer(withTimeInterval: 5.0, repeats: true) { _ in
            fetchDetectionData()
        }
    }
    
    // 検出データを取得する関数
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
                    // 背景の変化をチェックし、ランプの色を変更
                    self.backgroundChanged = detection.status != "no difference detected"
                    self.lastDetection = detection
                }
            } catch {
                print("検出データのデコードエラー: \(error.localizedDescription)")
            }
        }.resume()
    }

    func toggleRecording() {
        isRecording.toggle()
        statusMessage = isRecording ? "録画中..." : "待機中..."
    }
}

#Preview {
    FrameViewer()
}
