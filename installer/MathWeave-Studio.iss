; Inno Setup Script for MathWeave Studio
; Cross-Platform Mathematics Learning & Research Application
;
; Configured for:
; - 64-bit Windows architecture
; - Silent and interactive installation/uninstallation
; - Deterministic upgrade with running application detection
; - Start Menu and optional Desktop shortcuts
; - Complete uninstaller registration

#ifndef MyAppVersion
  #define MyAppVersion "0.1.1"
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "TqvNoCode"
#endif
#ifndef MyAppURL
  #define MyAppURL "https://github.com/TqvNoCode/MathWeave-Studio"
#endif
#ifndef MyAppExeName
  #define MyAppExeName "mathweave-studio.exe"
#endif
#ifndef MyAppName
  #define MyAppName "MathWeave Studio"
#endif
#ifndef MyOutputBaseFilename
  #define MyOutputBaseFilename "MathWeave-Studio-Setup-Unsigned-Dev"
#endif
#ifndef MySourceDir
  #define MySourceDir "..\dist\mathweave-studio"
#endif

[Setup]
; Stable application GUID - retained across all future releases
AppId={{780F209D-79B0-498A-84EB-77A1ED4765E4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename={#MyOutputBaseFilename}
SetupIconFile=..\assets\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; 64-bit Windows requirement
ArchitecturesAllowed=x64compatible x64
ArchitecturesInstallIn64BitMode=x64compatible x64

; Graceful Application Detection and Shutdown on Upgrade
CloseApplications=yes
CloseApplicationsTimeout=30

; Windows Version and Metadata Information
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoTextVersion={#MyAppVersion}
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}. All rights reserved.
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; Uninstaller configuration
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application binaries and dependencies from Onedir intermediate build
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{autoprograms}\{#MyAppName}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Filename: "{app}\{#MyAppExeName}"; Flags: nowait postinstall skipifsilent
