import SwiftUI
import Vision
import CoreImage
import CoreImage.CIFilterBuiltins

// UIImageの向きをCGImagePropertyOrientationに変換する拡張
extension CGImagePropertyOrientation {
    init(_ uiOrientation: UIImage.Orientation) {
        switch uiOrientation {
        case .up: self = .up
        case .down: self = .down   // 180 deg rotation
        case .left: self = .left   // 90 deg CCW
        case .right: self = .right // 90 deg CW
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
    
    @State private var lastDetection: DetectionData? // 前回の検出データ
    @State private var showAlert: Bool = false
    @State private var alertMessage: String = ""
    
    // 画像処理用のコンテキスト
    let ciContext = CIContext()

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
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .cornerRadius(10)
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
            
            Spacer()
            
            // ボタンとステータスバー
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
        .alert(isPresented: $showAlert) {
            Alert(title: Text("検出通知"), message: Text(alertMessage), dismissButton: .default(Text("OK")))
        }
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
                // 顔検出とモザイク処理を行う
                if let processedImage = self.detectAndBlurFaces(in: uiImage) {
                    DispatchQueue.main.async {
                        self.currentFrame = processedImage
                        self.statusMessage = "映像取得成功"
                    }
                } else {
                    // 処理が失敗した場合、元の画像を表示
                    DispatchQueue.main.async {
                        self.currentFrame = uiImage
                        self.statusMessage = "映像取得成功（モザイク未適用）"
                    }
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

    func toggleRecording() {
        isRecording.toggle()
        statusMessage = isRecording ? "録画中..." : "待機中..."
    }

    func detectAndBlurFaces(in image: UIImage) -> UIImage? {
        guard let ciImage = CIImage(image: image) else { return nil }

        // 画像の向きを取得して変換
        let cgOrientation = CGImagePropertyOrientation(image.imageOrientation)

        // 顔検出のリクエストを作成
        let faceDetectionRequest = VNDetectFaceRectanglesRequest()

        // ハンドラを作成（画像の向きを指定）
        let handler = VNImageRequestHandler(ciImage: ciImage, orientation: cgOrientation, options: [:])

        do {
            // 顔検出を実行
            try handler.perform([faceDetectionRequest])

            // 検出された顔の矩形を取得
            if let results = faceDetectionRequest.results as? [VNFaceObservation], !results.isEmpty {
                print("Number of faces detected: \(results.count)")

                var maskedImage = ciImage
                let imageSize = ciImage.extent.size

                for face in results {
                    // 顔の矩形を取得
                    let boundingBox = face.boundingBox

                    // 座標を変換
                    let faceRect = CGRect(
                        x: boundingBox.origin.x * imageSize.width,
                        y: boundingBox.origin.y * imageSize.height,
                        width: boundingBox.size.width * imageSize.width,
                        height: boundingBox.size.height * imageSize.height
                    )

                    // 顔部分を切り抜き
                    let faceImage = maskedImage.cropped(to: faceRect)

                    // モザイク（ピクセレート）フィルターを適用
                    let pixelateFilter = CIFilter.pixellate()
                    pixelateFilter.inputImage = faceImage
                    pixelateFilter.scale = 20  // モザイクの粗さを調整

                    guard let pixelatedFace = pixelateFilter.outputImage else { continue }

                    // 顔部分の位置に合わせてピクセレートされた顔画像を移動
                    let transform = CGAffineTransform(translationX: faceRect.origin.x, y: faceRect.origin.y)
                    let transformedPixelatedFace = pixelatedFace.transformed(by: transform)

                    // モザイク処理した顔を元の画像に合成
                    maskedImage = transformedPixelatedFace.composited(over: maskedImage)
                }

                // 画像を生成（元の画像の向きを保持）
                if let cgImage = ciContext.createCGImage(maskedImage, from: maskedImage.extent) {
                    return UIImage(cgImage: cgImage, scale: image.scale, orientation: image.imageOrientation)
                }
            } else {
                print("No faces detected.")
                return image
            }
        } catch {
            print("Failed to perform face detection: \(error)")
            // エラーが発生した場合、元の画像を返す
            return image
        }

        return nil
    }
}

#Preview {
    FrameViewer()
}
