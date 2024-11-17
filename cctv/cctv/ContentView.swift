import SwiftUI

struct ContentView: View {
    @State private var isShowingFrames = false

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
    }
}


#Preview {
    ContentView()
}
