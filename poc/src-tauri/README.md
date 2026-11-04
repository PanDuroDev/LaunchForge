# Tauri host spike

This is a deliberately privilege-free Tauri v2 shell for the shared renderer package. It registers no commands and includes no filesystem, shell, process, network updater, or plugin permissions. The purpose is to prove that the exported static renderer can be hosted by the selected Windows shell without moving renderer logic into Rust.

## Windows build prerequisites

- Rust stable toolchain with the MSVC target.
- Microsoft C++ Build Tools (`Desktop development with C++`).
- Microsoft Edge WebView2 Runtime.

Build after producing `poc/dist/`:

```powershell
cargo build --release --manifest-path .\poc\src-tauri\Cargo.toml
```

The executable is written under `poc/src-tauri/target/release/`. The executable is a portable host spike, not a signed production launcher. The Tauri configuration explicitly embeds `icons/icon.ico`; the Windows preparation step stages the exact icon referenced by `window.iconAssetId` at this path. WebView2 remains an OS/runtime prerequisite and is not silently bundled by this no-installer spike.
