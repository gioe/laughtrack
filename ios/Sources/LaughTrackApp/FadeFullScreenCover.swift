import SwiftUI

#if os(iOS)
import UIKit

extension View {
    func fadeFullScreenCover<CoverContent: View>(
        isPresented: Binding<Bool>,
        @ViewBuilder content: @escaping () -> CoverContent
    ) -> some View {
        background(
            FadeFullScreenCoverPresenter(
                isPresented: isPresented,
                coverContent: content
            )
            .frame(width: 0, height: 0)
        )
    }
}

private struct FadeFullScreenCoverPresenter<CoverContent: View>: UIViewControllerRepresentable {
    @Binding var isPresented: Bool
    let coverContent: () -> CoverContent

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeUIViewController(context: Context) -> UIViewController {
        UIViewController()
    }

    func updateUIViewController(_ uiViewController: UIViewController, context: Context) {
        if isPresented {
            if let hostingController = context.coordinator.presentedController as? UIHostingController<CoverContent> {
                hostingController.rootView = coverContent()
                return
            }

            guard uiViewController.presentedViewController == nil else { return }

            let hostingController = UIHostingController(rootView: coverContent())
            hostingController.view.backgroundColor = .clear
            hostingController.modalPresentationStyle = .overFullScreen
            hostingController.modalTransitionStyle = .crossDissolve
            context.coordinator.presentedController = hostingController

            DispatchQueue.main.async {
                uiViewController.present(hostingController, animated: true)
            }
        } else if let presentedController = context.coordinator.presentedController {
            context.coordinator.presentedController = nil
            DispatchQueue.main.async {
                presentedController.dismiss(animated: true)
            }
        }
    }

    final class Coordinator {
        var presentedController: UIViewController?
    }
}
#endif
