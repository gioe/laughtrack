import SwiftUI

struct AuthLoadingView: View {
    var body: some View {
        ZStack {
            Color("LaunchBackground")
                .ignoresSafeArea()
            Image("LaunchLogo")
                .resizable()
                .scaledToFit()
                .frame(width: 180, height: 180)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
