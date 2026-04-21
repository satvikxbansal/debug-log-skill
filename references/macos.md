# macOS — error catalog

Covers: macOS-native apps (AppKit + SwiftUI), menu-bar / status-item apps, global permissions (screen recording, accessibility, input monitoring), sandbox & hardened runtime, entitlements, code signing, notarisation, Mac Catalyst edge cases, `NSWindow` / `NSPanel` behaviour, full-screen / fullscreen-mirroring, external displays.

Each entry follows the same shape: **Symptom → Root cause → Fix → Prevention rule.**

## Table of contents

1. [Global screen-recording permission — silent until reboot](#m01)
2. [Accessibility permission requested per-build in development](#m02)
3. [Input Monitoring — key events drop silently without permission](#m03)
4. [Sandbox entitlement blocks `~/Library/...` access](#m04)
5. [Hardened runtime + missing entitlement = `dyld: Library not loaded`](#m05)
6. [Notarisation staples lost after zipping](#m06)
7. [Menu-bar app shows a Dock icon](#m07)
8. [`NSStatusItem` disappears after system theme change](#m08)
9. [`NSWindow` loses focus when another space switches](#m09)
10. [`NSPanel` doesn't accept keyboard focus by default](#m10)
11. [SwiftUI `WindowGroup` creates a new window on deep-link every time](#m11)
12. [`@FocusState` doesn't work across window boundaries](#m12)
13. [`NSEvent.addGlobalMonitorForEvents` fires even for own app](#m13)
14. [Full-screen SwiftUI view doesn't hide the menu bar](#m14)
15. [External display hot-plug loses window state](#m15)
16. [Mac Catalyst: `UIKit` code that references `UIApplication.shared.delegate` crashes](#m16)
17. [Apple Silicon vs Intel — Rosetta-only linker errors](#m17)
18. [Code signing: "resource fork, Finder information, or similar detritus not allowed"](#m18)
19. [Embedded command-line tool isn't signed → Gatekeeper blocks](#m19)
20. [Login item helper shows a user-visible alert on first launch](#m20)
21. [`AppleScript` / `Automation` permission prompt not shown in release](#m21)
22. [Quick Look previews fail for sandboxed documents](#m22)
23. [URL scheme registration lost on copy to Applications](#m23)
24. [SwiftUI `.alert` in a menu-bar popover does nothing](#m24)
25. [`NSApp.activate(ignoringOtherApps:)` is ignored by default on macOS 14+](#m25)

---

## <a name="m01"></a>1. Global screen-recording permission — silent until reboot

**Symptom.** App requests `CGDisplayStream` / `SCStream` / `CGWindowListCreateImage`. User taps "Allow" in System Settings → Privacy & Security → Screen Recording. App still returns empty pixels.

**Root cause.** On macOS, Screen Recording permission only takes effect after the app is *relaunched* (and historically, after a logout / reboot for some API families). The granted-bit is cached in the running process.

**Fix.** After detecting grant, quit and relaunch the app. For a smoother UX: detect permission state with `CGPreflightScreenCaptureAccess()`; if missing, open the Settings pane directly via `NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture")!)`; after user returns, prompt with "Screen recording enabled — relaunch to apply" and `NSApp.terminate(nil)` followed by a re-exec via `launchApplication`.

**Prevention rule.** Any macOS feature gated by a TCC permission includes a "relaunch to apply" step in the first-run flow. The app detects permission state on launch and doesn't wait for the call to silently fail. Why: the silent failure masquerades as a bug in the capture code; users give up before re-launching.

## <a name="m02"></a>2. Accessibility permission requested per-build in development

**Symptom.** Every time Xcode rebuilds, the developer has to re-grant Accessibility in System Settings. Removing the grant requires the admin password each time.

**Root cause.** TCC identifies apps by code-signing identity + bundle ID + team ID. Dev builds signed with different certs (or unsigned) are seen as distinct apps. Also, unsigned debug builds get removed from the list on each launch.

**Fix.** Sign debug builds with a stable personal-team certificate *and* pin `DEVELOPMENT_TEAM` in the xcconfig. Avoid switching provisioning profiles between runs. Use `tccutil reset Accessibility com.yourco.yourapp` to clean up stale entries.

**Prevention rule.** Local dev builds have a fixed signing identity; `DEVELOPMENT_TEAM` and the bundle ID are stable across branches. Why: TCC re-prompts devour iteration speed and mask real permission bugs ("is it broken, or is TCC stale?").

## <a name="m03"></a>3. Input Monitoring — key events drop silently without permission

**Symptom.** Global keyboard shortcut (say, ⌘⇧Space) registered via `NSEvent.addGlobalMonitorForEvents` doesn't fire. No error, no log.

**Root cause.** On macOS 10.15+, Input Monitoring permission is required for *global* key event observation (not local, not for the key equivalent registered on a menu). The API silently returns a monitor token and drops events.

**Fix.** Check `IOHIDCheckAccess(kIOHIDRequestTypeListenEvent)`, and if not granted, prompt with `IOHIDRequestAccess(kIOHIDRequestTypeListenEvent)`. Send the user to System Settings → Privacy & Security → Input Monitoring if denied. Prefer `MASShortcut` or `HotKey` libraries which wrap this cleanly.

**Prevention rule.** Global event monitoring paths verify Input Monitoring permission up front and surface a user-visible request before attempting to register. Why: silent-drop fails the "is it on?" diagnosis — the feature looks implemented but nonfunctional.

## <a name="m04"></a>4. Sandbox entitlement blocks `~/Library/...` access

**Symptom.** Sandboxed app fails to read `~/Library/Application Support/SomeOtherApp/` with an unhelpful `POSIX error 1 (Operation not permitted)`.

**Root cause.** The App Sandbox restricts file access to the app's container. Access outside requires either a specific entitlement (e.g., `com.apple.security.files.user-selected.read-only`, `com.apple.security.files.downloads.read-write`) or an explicit user grant via `NSOpenPanel` that yields a security-scoped bookmark.

**Fix.** Use `NSOpenPanel` to let the user pick the directory, persist a security-scoped bookmark, and call `startAccessingSecurityScopedResource()` around every access. For read-only access to a known location, add the appropriate sandbox entitlement.

**Prevention rule.** Sandboxed apps treat the filesystem as opaque except for the container. Out-of-container access is gated by bookmarks. Every I/O site documents which entitlement or bookmark grants it. Why: sandbox violations often return POSIX errors that look like "file not found", which sends the debugger down the wrong path.

## <a name="m05"></a>5. Hardened runtime + missing entitlement = `dyld: Library not loaded`

**Symptom.** App built with hardened runtime crashes on launch with `dyld: Library not loaded: @rpath/YourFramework.framework/Versions/A/YourFramework` or `dlopen failed: code signature invalid`.

**Root cause.** Hardened runtime forbids loading unsigned / differently-signed code. A third-party framework (or a Swift package's dynamic library) isn't signed with the same team, or lacks the `com.apple.security.cs.disable-library-validation` entitlement when that's needed.

**Fix.** Re-sign embedded frameworks with the app's team: Xcode handles this via "Embed & Sign". For plugins loaded dynamically from arbitrary locations, add `com.apple.security.cs.disable-library-validation` — but only if you've vetted the loaded code, since it weakens security. Run `codesign -dv --verbose=4 /path/to/YourApp.app/Contents/Frameworks/YourFramework.framework` to inspect.

**Prevention rule.** Every embedded framework is re-signed by the app bundle's team. Library validation stays on unless a plugin architecture demands otherwise, and that exception is documented. Why: hardened-runtime errors are opaque at the point of crash; they're much easier to catch in a signing-audit CI step.

## <a name="m06"></a>6. Notarisation staples lost after zipping

**Symptom.** A notarised DMG / app works. After zipping and re-uploading, Gatekeeper blocks with "Apple could not verify … is free of malware".

**Root cause.** Notarisation staple (`xattr com.apple.quarantine`-clearing metadata) lives in the extended attributes of the `.app`. Some zip tools strip extended attributes.

**Fix.** Use `ditto -c -k --sequesterRsrc --keepParent MyApp.app MyApp.zip` — it preserves xattrs. For DMG distribution, staple after creating the DMG with `xcrun stapler staple MyApp.dmg`, then let users download the DMG directly (not a zip of the DMG).

**Prevention rule.** Distribution packaging uses `ditto` (or DMG-with-stapler) and the CI step verifies via `spctl -a -vv MyApp.app` that Gatekeeper accepts it. Why: notarisation is silently undone by the wrong archive tool; the error only appears on a fresh machine without developer tools.

## <a name="m07"></a>7. Menu-bar app shows a Dock icon

**Symptom.** A menu-bar-only app also appears in the Dock and ⌘-Tab. User complains "why do I have two of these".

**Root cause.** Default `LSUIElement` is `NO`. For a pure menu-bar app, it must be `YES` in `Info.plist`.

**Fix.** Set `LSUIElement = YES` (a.k.a. "Application is agent") in `Info.plist`. If some flows need a Dock icon temporarily (preferences window, onboarding), toggle at runtime via `NSApp.setActivationPolicy(.regular)` and revert to `.accessory` afterward.

**Prevention rule.** Menu-bar apps set `LSUIElement = YES` from project creation. Dock visibility is a mode, toggled explicitly when needed. Why: the default UIKind is a Dock app; a status-item-only app that hasn't opted out is a UX bug that ships.

## <a name="m08"></a>8. `NSStatusItem` disappears after system theme change

**Symptom.** Status-bar icon vanishes when user switches light / dark mode, or after plugging in a monitor.

**Root cause.** The `NSStatusItem.button?.image` was set with a non-template image, and the OS is trying to render it inverted for the other appearance. Or the image's rendering intent wasn't marked `.template`, and the OS's adaptive rendering fails.

**Fix.** Use a template PDF / PNG asset (monochrome, alpha-based) and set `image.isTemplate = true`. The system will tint correctly for light/dark. For multi-state icons, use `NSImage.Name.…` symbols (SF Symbols on 11+).

**Prevention rule.** Status-item icons are template images. Light/dark mode is tested by toggling appearance under "General → Appearance" in Settings. Why: non-template icons look correct on the developer's monitor but vanish or invert on users'.

## <a name="m09"></a>9. `NSWindow` loses focus when another space switches

**Symptom.** Window becomes invisible when the user ⌃→ to another space. Or it moves to the wrong space.

**Root cause.** `collectionBehavior` is at defaults. For windows meant to follow the user, `.canJoinAllSpaces` is the right option. For windows tied to a specific space (document windows), the default is correct but `.moveToActiveSpace` may help.

**Fix.** Set `window.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]` for HUDs / overlays. `window.level = .floating` or `.statusBar` for always-on-top semantics. For floating palettes, `NSPanel` with `.nonactivating` is more appropriate than `NSWindow`.

**Prevention rule.** Window behaviour is declared explicitly via `collectionBehavior` and `level` at creation time. Defaults aren't assumed. Why: Spaces behaviour differs between utility windows, document windows, and HUDs; the defaults are wrong for overlay-style apps.

## <a name="m10"></a>10. `NSPanel` doesn't accept keyboard focus by default

**Symptom.** A panel shows a text field. The user clicks in it but typing does nothing.

**Root cause.** `NSPanel` is by default `becomesKeyOnlyIfNeeded`. For panels that host text input, you need to opt in to key-ness.

**Fix.** Subclass and override `canBecomeKey` and `canBecomeMain` to return `true` for the text-hosting panel. Or use `NSPanel(contentRect:styleMask: [.titled, .resizable, .nonactivatingPanel])` with care around activation.

**Prevention rule.** Any `NSPanel` that hosts text input overrides `canBecomeKey` / `canBecomeMain`. Non-text panels (tool palettes) use the default. Why: "typing doesn't work" is the symptom, but the root is always key-window eligibility.

## <a name="m11"></a>11. SwiftUI `WindowGroup` creates a new window on deep-link every time

**Symptom.** User clicks a link with a custom URL scheme. App launches a new window even though one is already open showing the same document.

**Root cause.** `WindowGroup` in SwiftUI opens an additional window per distinct URL payload unless the handler matches an existing window.

**Fix.** Use `openWindow` / `openURL` actions with a document model that has stable identity. For macOS 13+, `openWindow(id:value:)` and `WindowGroup(for: Model.self)` let you address specific windows. For older macOS, handle the URL in `AppDelegate` and bring the existing window to front manually via `NSApp.windows.first { … }?.makeKeyAndOrderFront(nil)`.

**Prevention rule.** Deep-link handling is routed through a single entry point that checks for an existing window before opening a new one. Why: duplicate windows break keyboard-shortcut binding and confuse users; the first window's state goes stale.

## <a name="m12"></a>12. `@FocusState` doesn't work across window boundaries

**Symptom.** A menu-bar popover opens; user starts typing; `@FocusState` says focus is on the text field but keys go to the Finder.

**Root cause.** `@FocusState` manages focus within the responder chain of a single window. Popover hosting in a borderless window that isn't key doesn't receive key events.

**Fix.** Before showing the popover, make its window key: `window.makeKeyAndOrderFront(nil)` and `NSApp.activate(ignoringOtherApps: true)`. For menu-bar apps, `NSApp.setActivationPolicy(.accessory)` + `activate` is the usual combo.

**Prevention rule.** Popovers / sheets that host text input explicitly request key-window status from the host. Focus visibility is tested with a character count — if typing doesn't change state, focus is in the wrong window. Why: SwiftUI focus feels magic but respects the AppKit responder chain underneath.

## <a name="m13"></a>13. `NSEvent.addGlobalMonitorForEvents` fires even for own app

**Symptom.** Global key monitor fires reliably for other apps but misses events when the user's own app is front — or worse, fires double when the app is front.

**Root cause.** Global monitors only receive events destined for *other* apps. For local monitoring, use `addLocalMonitorForEvents`. Apps that want to react to a shortcut regardless of who's front must register both monitors.

**Fix.** Register both: `addGlobalMonitorForEvents` for when the app isn't front, `addLocalMonitorForEvents` for when it is (returning `nil` if you want to consume the event, or `event` to pass through).

**Prevention rule.** Keyboard monitoring that must work regardless of front app registers both global and local monitors, with the local returning `nil` when consumed. Why: "my shortcut works everywhere except inside my own app" is the tell.

## <a name="m14"></a>14. Full-screen SwiftUI view doesn't hide the menu bar

**Symptom.** Toggling full-screen via `NSWindow.toggleFullScreen(nil)` (or SwiftUI's `.fullScreen` scene modifier) leaves the menu bar visible at the top.

**Root cause.** "Full screen" on macOS has several meanings: native full-screen space (hides menu), presentation options (`NSApplication.PresentationOptions.autoHideMenuBar`), and borderless fullscreen window. The right combination depends on intent.

**Fix.** For an immersive presentation: `NSApp.presentationOptions = [.autoHideMenuBar, .autoHideDock]`. For traditional full-screen: use `toggleFullScreen(nil)` and accept the native space. For kiosk / media players: consider `NSApplication.PresentationOptions` with `.hideMenuBar | .hideDock | .disableProcessSwitching`.

**Prevention rule.** Full-screen behaviour is declared per mode (document full-screen, presentation, kiosk) with a named configuration. The presentation options aren't toggled ad-hoc. Why: hybrid full-screen states (native space + tweaked options) cause visual glitches that only appear on certain macOS versions.

## <a name="m15"></a>15. External display hot-plug loses window state

**Symptom.** User disconnects an external monitor. Window that was on the external moves to a weird position, or disappears offscreen.

**Root cause.** `NSWindow.setFrame(_:display:)` was called once and state wasn't reconciled when `NSApplication.didChangeScreenParametersNotification` fired.

**Fix.** Observe `NSApplication.didChangeScreenParametersNotification`. On change, iterate all open windows, check if their frame is still on a valid `NSScreen`, and if not, move to the main screen or a remembered last-good position.

**Prevention rule.** Windows that persist position across launches validate their frame against `NSScreen.screens` before restoring. Screen-parameter changes trigger a re-validation. Why: offscreen windows are a long-standing UX gripe with no visual indicator of "your window is on a screen that isn't here".

## <a name="m16"></a>16. Mac Catalyst: `UIKit` code that references `UIApplication.shared.delegate` crashes

**Symptom.** An iOS app ported via Catalyst crashes on macOS when trying to access `UIApplicationDelegate.window` or other iOS-specific properties.

**Root cause.** Catalyst remaps UIKit onto AppKit, but some APIs (window management, status bar, certain UIScene behaviours) have no direct mac equivalent. Code that assumes iOS semantics breaks.

**Fix.** Guard with `#if targetEnvironment(macCatalyst)` and provide a mac-specific path. For window management, use `UIWindowScene.windows` or Catalyst-specific scene APIs. For status bar, omit or replace with a mac-appropriate UI element.

**Prevention rule.** Every UIKit API call is evaluated for Catalyst compatibility at the time it's added, with `targetEnvironment(macCatalyst)` guards where needed. Tests run on both simulators (iOS) and Catalyst targets. Why: Catalyst breakage is invisible when developing on iOS and appears only when the mac build runs.

## <a name="m17"></a>17. Apple Silicon vs Intel — Rosetta-only linker errors

**Symptom.** Build succeeds on an Intel Mac, fails on Apple Silicon with `symbol not found for architecture arm64`. Or vice versa.

**Root cause.** An embedded framework or XCFramework ships only one architecture slice. CocoaPods / Carthage / SPM cache lingers from a previous install in the other arch.

**Fix.** For frameworks you control, build as `XCFramework` with both slices (`-create-xcframework` in the build script). For third-party: check the `Pods/` / `Carthage/Build/` for arm64 slice presence; `lipo -info` inspects what's there. Clean derived data and reinstall dependencies after switching primary architecture.

**Prevention rule.** CI builds on both arm64 and x86_64. Every XCFramework ships both slices. Dependency manager lock files are committed and reinstalls are reproducible. Why: single-arch regressions pass local testing on the dev's mac and fail in TestFlight for the other population.

## <a name="m18"></a>18. Code signing: "resource fork, Finder information, or similar detritus not allowed"

**Symptom.** Signing or notarisation fails with "resource fork, Finder information, or similar detritus not allowed".

**Root cause.** Extended attributes (Finder tags, `com.apple.FinderInfo`) on files inside the app bundle. Usually introduced by copying assets through the Finder on a volume that preserved them, or by a build script that didn't strip them.

**Fix.** `xattr -cr /path/to/YourApp.app` before re-signing. Integrate into the build phase: `find "$TARGET_BUILD_DIR/$PRODUCT_NAME.app" -exec xattr -c {} \;`.

**Prevention rule.** A build phase strips extended attributes from the final bundle before code-signing. CI uses clean `.xcworkspace` checkouts so nothing from the dev's disk leaks in. Why: "detritus not allowed" errors are recurring and undiagnosable without the grep; adding the step once eliminates the class.

## <a name="m19"></a>19. Embedded command-line tool isn't signed → Gatekeeper blocks

**Symptom.** App bundles a helper CLI in `Contents/MacOS/` or `Contents/Resources/`. On first launch on a fresh machine, the CLI can't run: "cannot be opened because the developer cannot be verified".

**Root cause.** Xcode signs the main executable and frameworks but not arbitrary executable resources. The CLI needs explicit signing with the same team and hardened-runtime options as the parent.

**Fix.** In a build phase after copying: `codesign --force --options runtime --sign "Developer ID Application: Your Team" --entitlements Helper.entitlements "$TARGET_BUILD_DIR/$PRODUCT_NAME.app/Contents/Resources/helper-cli"`. Notarisation should be on the outer app; the inner CLI inherits the staple.

**Prevention rule.** Every executable file in a bundle — binaries, scripts, helper tools — is signed in a named build phase. The phase runs codesign with `--options runtime`. Why: ad-hoc embedded executables are a common blind spot and the error only surfaces on users' machines, never the developer's.

## <a name="m20"></a>20. Login item helper shows a user-visible alert on first launch

**Symptom.** App uses `SMLoginItemSetEnabled` (legacy) to register a launch-at-login helper. On first launch, macOS shows a "YourApp would like permission to run at login" alert and the user taps "Don't Allow". Silent failure thereafter.

**Root cause.** The legacy `SMLoginItemSetEnabled` API is deprecated and on macOS 13+ is replaced by `SMAppService`. User consent is per-user, persisted, and doesn't re-prompt if denied.

**Fix.** Migrate to `SMAppService` (macOS 13+). Provide a UI affordance for toggling login-at-launch in Preferences; on first enable, call `SMAppService.mainApp.register()` and surface `.notRegistered` / `.enabled` / `.requiresApproval` states via `SMAppService.status`. Guide the user to System Settings → General → Login Items if approval is needed.

**Prevention rule.** Login-at-login features use `SMAppService` on macOS 13+ and show the user an explicit toggle. The app handles denial gracefully and never silently assumes the helper is running. Why: a silent-failed login item produces "the app doesn't start" bug reports that are actually TCC / SMAppService state.

## <a name="m21"></a>21. `AppleScript` / `Automation` permission prompt not shown in release

**Symptom.** App scripts Safari or Finder via `NSAppleScript` / `OSAScript`. In debug it prompts for permission; in release it silently fails.

**Root cause.** `com.apple.security.automation.apple-events` entitlement missing from the release entitlements file. Or `NSAppleEventsUsageDescription` is missing from `Info.plist`.

**Fix.** Add `com.apple.security.automation.apple-events = true` to release entitlements. Add `NSAppleEventsUsageDescription` with a user-facing explanation. Include per-target `com.apple.security.scripting-targets` when the automation is scoped.

**Prevention rule.** Automation features ship with the entitlement and usage description from day one, and a release-build smoke test runs the scripted flow. Why: entitlement drift between debug and release is a recurring macOS failure mode; release builds fail silently where debug prompts.

## <a name="m22"></a>22. Quick Look previews fail for sandboxed documents

**Symptom.** App has a custom document type with a Quick Look plugin. Previews work in the Finder for files copied out, fail for files inside the sandbox container.

**Root cause.** Quick Look runs in a separate process (`QuickLookUIService`) that doesn't have access to the app's sandbox container. For it to read the document, the document path has to be outside the container or accessed through a security-scoped URL that's granted to the Quick Look process.

**Fix.** For document-based apps, store documents in the user's Documents folder (granted via standard `NSOpenPanel`) rather than the private container. For internal caches that should Quick Look, export to a temporary location in `~/Library/Caches/` that's accessible.

**Prevention rule.** Sandboxed document formats are user-accessible by design — stored where the user navigates, not inside `Application Support/`. Quick Look compatibility is tested on a signed, sandboxed build. Why: sandbox container paths feel "real" in development and turn out to be invisible to system services.

## <a name="m23"></a>23. URL scheme registration lost on copy to Applications

**Symptom.** App registered a custom `myapp://` URL scheme. Works in Xcode's run directory; fails after copying to `/Applications` until the user double-clicks to launch once.

**Root cause.** Launch Services registers URL schemes when it scans a bundle. Copying via Finder usually triggers a scan; copying via CLI (`cp -R`) sometimes doesn't. Also, multiple copies of the same app on disk can "win" the scheme registration.

**Fix.** After install, nudge Launch Services: `lsregister -f /Applications/YourApp.app`. For ambiguity between dev builds and installed builds, delete stale copies and run `lsregister -kill -r -domain local -domain user`.

**Prevention rule.** The install path for the app is singular: one copy in `/Applications`, nothing in `~/Downloads/`. Launch Services is poked as part of the first launch via `NSApp.registerURLSchemeHandler`-style code or an `lsregister` helper. Why: URL scheme ambiguity is a debugging nightmare and only reproduces on users' machines where an old version was in `/Applications`.

## <a name="m24"></a>24. SwiftUI `.alert` in a menu-bar popover does nothing

**Symptom.** Tapping a "Delete" button in a menu-bar popover triggers `.alert(...)` — nothing appears.

**Root cause.** The popover's hosting window isn't key when the alert tries to present, and `.alert` in SwiftUI on macOS requires a key window. Or the alert is modal to a window the popover isn't attached to.

**Fix.** Before triggering the alert, make the popover's window key (`NSApp.activate(ignoringOtherApps: true)`). Or replace the alert with a SwiftUI-in-popover confirmation UI that doesn't depend on the window-level alert pathway.

**Prevention rule.** Menu-bar popovers avoid modal `.alert` / `.confirmationDialog` in favour of inline confirmation UI, or explicitly activate their window before presenting. Why: macOS alert presentation has window-level assumptions that are implicit on iOS and broken in popover land.

## <a name="m25"></a>25. `NSApp.activate(ignoringOtherApps:)` is ignored by default on macOS 14+

**Symptom.** App calls `NSApp.activate(ignoringOtherApps: true)` from a background event (URL open, notification tap) on macOS Sonoma. Focus doesn't switch. Window doesn't come to front.

**Root cause.** macOS 14 tightened activation — apps can't steal focus from foreground apps without a recent user interaction. The call is respected only within a short window after a user gesture (click on Dock, URL handler, AppleScript).

**Fix.** For URL handlers and deep links, the OS already provides activation on behalf of the event; don't fight it. For long-running background work that needs to surface a window, post a user notification that the user must click — the click is the activation gesture.

**Prevention rule.** Code that needs to bring the app forward relies on an OS-provided activation gesture (URL event, notification click, Dock click), never a background `NSApp.activate` call. Why: macOS 14's activation rules broke a lot of "ping me when ready" UX; the fix is to go through a notification, not fight the OS.
