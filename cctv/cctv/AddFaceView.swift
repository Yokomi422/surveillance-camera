import SwiftUI

// Dataに文字列を追加するための拡張
extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
}

struct AddFaceView: View {
    @Environment(\.presentationMode) var presentationMode
    @State private var selectedImage: UIImage?
    @State private var showImagePicker: Bool = false
    @State private var inputImage: UIImage?
    @State private var name: String = ""
    @State private var isSaving: Bool = false
    @State private var saveSuccess: Bool = false
    @State private var imageSource: UIImagePickerController.SourceType = .photoLibrary // デフォルトの画像ソース

    // カスタムイニシャライザ
    init(selectedImage: UIImage? = nil, name: String = "") {
        _selectedImage = State(initialValue: selectedImage)
        _name = State(initialValue: name)
    }

    var body: some View {
        NavigationView {
            VStack {
                // 画像表示エリア
                ZStack {
                    Rectangle()
                        .fill(Color.secondary.opacity(0.2))
                        .frame(height: 200)
                        .cornerRadius(10)

                    if let image = selectedImage {
                        Image(uiImage: image)
                            .resizable()
                            .scaledToFit()
                            .cornerRadius(10)
                            .padding()
                    } else {
                        Image("default_face") // Assetsに追加したデフォルト画像を表示
                            .resizable()
                            .scaledToFit()
                            .cornerRadius(10)
                            .padding()
                            .opacity(0.6) // 必要に応じて透過度を調整
                    }
                }
                .padding()

                // 「写真を選択」と「その場で写真を撮る」ボタン
                HStack(spacing: 20) {
                    Button(action: {
                        self.imageSource = .photoLibrary
                        self.showImagePicker = true
                    }) {
                        HStack {
                            Image(systemName: "photo.on.rectangle")
                            Text("写真を選択")
                        }
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                    }

                    Button(action: {
                        self.imageSource = .camera
                        self.showImagePicker = true
                    }) {
                        HStack {
                            Image(systemName: "camera")
                            Text("写真を撮る")
                        }
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(Color.green)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                    }
                }
                .padding(.horizontal)

                // 名前入力フィールド
                Form {
                    Section(header: Text("名前")) {
                        TextField("名前を入力", text: $name)
                    }
                }
                .padding(.horizontal)

                Spacer()

                // 保存ボタン
                Button(action: saveFace) {
                    HStack {
                        Spacer()
                        if isSaving {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        } else {
                            Text("顔を登録")
                                .font(.headline)
                        }
                        Spacer()
                    }
                    .padding()
                    // 名前が入力されていれば青色、そうでなければ灰色
                    .background(!name.isEmpty ? Color.blue : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                    .padding(.horizontal)
                }
                // 名前が入力されているか、保存中かでボタンを無効化
                .disabled(name.isEmpty || isSaving)
            }
            .navigationBarTitle("顔の登録", displayMode: .inline)
            .navigationBarItems(trailing: Button("キャンセル") {
                presentationMode.wrappedValue.dismiss()
            })
            .sheet(isPresented: $showImagePicker, onDismiss: loadImage) {
                ImagePicker(image: self.$inputImage, sourceType: self.imageSource)
            }
            .alert(isPresented: $saveSuccess) {
                Alert(title: Text("成功"), message: Text("顔が正常に登録されました。"), dismissButton: .default(Text("OK")) {
                    presentationMode.wrappedValue.dismiss()
                })
            }
        }
    }

    func saveFace() {
        // selectedImage が nil の場合はデフォルト画像を使用
        guard let image = selectedImage ?? UIImage(named: "default_face") else {
            print("デフォルト画像が見つかりません。")
            return
        }

        guard let imageData = image.jpegData(compressionQuality: 0.8) else {
            print("画像データの取得に失敗しました。")
            return
        }

        isSaving = true

        // サーバーのURLを指定
        guard let url = URL(string: "http://localhost:8080/register_face") else {
            print("Invalid server URL")
            isSaving = false
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // 名前のパート
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"name\"\r\n\r\n")
        body.append("\(name)\r\n")

        // 画像のパート
        body.append("--\(boundary)\r\n")
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"\(name).jpg\"\r\n")
        body.append("Content-Type: image/jpeg\r\n\r\n")
        body.append(imageData)
        body.append("\r\n")

        body.append("--\(boundary)--\r\n")

        request.httpBody = body

        // リクエストの送信
        URLSession.shared.dataTask(with: request) { data, response, error in
            DispatchQueue.main.async {
                self.isSaving = false
            }

            if let error = error {
                print("Error during face registration: \(error.localizedDescription)")
                return
            }

            guard let httpResponse = response as? HTTPURLResponse else {
                print("Invalid response")
                return
            }

            if httpResponse.statusCode == 200 {
                DispatchQueue.main.async {
                    self.saveSuccess = true
                }
            } else {
                print("Failed to register face: \(httpResponse.statusCode)")
                if let data = data, let message = String(data: data, encoding: .utf8) {
                    print("Error message: \(message)")
                }
            }
        }.resume()
    }

    func loadImage() {
        guard let inputImage = inputImage else { return }
        selectedImage = inputImage
    }

    struct AddFaceView_Previews: PreviewProvider {
        static var previews: some View {
            AddFaceView()
                .previewDevice("iPhone 14")
                .previewDisplayName("AddFaceView Preview")
        }
    }
}

