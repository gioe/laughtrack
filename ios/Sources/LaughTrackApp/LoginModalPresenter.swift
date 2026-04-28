import SwiftUI

@MainActor
final class LoginModalPresenter: ObservableObject {
    @Published var isPresented = false

    func present() {
        isPresented = true
    }

    func dismiss() {
        isPresented = false
    }
}
