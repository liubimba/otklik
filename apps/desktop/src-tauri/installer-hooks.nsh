!macro NSIS_HOOK_PREINSTALL
  nsExec::Exec 'taskkill /F /T /IM otklik-backend.exe'
  Pop $0
  Sleep 500
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::Exec 'taskkill /F /T /IM otklik-backend.exe'
  Pop $0
  Sleep 500
!macroend
