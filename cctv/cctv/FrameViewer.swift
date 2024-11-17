import SwiftUI

struct FrameViewer: View {
    @Environment(\.presentationMode) var presentationMode
    @State private var currentFrame: UIImage?
    @State private var timer: Timer?

    var body: some View {
        VStack {
            if let image = currentFrame {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
            } else {
                Text("映像を読み込み中...")
            }
        }
        .onAppear {
            startFetchingFrames()
        }
        .onDisappear {
            stopFetchingFrames()
        }
        .navigationBarItems(trailing: Button("閉じる") {
            presentationMode.wrappedValue.dismiss()
        })
    }

    func startFetchingFrames() {
        timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { _ in
            fetchLatestFrame()
        }
    }

    func stopFetchingFrames() {
        timer?.invalidate()
        timer = nil
    }

    func fetchLatestFrame() {
        guard let url = URL(string: "http://localhost:8080/get_frame") else { return }

        URLSession.shared.dataTask(with: url) { data, response, error in
            if let data = data, let uiImage = UIImage(data: data) {
                DispatchQueue.main.async {
                    self.currentFrame = uiImage
                }
            }
        }.resume()
    }
}
