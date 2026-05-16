import SwiftUI

struct AuthLoadingView: View {
    let logoNamespace: Namespace.ID

    var body: some View {
        ZStack {
            Color("LaunchBackground")
                .ignoresSafeArea()
            Image("LaunchLogo")
                .resizable()
                .scaledToFit()
                .frame(width: 180, height: 180)
                .matchedGeometryEffect(id: "launch-logo", in: logoNamespace)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
