import SharedKit
import SwiftUI

// MARK: - Theme

public typealias AppThemeProtocol = SharedKit.AppThemeProtocol
public typealias DefaultTheme = SharedKit.DefaultTheme
public typealias ColorTokens = SharedKit.ColorTokens
public typealias TypographyTokens = SharedKit.TypographyTokens
public typealias SpacingTokens = SharedKit.SpacingTokens
public typealias CornerRadiusTokens = SharedKit.CornerRadiusTokens
public typealias ShadowTokens = SharedKit.ShadowTokens
public typealias IconSizeTokens = SharedKit.IconSizeTokens
public typealias AnimationTokens = SharedKit.AnimationTokens
public typealias GradientTokens = SharedKit.GradientTokens
public typealias ShadowStyle = SharedKit.ShadowStyle

// MARK: - Service Container

public typealias ServiceContainer = SharedKit.ServiceContainer
public typealias ServiceScope = SharedKit.ServiceScope

// MARK: - Navigation

public typealias NavigationCoordinator = SharedKit.NavigationCoordinator
public typealias CoordinatedNavigationStack = SharedKit.CoordinatedNavigationStack
public typealias ModalPresentation = SharedKit.ModalPresentation
public typealias PresentationStyle = SharedKit.PresentationStyle

// MARK: - NetworkMonitor

public typealias NetworkMonitor = SharedKit.NetworkMonitor
public typealias NetworkMonitorProtocol = SharedKit.NetworkMonitorProtocol

// MARK: - KeychainStorage

public typealias KeychainStorage = SharedKit.KeychainStorage
public typealias SecureStorageProtocol = SharedKit.SecureStorageProtocol
public typealias AuthTokenManager = SharedKit.AuthTokenManager

// MARK: - ToastManager

public typealias ToastManager = SharedKit.ToastManager
public typealias ToastManagerProtocol = SharedKit.ToastManagerProtocol

// MARK: - OfflineOperationQueue

public typealias OfflineOperationQueue = SharedKit.OfflineOperationQueue
public typealias QueuedOperation = SharedKit.QueuedOperation

// MARK: - DataCache + ImageCache

public typealias DataCache = SharedKit.DataCache
public typealias ImageCache = SharedKit.ImageCache

// MARK: - AppStateStorage

public typealias AppStateStorage = SharedKit.AppStateStorage
public typealias AppStateStorageProtocol = SharedKit.AppStateStorageProtocol

// Environment extensions are automatically available through the re-exported types.
// The .environment(\.appTheme, ...) and .environment(\.serviceContainer, ...) modifiers
// work because EnvironmentValues extensions are resolved at the SwiftUI framework level,
// not through the import that declares the key.
