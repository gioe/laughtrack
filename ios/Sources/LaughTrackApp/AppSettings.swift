import Foundation

#if canImport(UIKit)
import UIKit
#endif

func openAppSettings() {
    #if canImport(UIKit)
    guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
    UIApplication.shared.open(url)
    #endif
}
