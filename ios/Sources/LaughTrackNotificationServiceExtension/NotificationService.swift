import Foundation
import UserNotifications

final class NotificationService: UNNotificationServiceExtension {
    private var contentHandler: ((UNNotificationContent) -> Void)?
    private var bestAttemptContent: UNMutableNotificationContent?
    private var downloadTask: URLSessionDownloadTask?

    override func didReceive(
        _ request: UNNotificationRequest,
        withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
    ) {
        self.contentHandler = contentHandler

        guard let content = request.content.mutableCopy() as? UNMutableNotificationContent else {
            contentHandler(request.content)
            return
        }
        bestAttemptContent = content

        guard let imageURL = Self.imageURL(from: request.content.userInfo) else {
            contentHandler(content)
            return
        }

        downloadTask = URLSession.shared.downloadTask(with: imageURL) { location, _, _ in
            defer { contentHandler(content) }
            guard let location,
                  let attachment = Self.attachment(fromDownloadedFile: location, sourceURL: imageURL)
            else {
                return
            }
            content.attachments = [attachment]
        }
        downloadTask?.resume()
    }

    override func serviceExtensionTimeWillExpire() {
        downloadTask?.cancel()
        if let bestAttemptContent {
            contentHandler?(bestAttemptContent)
        }
    }

    private static func imageURL(from userInfo: [AnyHashable: Any]) -> URL? {
        guard let raw = userInfo["imageUrl"] as? String else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        return URL(string: trimmed)
    }

    private static func attachment(
        fromDownloadedFile location: URL,
        sourceURL: URL
    ) -> UNNotificationAttachment? {
        let fileExtension = sourceURL.pathExtension.isEmpty ? "jpg" : sourceURL.pathExtension
        let temporaryURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension(fileExtension)
        do {
            try FileManager.default.copyItem(at: location, to: temporaryURL)
            return try UNNotificationAttachment(identifier: "comedian-image", url: temporaryURL)
        } catch {
            return nil
        }
    }
}
